from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
from sklearn.cluster import KMeans
from sklearn.manifold import SpectralEmbedding
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.neighbors import kneighbors_graph

from src.clustering import build_sparse_centered_matrix, select_analysis_slice


@dataclass(frozen=True)
class SpectralFastConfig:
    target_note_count: int
    target_user_count: int
    min_note_ratings: int = 3
    hours_window: int = 48
    k_min: int = 2
    k_max: int = 7
    random_state: int = 42
    stability_runs: int = 5
    stability_subsample_frac: float = 0.8
    knn_neighbors: int = 15
    silhouette_sample_size: int = 5000
    ann_backend_min_users: int = 8000
    pynndescent_n_trees: int = 32
    pynndescent_max_candidates: int = 60
    require_ann: bool = True
    kmeans_n_init: int = 10
    eigen_solver: str = "arpack"  # "arpack" | "lobpcg" | "amg"


def _kmeans_on_embedding(embedding: np.ndarray, n_clusters: int, random_state: int, n_init: int) -> np.ndarray:
    return KMeans(
        n_clusters=n_clusters,
        n_init=n_init,
        random_state=random_state,
    ).fit_predict(embedding)


def _knn_via_pynndescent(
    user_matrix: sp.csr_matrix,
    n_neighbors: int,
    n_trees: int,
    max_candidates: int,
    random_state: int,
) -> sp.csr_matrix:
    from pynndescent import NNDescent

    n = user_matrix.shape[0]
    index = NNDescent(
        user_matrix,
        metric="cosine",
        n_neighbors=n_neighbors + 1,
        n_trees=n_trees,
        max_candidates=max_candidates,
        random_state=random_state,
        verbose=True,
    )
    indices, distances = index.neighbor_graph

    rows = np.repeat(np.arange(n, dtype=np.int64), indices.shape[1])
    cols = indices.reshape(-1).astype(np.int64)
    data = distances.reshape(-1).astype(np.float32)
    keep = rows != cols
    return sp.csr_matrix((data[keep], (rows[keep], cols[keep])), shape=(n, n))


def _knn_via_sklearn(user_matrix: sp.csr_matrix, n_neighbors: int) -> sp.csr_matrix:
    return kneighbors_graph(
        user_matrix,
        n_neighbors=n_neighbors,
        mode="distance",
        metric="cosine",
        include_self=False,
        n_jobs=-1,
    ).astype(np.float32)


def build_fast_knn_affinity(
    user_matrix: sp.csr_matrix,
    config: SpectralFastConfig,
) -> tuple[sp.csr_matrix, str]:
    n = user_matrix.shape[0]
    k = max(1, min(config.knn_neighbors, n - 1))
    use_ann = n >= config.ann_backend_min_users

    if use_ann:
        try:
            knn = _knn_via_pynndescent(
                user_matrix,
                n_neighbors=k,
                n_trees=config.pynndescent_n_trees,
                max_candidates=config.pynndescent_max_candidates,
                random_state=config.random_state,
            )
            backend = "pynndescent"
        except Exception:
            if config.require_ann:
                raise
            knn = _knn_via_sklearn(user_matrix, n_neighbors=k)
            backend = "sklearn_exact_fallback"
    else:
        knn = _knn_via_sklearn(user_matrix, n_neighbors=k)
        backend = "sklearn_exact_small_n"

    knn.data = np.clip(1.0 - 0.5 * knn.data, 0.0, 1.0).astype(np.float32)
    affinity = knn.maximum(knn.T).tocsr()
    affinity.setdiag(1.0)
    affinity.eliminate_zeros()
    return affinity, backend


