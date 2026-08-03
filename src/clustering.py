from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.cluster import KMeans
from sklearn.manifold import SpectralEmbedding
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.neighbors import kneighbors_graph

from .config import ClusteringConfig


def select_analysis_slice(df: pd.DataFrame, config: ClusteringConfig) -> pd.DataFrame:
    top_notes = df["noteId"].value_counts().head(config.target_note_count).index
    df_sub = df[df["noteId"].isin(top_notes)].copy()

    top_users = df_sub["raterParticipantId"].value_counts().head(config.target_user_count).index
    df_sub = df_sub[df_sub["raterParticipantId"].isin(top_users)].copy()
    return df_sub


def build_sparse_centered_matrix(
    df_sub: pd.DataFrame,
) -> tuple[sp.csr_matrix, pd.Index, pd.Index]:
    user_codes, user_index = pd.factorize(df_sub["raterParticipantId"], sort=False)
    note_codes, note_index = pd.factorize(df_sub["noteId"], sort=False)
    votes = df_sub["vote"].to_numpy(dtype=np.float32)

    n_users = len(user_index)
    user_sum = np.bincount(user_codes, weights=votes, minlength=n_users)
    user_count = np.bincount(user_codes, minlength=n_users).astype(np.float32)
    user_mean = (user_sum / np.maximum(user_count, 1.0)).astype(np.float32)

    centered = votes - user_mean[user_codes]
    matrix = sp.coo_matrix(
        (centered, (user_codes, note_codes)),
        shape=(n_users, len(note_index)),
        dtype=np.float32,
    ).tocsr()
    return matrix, pd.Index(user_index, name="raterParticipantId"), pd.Index(note_index, name="noteId")


def build_knn_affinity(
    user_matrix: sp.csr_matrix,
    n_neighbors: int,
) -> sp.csr_matrix:
    n = user_matrix.shape[0]
    k = max(1, min(n_neighbors, n - 1))
    # cosine "distance" in sklearn is 1 - cosine_similarity in [0, 2].
    # kneighbors_graph runs in O(n * k) wall-clock with optimized brute-force
    # cosine search on sparse inputs — orders of magnitude cheaper than a
    # dense n x n cosine_similarity call.
    knn = kneighbors_graph(
        user_matrix,
        n_neighbors=k,
        mode="distance",
        metric="cosine",
        include_self=False,
        n_jobs=-1,
    ).astype(np.float32)

    # Distance -> affinity in [0, 1]. Pairs that ended up with negative
    # cosine (distance > 1) collapse to a small non-negative weight rather
    # than getting clipped away entirely, mirroring the linear (sim+1)/2
    # mapping the dense version used.
    knn.data = np.clip(1.0 - 0.5 * knn.data, 0.0, 1.0).astype(np.float32)

    # Symmetrize: a directed edge from i->j is enough; take the stronger tie.
    affinity = knn.maximum(knn.T).tocsr()
    affinity.setdiag(1.0)
    affinity.eliminate_zeros()
    return affinity


