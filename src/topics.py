from __future__ import annotations

import numpy as np
import pandas as pd
import re


def shorten_topic_name(name: str, max_len: int = 42, max_terms: int = 4) -> str:
    if not isinstance(name, str) or not name.strip():
        return "Unknown"

    cleaned = re.sub(r"^\d+_", "", name.strip())
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"www\.\S+", " ", cleaned)
    cleaned = cleaned.replace("__", "_").replace("-", "_")
    cleaned = re.sub(r"[^A-Za-z0-9_ ]+", " ", cleaned)
    tokens = [tok for tok in re.split(r"[_\s]+", cleaned) if tok]

    stop_tokens = {
        "http",
        "https",
        "html",
        "www",
        "com",
        "news",
        "story",
        "article",
        "read",
        "nnn",
        "cn",
        "que"
    }
    filtered = [tok for tok in tokens if tok.lower() not in stop_tokens]
    chosen = filtered[:max_terms] if filtered else tokens[:max_terms]
    label = " ".join(chosen).strip()
    if not label:
        label = cleaned[:max_len].strip()
    if len(label) > max_len:
        label = label[: max_len - 1].rstrip() + "…"
    return label.title()


def add_topic_labels(df: pd.DataFrame, source_col: str = "Name", target_col: str = "topic_label") -> pd.DataFrame:
    labeled = df.copy()
    labeled[target_col] = labeled[source_col].apply(shorten_topic_name)
    return labeled


def _cluster_id_from_col(col: str) -> int:
    return int(col.split("_")[1])


def get_cluster_approval_columns(df: pd.DataFrame) -> list[str]:
    return sorted(
        [col for col in df.columns if col.startswith("cluster_") and col.endswith("_approval")],
        key=_cluster_id_from_col,
    )


def add_topic_display_labels(
    df: pd.DataFrame,
    label_col: str = "topic_label",
    topic_col: str = "topic",
    target_col: str = "topic_display_label",
) -> pd.DataFrame:
    """Add a plot-safe topic label while preserving the clean topic label.

    BERTopic names can collapse to the same cleaned label for multiple topic
    ids. Pandas categoricals and paper plots need unique y-axis labels, so only
    duplicated labels get a compact topic-id suffix.
    """
    labeled = df.copy()
    if label_col not in labeled.columns:
        return labeled
    labeled[target_col] = labeled[label_col].fillna("Unknown").astype(str)
    if topic_col not in labeled.columns:
        return labeled

    topic_labels = labeled[[topic_col, label_col]].drop_duplicates()
    duplicated_labels = topic_labels.loc[
        topic_labels.duplicated(label_col, keep=False), label_col
    ].dropna().unique()
    duplicate_mask = labeled[label_col].isin(duplicated_labels)
    labeled.loc[duplicate_mask, target_col] = (
        labeled.loc[duplicate_mask, label_col].astype(str)
        + " (T"
        + labeled.loc[duplicate_mask, topic_col].astype(str)
        + ")"
    )
    return labeled


def add_cluster_range_metrics(df: pd.DataFrame, avg_prefix: str = "avg_") -> pd.DataFrame:
    """Add n-cluster disagreement metrics as max-minus-min approval range."""
    enriched = df.copy()
    cluster_cols = get_cluster_approval_columns(enriched)
    if avg_prefix:
        cluster_cols = [
            col
            for col in enriched.columns
            if col.startswith(f"{avg_prefix}cluster_")
        ]
        cluster_cols = sorted(cluster_cols, key=lambda col: int(col.split("_")[2]))

    if len(cluster_cols) < 2:
        return enriched

    values = enriched[cluster_cols].astype(float)
    enriched["approval_max"] = values.max(axis=1)
    enriched["approval_min"] = values.min(axis=1)
    enriched["approval_range"] = enriched["approval_max"] - enriched["approval_min"]
    enriched["abs_gap"] = enriched["approval_range"]

    max_col = values.idxmax(axis=1)
    min_col = values.idxmin(axis=1)
    if avg_prefix:
        enriched["top_cluster"] = max_col.str.extract(r"avg_cluster_(\d+)")[0].astype("Int64")
        enriched["bottom_cluster"] = min_col.str.extract(r"avg_cluster_(\d+)")[0].astype("Int64")
    else:
        enriched["top_cluster"] = max_col.str.extract(r"cluster_(\d+)_approval")[0].astype("Int64")
        enriched["bottom_cluster"] = min_col.str.extract(r"cluster_(\d+)_approval")[0].astype("Int64")

    if avg_prefix:
        cluster_pairs = [
            (int(col.rsplit("_", 1)[1]), col)
            for col in cluster_cols
        ]
    else:
        cluster_pairs = [
            (_cluster_id_from_col(col), col)
            for col in cluster_cols
        ]
    for left_idx, (left_id, left_col) in enumerate(cluster_pairs):
        for right_id, right_col in cluster_pairs[left_idx + 1 :]:
            enriched[f"approval_gap_{left_id}_{right_id}"] = enriched[left_col] - enriched[right_col]
    if "approval_gap_0_1" in enriched.columns:
        enriched["approval_gap"] = enriched["approval_gap_0_1"]
    return enriched


