from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ScoringConfig


def compute_note_scores(
    df_clustered: pd.DataFrame,
    config: ScoringConfig | None = None,
) -> pd.DataFrame:
    config = config or ScoringConfig()

    global_stats = (
        df_clustered.groupby("noteId")
        .agg(
            total_votes=("vote", "count"),
            global_approval=("vote", "mean"),
            tweetId=("tweetId", "first"),
            currentStatus=("currentStatus", "first"),
            classification=("classification", "first"),
        )
        .reset_index()
    )

    cluster_stats = df_clustered.groupby(["noteId", "cluster"])["vote"].mean().unstack()
    cluster_stats.columns = [f"cluster_{int(col)}_approval" for col in cluster_stats.columns]

    # Count raters per cluster per note (for the per-cluster minimum filter)
    cluster_counts = df_clustered.groupby(["noteId", "cluster"])["vote"].count().unstack()
    cluster_counts.columns = [f"cluster_{int(col)}_count" for col in cluster_counts.columns]
    cluster_counts = cluster_counts.fillna(0).astype(int)

    # 0.5 fallback: if no raters from a cluster rated a note, assume
    # neutral approval.  This is distinct from the clustering stage,
    # where per-user mean-centering with zero-fill is used instead.
    cluster_stats = cluster_stats.fillna(0.5)

    scores = global_stats.merge(cluster_stats, on="noteId", how="left")
    scores = scores.merge(cluster_counts, on="noteId", how="left")

    note_text_lookup = (
        df_clustered[["noteId", "summary"]]
        .dropna(subset=["noteId", "summary"])
        .drop_duplicates(subset=["noteId"])
    )
    scores = scores.merge(note_text_lookup, on="noteId", how="left")
    scores = scores[scores["total_votes"] >= config.min_note_ratings].copy()

    cluster_cols = get_cluster_approval_columns(scores)
    count_cols = sorted(
        [col for col in scores.columns if col.startswith("cluster_") and col.endswith("_count")],
        key=lambda col: int(col.split("_")[1]),
    )

    # Bridge score is only meaningful when every cluster has enough raters.
    # Notes that fail the per-cluster minimum keep their cluster approvals
    # (useful for pluralistic selection) but receive bridge_score = NaN.
    has_enough = (scores[count_cols] >= config.min_cluster_ratings).all(axis=1)
    scores["bridge_score"] = np.nan
    scores.loc[has_enough, "bridge_score"] = geometric_mean(
        scores.loc[has_enough, cluster_cols], eps=config.eps
    )
    scores["mean_cluster_approval"] = scores[cluster_cols].mean(axis=1)
    scores["disagreement_std"] = scores[cluster_cols].std(axis=1)
    if len(cluster_cols) >= 2:
        scores["approval_gap_0_1"] = scores[cluster_cols[0]] - scores[cluster_cols[1]]
        scores["abs_gap_0_1"] = scores["approval_gap_0_1"].abs()
    return scores


def get_cluster_approval_columns(df: pd.DataFrame) -> list[str]:
    return sorted(
        [col for col in df.columns if col.startswith("cluster_") and col.endswith("_approval")],
        key=lambda col: int(col.split("_")[1]),
    )


def geometric_mean(df: pd.DataFrame, eps: float = 1e-6) -> pd.Series:
    return np.exp(np.mean(np.log(df.clip(eps, 1.0)), axis=1))


def compute_diagnostic_scores(scores: pd.DataFrame) -> pd.DataFrame:
    """Per-note disagreement metrics used to rank cluster-diagnostic notes.

    Adds three columns:
      - ``cluster_approval_max``  — highest cluster-conditional approval rate.
      - ``cluster_approval_min``  — lowest cluster-conditional approval rate.
      - ``cluster_approval_spread`` = max - min (the diagnostic score).

    Higher spread means the note more sharply separates the user clusters.
    Per-cluster fallbacks (``fillna(0.5)`` in :func:`compute_note_scores`) are
    deliberately *not* undone here; downstream callers can require a minimum
    per-cluster rater count via :func:`select_diagnostic_notes` to restrict
    selection to notes whose spread is supported by real signal.
    """
    result = scores.copy()
    cluster_cols = get_cluster_approval_columns(result)
    if not cluster_cols:
        result["cluster_approval_max"] = np.nan
        result["cluster_approval_min"] = np.nan
        result["cluster_approval_spread"] = np.nan
        return result
    cluster_block = result[cluster_cols]
    result["cluster_approval_max"] = cluster_block.max(axis=1)
    result["cluster_approval_min"] = cluster_block.min(axis=1)
    result["cluster_approval_spread"] = (
        result["cluster_approval_max"] - result["cluster_approval_min"]
    )
    return result