def clean_affinity(affinity: sp.spmatrix) -> sp.csr_matrix:
    if not sp.issparse(affinity):
        affinity = sp.csr_matrix(affinity)
    cleaned = affinity.tocsr(copy=True)
    if np.issubdtype(cleaned.data.dtype, np.floating):
        np.nan_to_num(cleaned.data, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
    np.clip(cleaned.data, 0.0, 1.0, out=cleaned.data)
    cleaned.setdiag(1.0)
    cleaned.eliminate_zeros()
    return cleaned


def spectral_embedding_from_affinity(
    affinity: sp.spmatrix, n_components: int, random_state: int
) -> np.ndarray:
    embedding = SpectralEmbedding(
        n_components=n_components,
        affinity="precomputed",
        random_state=random_state,
        n_jobs=-1,
    )
    return embedding.fit_transform(affinity)


def _kmeans_on_embedding(embedding: np.ndarray, n_clusters: int, random_state: int) -> np.ndarray:
    return KMeans(
        n_clusters=n_clusters,
        n_init=10,
        random_state=random_state,
    ).fit_predict(embedding)


def silhouette_over_k(
    affinity: sp.spmatrix,
    k_min: int,
    k_max: int,
    random_state: int,
    sample_size: int | None = None,
) -> tuple[int, pd.DataFrame]:
    affinity_clean = clean_affinity(affinity)
    n = affinity_clean.shape[0]
    effective_sample = None if sample_size is None or sample_size >= n else sample_size
    rows: list[tuple[int, float]] = []

    for k in range(k_min, k_max + 1):
        embedded = spectral_embedding_from_affinity(
            affinity_clean, n_components=k, random_state=random_state
        )
        labels = _kmeans_on_embedding(embedded, n_clusters=k, random_state=random_state)
        score = silhouette_score(
            embedded,
            labels,
            metric="euclidean",
            sample_size=effective_sample,
            random_state=random_state,
        )
        rows.append((k, float(score)))

    result = pd.DataFrame(rows, columns=["k", "silhouette"])
    best_k = int(result.loc[result["silhouette"].idxmax(), "k"])
    return best_k, result


def stability_over_k(
    affinity: sp.spmatrix,
    k_min: int,
    k_max: int,
    n_runs: int,
    subsample_frac: float,
    random_state: int,
) -> tuple[int | None, pd.DataFrame]:
    rng = np.random.default_rng(random_state)
    affinity_clean = clean_affinity(affinity)
    n_rows = affinity_clean.shape[0]
    sample_size = int(np.floor(subsample_frac * n_rows))
    rows: list[tuple[int, float, int]] = []

    for k in range(k_min, k_max + 1):
        labelings: list[np.ndarray] = []
        index_sets: list[np.ndarray] = []

        for run_idx in range(n_runs):
            subset_idx = np.sort(rng.choice(n_rows, size=sample_size, replace=False))
            subset_affinity = affinity_clean[subset_idx][:, subset_idx]
            embedded = spectral_embedding_from_affinity(
                subset_affinity,
                n_components=k,
                random_state=random_state + run_idx,
            )
            labels = _kmeans_on_embedding(
                embedded, n_clusters=k, random_state=random_state + run_idx
            )
            labelings.append(labels)
            index_sets.append(subset_idx)

        aris: list[float] = []
        for i in range(n_runs):
            for j in range(i + 1, n_runs):
                inter, ii, jj = np.intersect1d(index_sets[i], index_sets[j], return_indices=True)
                if inter.size < max(50, k * 10):
                    continue
                aris.append(adjusted_rand_score(labelings[i][ii], labelings[j][jj]))

        rows.append((k, float(np.mean(aris)) if aris else np.nan, len(aris)))

    result = pd.DataFrame(rows, columns=["k", "mean_ari", "n_pairs"])
    non_null = result.dropna(subset=["mean_ari"])
    best_k = int(non_null.loc[non_null["mean_ari"].idxmax(), "k"]) if len(non_null) else None
    return best_k, result


def run_clustering(
    df: pd.DataFrame,
    config: ClusteringConfig | None = None,
) -> dict[str, object]:
    config = config or ClusteringConfig()
    df_sub = select_analysis_slice(df, config)

    user_matrix, user_index, note_index = build_sparse_centered_matrix(df_sub)
    affinity = build_knn_affinity(user_matrix, n_neighbors=config.knn_neighbors)
    affinity_clean = clean_affinity(affinity)

    k_sil, sil_df = silhouette_over_k(
        affinity_clean,
        k_min=config.k_min,
        k_max=config.k_max,
        random_state=config.random_state,
        sample_size=config.silhouette_sample_size,
    )
    k_stab, stab_df = stability_over_k(
        affinity_clean,
        k_min=config.k_min,
        k_max=config.k_max,
        n_runs=config.stability_runs,
        subsample_frac=config.stability_subsample_frac,
        random_state=config.random_state,
    )
    n_clusters = k_stab if k_stab is not None else k_sil

    embedded = spectral_embedding_from_affinity(
        affinity_clean, n_components=n_clusters, random_state=config.random_state
    )
    user_labels = _kmeans_on_embedding(
        embedded, n_clusters=n_clusters, random_state=config.random_state
    )

    user_cluster_map = dict(zip(user_index, user_labels))
    df_clustered = df_sub.copy()
    df_clustered["cluster"] = df_clustered["raterParticipantId"].map(user_cluster_map)
    df_clustered = df_clustered.dropna(subset=["cluster"]).copy()
    user_cluster_df = pd.DataFrame(
        {
            "raterParticipantId": user_index,
            "cluster": user_labels,
        }
    )

    return {
        "config": asdict(config),
        "df_sub": df_sub,
        "user_index": user_index,
        "note_index": note_index,
        "user_matrix": user_matrix,
        "affinity": affinity,
        "affinity_clean": affinity_clean,
        "silhouette_table": sil_df,
        "stability_table": stab_df,
        "n_clusters": n_clusters,
        "user_labels": user_labels,
        "user_cluster_df": user_cluster_df,
        "df_clustered": df_clustered,
    }


def build_user_cluster_summary(df_clustered: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    user_stats = (
        df_clustered.groupby(["raterParticipantId", "cluster"])
        .agg(
            total_votes=("vote", "count"),
            positive_votes=("vote", "sum"),
            negative_votes=("vote", lambda x: (x == 0).sum()),
            distinct_notes=("noteId", "nunique"),
        )
        .reset_index()
    )
    user_stats["positive_rate"] = user_stats["positive_votes"] / user_stats["total_votes"]
    user_stats["negative_rate"] = user_stats["negative_votes"] / user_stats["total_votes"]

    cluster_summary = (
        user_stats.groupby("cluster")
        .agg(
            users=("raterParticipantId", "nunique"),
            avg_total_votes=("total_votes", "mean"),
            median_total_votes=("total_votes", "median"),
            avg_positive_rate=("positive_rate", "mean"),
            avg_negative_rate=("negative_rate", "mean"),
            avg_distinct_notes=("distinct_notes", "mean"),
        )
        .reset_index()
    )
    return user_stats, cluster_summary