def prepare_topic_frame(scores: pd.DataFrame) -> pd.DataFrame:
    required = ["noteId", "summary", "total_votes"]
    cluster_cols = get_cluster_approval_columns(scores)
    use_cols = required + cluster_cols
    topic_df = (
        scores.dropna(subset=["summary"])
        .loc[:, use_cols]
        .drop_duplicates(subset=["noteId"])
        .reset_index(drop=True)
    )
    topic_df["summary"] = topic_df["summary"].str.replace(
        r"https?://\S+|www\.\S+", " ", regex=True
    ).str.strip()
    return add_cluster_range_metrics(topic_df, avg_prefix="")


_EXTRA_STOP_WORDS = {
    # Spanish function words
    "de", "que", "el", "la", "los", "las", "en", "un", "una",
    "es", "se", "del", "al", "con", "por", "para", "le", "su",
    # URL / web fragments
    "http", "https", "www", "com", "html", "co", "net", "org",
    "httpswww", "httpstwitter", "httpst",
    # Generic Twitter noise
    "rt", "via", "amp",
}


def fit_topic_model(topic_df: pd.DataFrame, embedding_model_name: str, random_state: int = 42):
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.feature_extraction import text as sk_text
    from umap import UMAP

    texts = topic_df["summary"].astype(str).tolist()
    embedder = SentenceTransformer(embedding_model_name)
    embeddings = embedder.encode(texts, show_progress_bar=True)
    umap_model = UMAP(
        n_neighbors=15,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=random_state,
    )
    all_stops = list(sk_text.ENGLISH_STOP_WORDS.union(_EXTRA_STOP_WORDS))
    vectorizer_model = CountVectorizer(
        stop_words=all_stops,
        min_df=2,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[A-Za-z][A-Za-z]{2,}\b",
    )
    topic_model = BERTopic(
        umap_model=umap_model,
        vectorizer_model=vectorizer_model,
        calculate_probabilities=False,
        verbose=True,
    )
    topics, probs = topic_model.fit_transform(texts, embeddings)
    enriched = topic_df.copy()
    enriched["topic"] = topics
    enriched["topic_probability"] = probs if probs is not None else None
    return topic_model, enriched


def attach_topic_names(topic_model, topic_df: pd.DataFrame) -> pd.DataFrame:
    topic_info = topic_model.get_topic_info()[["Topic", "Name"]].copy()
    merged = topic_df.merge(topic_info, left_on="topic", right_on="Topic", how="left")
    return add_topic_labels(merged, source_col="Name", target_col="topic_label")


def build_topic_cluster_stats(topic_notes: pd.DataFrame) -> pd.DataFrame:
    cluster_cols = get_cluster_approval_columns(topic_notes)
    agg_map: dict[str, tuple[str, str]] = {
        "notes": ("noteId", "nunique"),
        "avg_votes": ("total_votes", "mean"),
    }
    for col in cluster_cols:
        cluster_id = _cluster_id_from_col(col)
        agg_map[f"avg_cluster_{cluster_id}"] = (col, "mean")

    topic_cluster_stats = (
        topic_notes[topic_notes["topic"] != -1]
        .groupby(["topic", "Name"])
        .agg(**agg_map)
        .reset_index()
    )
    topic_cluster_stats = add_cluster_range_metrics(topic_cluster_stats, avg_prefix="avg_")
    topic_cluster_stats = add_topic_labels(topic_cluster_stats, source_col="Name", target_col="topic_label")
    topic_cluster_stats = add_topic_display_labels(topic_cluster_stats)
    return topic_cluster_stats.sort_values("abs_gap", ascending=False)