def select_diagnostic_notes(
    scores: pd.DataFrame,
    min_spread: float = 0.9,
    min_cluster_ratings: int | None = None,
    require_summary: bool = True,
) -> pd.DataFrame:
    """Notes whose between-cluster approval spread meets a minimum threshold.

    ``min_spread`` is the primary filter: only notes where
    ``cluster_approval_spread >= min_spread`` are kept. With k=2 fully-polarised
    clusters (median spread ~0.69 in the 200k run), a threshold of 0.9 selects
    the top ~10 % of notes — those where one cluster approves at ≥95 % and the
    other at ≤5 %. This is semantically motivated (Carina, 2026-05-15):
    "extract the notes most diagnostic of cluster membership; topic modeling
    can then be run only on this reduced subset."

    When ``min_cluster_ratings`` is set, notes without enough raters in every
    cluster are dropped first, preventing the 0.5 neutral-approval fallback from
    inflating spread scores.
    """
    enriched = compute_diagnostic_scores(scores)

    if min_cluster_ratings is not None:
        count_cols = sorted(
            [
                col
                for col in enriched.columns
                if col.startswith("cluster_") and col.endswith("_count")
            ],
            key=lambda col: int(col.split("_")[1]),
        )
        if count_cols:
            mask = (enriched[count_cols] >= min_cluster_ratings).all(axis=1)
            enriched = enriched.loc[mask]

    if require_summary and "summary" in enriched.columns:
        enriched = enriched.dropna(subset=["summary"])
        enriched = enriched[enriched["summary"].str.len() > 0]

    enriched = enriched.dropna(subset=["cluster_approval_spread"])
    enriched = enriched[enriched["cluster_approval_spread"] >= min_spread]
    enriched = enriched.sort_values(
        "cluster_approval_spread", ascending=False, kind="mergesort"
    )
    return enriched.reset_index(drop=True)


def simulate_models(scores: pd.DataFrame, bridge_threshold: float) -> pd.DataFrame:
    results: list[dict[str, object]] = []

    for tweet_id, group in scores.groupby("tweetId"):
        if group.empty:
            continue

        simple_majoritarian = group.sort_values("global_approval", ascending=False).iloc[0]
        simple_majoritarian_published = (
            simple_majoritarian["currentStatus"] == "CURRENTLY_RATED_HELPFUL"
        )

        valid_notes = group[group["classification"] != "NOT_NEEDED"]
        if valid_notes.empty:
            valid_notes = group

        cluster_cols = get_cluster_approval_columns(group)
        pluralistic_picks = [
            valid_notes.sort_values(cluster_col, ascending=False).iloc[0] for cluster_col in cluster_cols
        ]
        representative_pick = group.sort_values("bridge_score", ascending=False).iloc[0]

        results.append(
            {
                "tweetId": tweet_id,
                "simple_majoritarian_published": simple_majoritarian_published,
                "plur_rescued": any(
                    pick["currentStatus"] != "CURRENTLY_RATED_HELPFUL" for pick in pluralistic_picks
                ),
                "rep_rescued": (
                    representative_pick["bridge_score"] > bridge_threshold
                    and representative_pick["currentStatus"] != "CURRENTLY_RATED_HELPFUL"
                ),
                "simple_majoritarian_noteId": simple_majoritarian["noteId"],
                "representative_noteId": representative_pick["noteId"],
                "representative_bridge_score": representative_pick["bridge_score"],
            }
        )

    return pd.DataFrame(results)


def build_model_counts(res_df: pd.DataFrame) -> dict[str, int]:
    return {
        "Simple Majoritarian Rule": int(res_df["simple_majoritarian_published"].sum()),
        "Pluralistic-K (Total Visible)": int(
            res_df["simple_majoritarian_published"].sum() + res_df["plur_rescued"].sum()
        ),
        "Representative (Total Visible)": int(
            res_df["simple_majoritarian_published"].sum() + res_df["rep_rescued"].sum()
        ),
    }


def build_analysis_table(scores: pd.DataFrame) -> pd.DataFrame:
    table_df = scores.copy()
    cluster_cols = get_cluster_approval_columns(table_df)
    table_df = table_df.dropna(subset=cluster_cols).copy()

    table_df["Bridge Score"] = geometric_mean(table_df[cluster_cols])
    table_df["Twitter's Label"] = table_df["currentStatus"]
    table_df["Disagreement (std)"] = table_df[cluster_cols].std(axis=1)
    table_df["Mean cluster approval"] = table_df[cluster_cols].mean(axis=1)

    rename_map = {"tweetId": "Tweet ID", "noteId": "Note"}
    table_df = table_df.rename(columns=rename_map)

    for idx, cluster_col in enumerate(cluster_cols):
        table_df[f"Cluster {idx} score"] = table_df[cluster_col]

    ordered_cols = ["Tweet ID", "Note", "summary", "global_approval", "Bridge Score", "Disagreement (std)"]
    ordered_cols += [f"Cluster {idx} score" for idx in range(len(cluster_cols))]
    ordered_cols += ["Twitter's Label", "classification", "total_votes"]
    existing = [col for col in ordered_cols if col in table_df.columns]
    remaining = [col for col in table_df.columns if col not in existing]
    return table_df.loc[:, existing + remaining]