def clean_affinity(affinity: sp.spmatrix) -> sp.csr_matrix:
    cleaned = affinity.tocsr(copy=True)
    np.nan_to_num(cleaned.data, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
    np.clip(cleaned.data, 0.0, 1.0, out=cleaned.data)
    cleaned.setdiag(1.0)
    cleaned.eliminate_zeros()
    return cleaned


def spectral_embedding_from_affinity(
    affinity: sp.spmatrix,
    n_components: int,
    random_state: int,
    eigen_solver: str = "arpack",
) -> np.ndarray:
    embedding = SpectralEmbedding(
        n_components=n_components,
        affinity="precomputed",
        eigen_solver=eigen_solver,
        random_state=random_state,
        n_jobs=-1,
    )
    return embedding.fit_transform(affinity).astype(np.float32)


def graph_diagnostics(affinity: sp.csr_matrix, backend: str, config: SpectralFastConfig) -> pd.DataFrame:
    offdiag = affinity.copy()
    offdiag.setdiag(0)
    offdiag.eliminate_zeros()
    degrees = np.diff(offdiag.indptr)
    n_components, labels = connected_components(affinity, directed=False)
    component_sizes = np.bincount(labels)
    return pd.DataFrame([{
        "backend": backend,
        "users": int(affinity.shape[0]),
        "knn_neighbors": int(config.knn_neighbors),
        "nnz_with_diag": int(affinity.nnz),
        "offdiag_edges": int(offdiag.nnz),
        "degree_min": int(degrees.min()) if len(degrees) else 0,
        "degree_median": float(np.median(degrees)) if len(degrees) else 0.0,
        "degree_mean": float(degrees.mean()) if len(degrees) else 0.0,
        "degree_max": int(degrees.max()) if len(degrees) else 0,
        "connected_components": int(n_components),
        "largest_component_users": int(component_sizes.max()) if len(component_sizes) else 0,
        "largest_component_share": float(component_sizes.max() / max(affinity.shape[0], 1)) if len(component_sizes) else 0.0,
    }])


def silhouette_over_k_reuse(
    embedding_kmax: np.ndarray,
    config: SpectralFastConfig,
) -> tuple[int, pd.DataFrame]:
    n = embedding_kmax.shape[0]
    effective_sample = None if config.silhouette_sample_size >= n else config.silhouette_sample_size
    rows = []
    for k in range(config.k_min, config.k_max + 1):
        emb = embedding_kmax[:, :k]
        labels = _kmeans_on_embedding(emb, k, config.random_state, config.kmeans_n_init)
        if len(np.unique(labels)) < 2:
            score = np.nan
        else:
            score = silhouette_score(
                emb,
                labels,
                metric="euclidean",
                sample_size=effective_sample,
                random_state=config.random_state,
            )
        rows.append({"k": k, "silhouette": float(score) if pd.notna(score) else np.nan})
    result = pd.DataFrame(rows)
    non_null = result.dropna(subset=["silhouette"])
    best_k = int(non_null.loc[non_null["silhouette"].idxmax(), "k"]) if len(non_null) else config.k_min
    return best_k, result


def stability_over_k_reuse(
    affinity: sp.csr_matrix,
    config: SpectralFastConfig,
) -> tuple[int | None, pd.DataFrame]:
    rng = np.random.default_rng(config.random_state)
    n_rows = affinity.shape[0]
    sample_size = int(np.floor(config.stability_subsample_frac * n_rows))
    subsets = [
        np.sort(rng.choice(n_rows, size=sample_size, replace=False))
        for _ in range(config.stability_runs)
    ]

    labels_by_k: dict[int, list[np.ndarray]] = {k: [] for k in range(config.k_min, config.k_max + 1)}
    for run_idx, subset_idx in enumerate(subsets):
        subset_affinity = affinity[subset_idx][:, subset_idx]
        subset_embedding = spectral_embedding_from_affinity(
            subset_affinity,
            n_components=config.k_max,
            random_state=config.random_state + run_idx,
            eigen_solver=config.eigen_solver,
        )
        for k in range(config.k_min, config.k_max + 1):
            labels = _kmeans_on_embedding(
                subset_embedding[:, :k],
                k,
                config.random_state + run_idx,
                config.kmeans_n_init,
            )
            labels_by_k[k].append(labels)

    rows = []
    for k in range(config.k_min, config.k_max + 1):
        aris = []
        labelings = labels_by_k[k]
        for i in range(config.stability_runs):
            for j in range(i + 1, config.stability_runs):
                inter, ii, jj = np.intersect1d(subsets[i], subsets[j], return_indices=True)
                if inter.size < max(50, k * 10):
                    continue
                aris.append(adjusted_rand_score(labelings[i][ii], labelings[j][jj]))
        rows.append({
            "k": k,
            "mean_ari": float(np.mean(aris)) if aris else np.nan,
            "std_ari": float(np.std(aris, ddof=1)) if len(aris) > 1 else np.nan,
            "min_ari": float(np.min(aris)) if aris else np.nan,
            "max_ari": float(np.max(aris)) if aris else np.nan,
            "n_pairs": len(aris),
        })
    result = pd.DataFrame(rows)
    non_null = result.dropna(subset=["mean_ari"])
    best_k = int(non_null.loc[non_null["mean_ari"].idxmax(), "k"]) if len(non_null) else None
    return best_k, result


def run_clustering_spectral_fast(
    df: pd.DataFrame,
    config: SpectralFastConfig,
) -> dict[str, object]:
    runtime_rows = []

    t0 = perf_counter()
    df_sub = select_analysis_slice(df, config)
    runtime_rows.append({"stage": "select_analysis_slice", "seconds": perf_counter() - t0})

    t0 = perf_counter()
    user_matrix, user_index, note_index = build_sparse_centered_matrix(df_sub)
    runtime_rows.append({"stage": "build_sparse_centered_matrix", "seconds": perf_counter() - t0})

    t0 = perf_counter()
    affinity, backend = build_fast_knn_affinity(user_matrix, config)
    affinity_clean = clean_affinity(affinity)
    runtime_rows.append({"stage": f"build_knn_affinity_{backend}", "seconds": perf_counter() - t0})

    t0 = perf_counter()
    graph_df = graph_diagnostics(affinity_clean, backend, config)
    runtime_rows.append({"stage": "graph_diagnostics", "seconds": perf_counter() - t0})

    t0 = perf_counter()
    embedding_kmax = spectral_embedding_from_affinity(
        affinity_clean,
        n_components=config.k_max,
        random_state=config.random_state,
        eigen_solver=config.eigen_solver,
    )
    runtime_rows.append({"stage": "spectral_embedding_full_kmax", "seconds": perf_counter() - t0})

    t0 = perf_counter()
    k_sil, sil_df = silhouette_over_k_reuse(embedding_kmax, config)
    runtime_rows.append({"stage": "silhouette_over_k_reuse", "seconds": perf_counter() - t0})

    t0 = perf_counter()
    k_stab, stab_df = stability_over_k_reuse(affinity_clean, config)
    runtime_rows.append({"stage": "stability_over_k_reuse", "seconds": perf_counter() - t0})

    n_clusters = k_stab if k_stab is not None else k_sil
    user_labels = _kmeans_on_embedding(
        embedding_kmax[:, :n_clusters],
        n_clusters,
        config.random_state,
        config.kmeans_n_init,
    )

    user_cluster_map = dict(zip(user_index, user_labels))
    df_clustered = df_sub.copy()
    df_clustered["cluster"] = df_clustered["raterParticipantId"].map(user_cluster_map)
    df_clustered = df_clustered.dropna(subset=["cluster"]).copy()
    user_cluster_df = pd.DataFrame({
        "raterParticipantId": user_index,
        "cluster": user_labels,
    })

    runtime_df = pd.DataFrame(runtime_rows)
    runtime_df["variant"] = "spectral_fast"
    return {
        "config": asdict(config),
        "df_sub": df_sub,
        "user_index": user_index,
        "note_index": note_index,
        "user_matrix": user_matrix,
        "affinity_clean": affinity_clean,
        "embedding": embedding_kmax,
        "silhouette_table": sil_df,
        "stability_table": stab_df,
        "graph_diagnostics": graph_df,
        "runtime_table": runtime_df,
        "n_clusters": n_clusters,
        "user_labels": user_labels,
        "user_cluster_df": user_cluster_df,
        "df_clustered": df_clustered,
        "knn_backend": backend,
    }