def build_topic_exemplars(
    topic_notes: pd.DataFrame,
    topic_cluster_stats: pd.DataFrame,
    top_k_topics: int = 10,
    top_k_exemplars: int = 5,
) -> pd.DataFrame:
    top_topics = topic_cluster_stats.head(top_k_topics)["topic"].tolist()
    exemplars = (
        topic_notes[topic_notes["topic"].isin(top_topics)]
        .sort_values(["topic", "abs_gap", "total_votes"], ascending=[True, False, False])
        .groupby("topic")
        .head(top_k_exemplars)
        .reset_index(drop=True)
    )
    return exemplars


def build_topic_salience(df_clustered: pd.DataFrame, note_topic_map: pd.DataFrame) -> pd.DataFrame:
    ratings_with_topic = df_clustered.merge(note_topic_map, on="noteId", how="inner")
    group_cols = ["topic", "Name", "cluster"]
    if "topic_label" in ratings_with_topic.columns:
        group_cols.insert(2, "topic_label")
    if "topic_display_label" in ratings_with_topic.columns:
        insert_at = 3 if "topic_label" in group_cols else 2
        group_cols.insert(insert_at, "topic_display_label")
    topic_salience_df = (
        ratings_with_topic.groupby(group_cols)
        .agg(
            total_ratings=("vote", "count"),
            unique_users=("raterParticipantId", "nunique"),
            unique_notes=("noteId", "nunique"),
            positive_votes=("vote", "sum"),
            negative_votes=("vote", lambda x: (x == 0).sum()),
        )
        .reset_index()
    )
    topic_salience_df["ratings_per_user"] = (
        topic_salience_df["total_ratings"] / topic_salience_df["unique_users"]
    )
    topic_salience_df["positive_rate"] = (
        topic_salience_df["positive_votes"] / topic_salience_df["total_ratings"]
    )
    return topic_salience_df


def build_salience_pivot(topic_salience_df: pd.DataFrame) -> pd.DataFrame:
    index_cols = ["topic", "Name"]
    if "topic_label" in topic_salience_df.columns:
        index_cols.append("topic_label")
    if "topic_display_label" in topic_salience_df.columns:
        index_cols.append("topic_display_label")
    pivot = (
        topic_salience_df.pivot_table(
            index=index_cols,
            columns="cluster",
            values=["total_ratings", "unique_users", "ratings_per_user", "positive_rate"],
            aggfunc="first",
        )
    )
    pivot.columns = [f"{metric}_cluster_{int(cluster)}" for metric, cluster in pivot.columns]
    pivot = pivot.reset_index()

    for metric in ["total_ratings", "unique_users", "ratings_per_user", "positive_rate"]:
        metric_cols = sorted(
            [col for col in pivot.columns if col.startswith(f"{metric}_cluster_")],
            key=lambda col: int(col.rsplit("_", 1)[1]),
        )
        if len(metric_cols) >= 2:
            pivot[f"{metric}_range"] = pivot[metric_cols].max(axis=1) - pivot[metric_cols].min(axis=1)
        metric_pairs = [
            (int(col.rsplit("_", 1)[1]), col)
            for col in metric_cols
        ]
        for left_idx, (left_id, left_col) in enumerate(metric_pairs):
            for right_id, right_col in metric_pairs[left_idx + 1 :]:
                pivot[f"{metric}_delta_{right_id}_minus_{left_id}"] = pivot[right_col] - pivot[left_col]
    return pivot


def build_topic_rescue_stats(scores: pd.DataFrame, note_topic_map: pd.DataFrame, bridge_threshold: float) -> pd.DataFrame:
    rescue_df = scores.merge(note_topic_map, on="noteId", how="inner")
    rescue_df["is_consensus"] = rescue_df["bridge_score"] > bridge_threshold
    rescue_df["is_published"] = rescue_df["currentStatus"].eq("CURRENTLY_RATED_HELPFUL")
    rescue_df["is_consensus_failure"] = rescue_df["is_consensus"] & (~rescue_df["is_published"])

    topic_rescue_df = (
        rescue_df.groupby(["topic", "Name"])
        .agg(
            notes=("noteId", "nunique"),
            avg_votes=("total_votes", "mean"),
            consensus_notes=("is_consensus", "sum"),
            consensus_failures=("is_consensus_failure", "sum"),
        )
        .reset_index()
    )
    topic_rescue_df["failure_rate_within_consensus"] = (
        topic_rescue_df["consensus_failures"] / topic_rescue_df["consensus_notes"].clip(lower=1)
    )
    topic_rescue_df = add_topic_labels(topic_rescue_df, source_col="Name", target_col="topic_label")
    return topic_rescue_df.sort_values("failure_rate_within_consensus", ascending=False)


