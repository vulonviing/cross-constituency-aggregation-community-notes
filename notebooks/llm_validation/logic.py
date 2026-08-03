from __future__ import annotations

from collections import Counter
from statistics import median


# ---------------------------------------------------------------------------
# Single-run helpers (STAGE1_RUNS = 1 / STAGE2_RUNS = 1 mode)
# ---------------------------------------------------------------------------

def resolve_stage1_single(labels: list[str]) -> tuple[str, str | None]:
    """Resolve Stage 1 with any non-zero number of labels.

    In single-run mode the first (and only) label is final.  With legacy
    3-run data already in the DB, the mode is used so the function is safe
    to call on 3- or 6-call notes without changing their resolved label.
    Returns ("pending", None) if no labels are available.
    """
    if not labels:
        return "pending", None
    return "resolved", Counter(labels).most_common(1)[0][0]


def resolve_stage2_single(scores: list[int]) -> float | None:
    """Return the single score (or median of any already-stored scores) as a float."""
    if not scores:
        return None
    return float(median(scores))


# ---------------------------------------------------------------------------
# Ensemble helpers (STAGE1_RUNS >= 3 mode)
# ---------------------------------------------------------------------------

def majority_of_three(votes: list[str]) -> str | None:
    if len(votes) != 3:
        return None
    counts = Counter(votes).most_common(2)
    if counts and counts[0][1] >= 2:
        return counts[0][0]
    return None


def resolve_stage1(
    round1_votes: list[str], round2_votes: list[str] | None = None
) -> tuple[str, str | None]:
    first = majority_of_three(round1_votes)
    if first is not None:
        return "resolved", first
    if len(round1_votes) < 3:
        return "pending", None
    if round2_votes is None or len(round2_votes) < 3:
        return "needs_rerun", None
    second = majority_of_three(round2_votes)
    if second is not None:
        return "resolved", second
    return "unresolved", None


def resolve_stage2(scores: list[int]) -> float | None:
    if len(scores) != 3:
        return None
    return float(median(scores))