def build_pluralistic_breakdown(scores: pd.DataFrame) -> pd.DataFrame:
    rescued_by_cluster: dict[str, int] = {}
    for _, group in scores.groupby("tweetId"):
        if group.empty:
            continue
        valid_notes = group[group["classification"] != "NOT_NEEDED"]
        if valid_notes.empty:
            valid_notes = group
        for cluster_col in get_cluster_approval_columns(group):
            pick = valid_notes.sort_values(cluster_col, ascending=False).iloc[0]
            rescued_by_cluster.setdefault(cluster_col, 0)
            rescued_by_cluster[cluster_col] += int(pick["currentStatus"] != "CURRENTLY_RATED_HELPFUL")

    return pd.DataFrame(
        {
            "cluster_col": list(rescued_by_cluster.keys()),
            "rescued_tweets": list(rescued_by_cluster.values()),
        }
    )


def summarize_model_selections(scores: pd.DataFrame, bridge_threshold: float) -> pd.DataFrame:
    selection_rows: list[dict[str, object]] = []

    for tweet_id, group in scores.groupby("tweetId"):
        if group.empty:
            continue

        valid_notes = group[group["classification"] != "NOT_NEEDED"]
        if valid_notes.empty:
            valid_notes = group

        simple_majoritarian = group.sort_values("global_approval", ascending=False).iloc[0]
        selection_rows.append(
            {
                "tweetId": tweet_id,
                "strategy": "Simple Majoritarian Rule",
                "selection_scope": "single_pick",
                "selected_noteId": simple_majoritarian["noteId"],
                "status": simple_majoritarian["currentStatus"],
                "global_approval": simple_majoritarian["global_approval"],
                "bridge_score": simple_majoritarian["bridge_score"],
            }
        )

        representative = group.sort_values("bridge_score", ascending=False).iloc[0]
        selection_rows.append(
            {
                "tweetId": tweet_id,
                "strategy": "Representative",
                "selection_scope": "single_pick",
                "selected_noteId": representative["noteId"],
                "status": representative["currentStatus"],
                "global_approval": representative["global_approval"],
                "bridge_score": representative["bridge_score"],
                "passes_bridge_threshold": representative["bridge_score"] > bridge_threshold,
            }
        )

        pluralistic_picks = []
        for cluster_col in get_cluster_approval_columns(group):
            pick = valid_notes.sort_values(cluster_col, ascending=False).iloc[0]
            cluster_name = cluster_col.replace("_approval", "").replace("_", " ").title()
            selection_rows.append(
                {
                    "tweetId": tweet_id,
                    "strategy": cluster_name,
                    "selection_scope": "cluster_pick",
                    "selected_noteId": pick["noteId"],
                    "status": pick["currentStatus"],
                    "global_approval": pick["global_approval"],
                    "bridge_score": pick["bridge_score"],
                    "selection_metric": cluster_col,
                    "selection_score": pick[cluster_col],
                }
            )
            pluralistic_picks.append(pick)

        for pick in pluralistic_picks:
            selection_rows.append(
                {
                    "tweetId": tweet_id,
                    "strategy": "Pluralistic-K",
                    "selection_scope": "all_cluster_picks",
                    "selected_noteId": pick["noteId"],
                    "status": pick["currentStatus"],
                    "global_approval": pick["global_approval"],
                    "bridge_score": pick["bridge_score"],
                }
            )

    return pd.DataFrame(selection_rows)


def build_selection_status_summary(selection_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        selection_df.assign(
            status_group=lambda x: np.where(
                x["status"].eq("CURRENTLY_RATED_HELPFUL"),
                "Helpful",
                np.where(x["status"].eq("NEEDS_MORE_RATINGS"), "NMR", "Other"),
            )
        )
        .groupby(["strategy", "status_group"])
        .agg(
            selected_picks=("selected_noteId", "count"),
            unique_tweets=("tweetId", "nunique"),
            unique_notes=("selected_noteId", "nunique"),
            avg_global_approval=("global_approval", "mean"),
            avg_bridge_score=("bridge_score", "mean"),
        )
        .reset_index()
    )

    totals = (
        summary.groupby("strategy")["selected_picks"]
        .sum()
        .rename("total_selected_picks")
        .reset_index()
    )
    summary = summary.merge(totals, on="strategy", how="left")
    summary["share_within_strategy"] = summary["selected_picks"] / summary["total_selected_picks"]
    return summary