def build_topic_strategy_summary(
    selection_log: pd.DataFrame,
    note_topic_map: pd.DataFrame,
) -> pd.DataFrame:
    topic_lookup = note_topic_map.rename(columns={"noteId": "selected_noteId"})
    strategy_topic_df = selection_log.merge(topic_lookup, on="selected_noteId", how="left")
    strategy_topic_df = strategy_topic_df[strategy_topic_df["topic"].ne(-1)].copy()
    group_cols = ["strategy", "topic", "Name", "status_group"]
    if "topic_label" in strategy_topic_df.columns:
        group_cols.insert(3, "topic_label")
    if "topic_display_label" in strategy_topic_df.columns:
        insert_at = 4 if "topic_label" in group_cols else 3
        group_cols.insert(insert_at, "topic_display_label")

    summary = (
        strategy_topic_df.assign(
            status_group=lambda x: np.where(
                x["status"].eq("CURRENTLY_RATED_HELPFUL"),
                "Helpful",
                np.where(x["status"].eq("NEEDS_MORE_RATINGS"), "NMR", "Other"),
            )
        )
        .groupby(group_cols)
        .agg(
            selected_picks=("selected_noteId", "count"),
            unique_tweets=("tweetId", "nunique"),
            unique_notes=("selected_noteId", "nunique"),
            avg_global_approval=("global_approval", "mean"),
            avg_bridge_score=("bridge_score", "mean"),
        )
        .reset_index()
    )
    if "topic_label" not in summary.columns:
        summary = add_topic_labels(summary, source_col="Name", target_col="topic_label")
    if "topic_display_label" not in summary.columns:
        summary = add_topic_display_labels(summary)
    return summary.sort_values(["strategy", "selected_picks"], ascending=[True, False])


def build_strategy_topic_pivot(
    topic_strategy_summary: pd.DataFrame,
    value_col: str = "selected_picks",
) -> pd.DataFrame:
    pivot = (
        topic_strategy_summary.pivot_table(
            index=[col for col in ["topic", "Name", "topic_label", "topic_display_label"] if col in topic_strategy_summary.columns],
            columns="strategy",
            values=value_col,
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    if "topic_label" not in pivot.columns:
        pivot = add_topic_labels(pivot, source_col="Name", target_col="topic_label")
    if "topic_display_label" not in pivot.columns:
        pivot = add_topic_display_labels(pivot)
    return pivot


def build_topic_selection_overlap(
    selection_log: pd.DataFrame,
    note_topic_map: pd.DataFrame,
    compare_to: str = "Simple Majoritarian Rule",
) -> pd.DataFrame:
    topic_lookup = note_topic_map.rename(columns={"noteId": "selected_noteId"})
    enriched = selection_log.merge(topic_lookup, on="selected_noteId", how="left")
    enriched = enriched[enriched["topic"].ne(-1)].copy()

    reference_map = (
        enriched[enriched["strategy"] == compare_to][["tweetId", "topic", "selected_noteId"]]
        .drop_duplicates(subset=["tweetId", "topic"])
        .rename(columns={"selected_noteId": "reference_noteId"})
    )

    rows: list[dict[str, object]] = []
    for strategy, strategy_df in enriched.groupby("strategy"):
        if strategy == compare_to:
            continue
        merged = strategy_df.merge(reference_map, on=["tweetId", "topic"], how="inner")
        if merged.empty:
            continue
        topic_summary = (
            merged.assign(matches_reference=lambda x: x["selected_noteId"].eq(x["reference_noteId"]))
            .groupby(
                [
                    col
                    for col in ["strategy", "topic", "Name", "topic_label", "topic_display_label"]
                    if col in merged.columns
                ]
            )
            .agg(
                overlap_rate=("matches_reference", "mean"),
                matching_rows=("matches_reference", "sum"),
                total_rows=("matches_reference", "size"),
            )
            .reset_index()
        )
        rows.append(topic_summary)

    if not rows:
        return pd.DataFrame(
            columns=[
                "strategy",
                "topic",
                "Name",
                "topic_label",
                "topic_display_label",
                "overlap_rate",
                "matching_rows",
                "total_rows",
            ]
        )
    combined = pd.concat(rows, ignore_index=True).sort_values(
        ["strategy", "overlap_rate"], ascending=[True, False]
    )
    if "topic_label" not in combined.columns:
        combined = add_topic_labels(combined, source_col="Name", target_col="topic_label")
    if "topic_display_label" not in combined.columns:
        combined = add_topic_display_labels(combined)
    return combined
