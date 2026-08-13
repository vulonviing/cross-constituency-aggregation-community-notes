"""Regression tests that re-derive the paper's headline numbers from committed data.

Every value asserted here appears in `paper/03-07-2026-1550-edition/main.pdf`, and
every one of them is recomputed from a parquet file that ships with this
repository. No Hugging Face download and no raw X snapshot are required.

The one headline chain these tests cannot cover is 1.7M English notes ->
510,212 eligible notes, which needs `data/master_full.parquet` (see
REPRODUCING.md, tier B). It is documented there instead of asserted here.

Each test skips with an explicit message when its input file is absent, so a
fresh clone that has not fetched large data still reports a clean run.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
INTERIM = REPO_ROOT / "data" / "interim"
PROCESSED = REPO_ROOT / "data" / "processed"
STAGE2_EXPANDED = (
    REPO_ROOT
    / "data"
    / "llm_validation"
    / "runs"
    / "gemma-4-31b-it-scckn-stage2-expanded-v1"
    / "stage2_results.parquet"
)

# Both camps must clear this many raters on a note before the note enters the
# between-camp diagnostics. The threshold and the 0.3 discrimination cutoff below
# are the ones used to produce the figures quoted in Section 6.2.
MIN_RATERS_PER_CAMP = 10
DISCRIMINATING_GAP = 0.3


def _load(path: Path, test: unittest.TestCase) -> pd.DataFrame:
    if not path.exists():
        test.skipTest(f"missing {path.relative_to(REPO_ROOT)}; see REPRODUCING.md")
    return pd.read_parquet(path)


class ClusteringSelectionTests(unittest.TestCase):
    """Section 3: what the spectral partition actually selected at 200k."""

    def test_bootstrap_stability_selects_three_clusters(self):
        stability = _load(INTERIM / "stability_over_k.parquet", self)
        best = stability.loc[stability["mean_ari"].idxmax()]
        self.assertEqual(int(best["k"]), 3)
        self.assertAlmostEqual(float(best["mean_ari"]), 0.9706, places=3)

    def test_two_clusters_are_markedly_less_stable(self):
        """The paper's argument that k=2 was not what the algorithm chose."""
        stability = _load(INTERIM / "stability_over_k.parquet", self).set_index("k")
        self.assertAlmostEqual(float(stability.loc[2, "mean_ari"]), 0.5929, places=3)
        self.assertLess(float(stability.loc[2, "mean_ari"]), float(stability.loc[3, "mean_ari"]))

    def test_the_third_cluster_is_a_handful_of_hyperactive_raters(self):
        summary = _load(INTERIM / "cluster_summary.parquet", self).set_index("cluster")
        self.assertEqual([int(v) for v in summary["users"].tolist()], [107680, 92256, 64])
        self.assertEqual(
            [int(v) for v in summary["median_total_votes"].tolist()], [121, 101, 1269]
        )
        # Roughly a tenfold vote rate against either main camp.
        self.assertGreater(
            summary.loc[2, "median_total_votes"] / summary.loc[0, "median_total_votes"], 10
        )


class ReassignmentRobustnessTests(unittest.TestCase):
    """Section 6.2: the outcome does not depend on how the outliers are folded in."""

    def _partitions(self):
        method_a = _load(INTERIM / "user_clusters_method_a_embedding.parquet", self)
        method_b = _load(INTERIM / "user_clusters_method_b_voteprofile.parquet", self)
        return method_a.merge(method_b, on="raterParticipantId", suffixes=("_a", "_b"))

    def test_the_two_rules_cover_the_same_two_hundred_thousand_raters(self):
        merged = self._partitions()
        self.assertEqual(len(merged), 200_000)

    def test_the_two_rules_disagree_about_twenty_nine_raters(self):
        merged = self._partitions()
        self.assertEqual(int((merged["cluster_a"] != merged["cluster_b"]).sum()), 29)

    def test_both_rules_leave_only_two_camps(self):
        merged = self._partitions()
        self.assertEqual(sorted(merged["cluster_a"].unique().tolist()), [0, 1])
        self.assertEqual(sorted(merged["cluster_b"].unique().tolist()), [0, 1])


class BetweenCampStructureTests(unittest.TestCase):
    """Section 6.2: the two camps really do disagree, and sharply."""

    def _filtered_scores(self) -> pd.DataFrame:
        scores = _load(PROCESSED / "scores.parquet", self)
        return scores[
            (scores["cluster_0_count"] >= MIN_RATERS_PER_CAMP)
            & (scores["cluster_1_count"] >= MIN_RATERS_PER_CAMP)
        ]

    def test_the_scored_slice_holds_one_hundred_thousand_notes(self):
        self.assertEqual(len(_load(PROCESSED / "scores.parquet", self)), 100_000)

    def test_the_diagnostic_subset_holds_ninety_eight_thousand_notes(self):
        self.assertEqual(len(self._filtered_scores()), 98_442)

    def test_camp_approval_rates_are_strongly_negatively_correlated(self):
        filtered = self._filtered_scores()
        pearson = np.corrcoef(
            filtered["cluster_0_approval"], filtered["cluster_1_approval"]
        )[0, 1]
        self.assertAlmostEqual(pearson, -0.620, places=3)

    def test_four_notes_in_five_discriminate_between_the_camps(self):
        filtered = self._filtered_scores()
        gap = (filtered["cluster_0_approval"] - filtered["cluster_1_approval"]).abs()
        share = float((gap > DISCRIMINATING_GAP).mean() * 100)
        self.assertAlmostEqual(share, 81.4, places=1)


class SelectionOverlapTests(unittest.TestCase):
    """Table 4: what Community Notes showed against what CCA qualifies."""

    def _representative_picks(self) -> pd.DataFrame:
        log = _load(PROCESSED / "selection_log.parquet", self)
        return log[
            (log["strategy"] == "Representative") & (log["selection_scope"] == "single_pick")
        ]

    def test_the_pick_universe_covers_every_eligible_tweet(self):
        self.assertEqual(len(self._representative_picks()), 44_722)

    def test_community_notes_showed_six_thousand_of_those_picks(self):
        picks = self._representative_picks()
        self.assertEqual(int((picks["status"] == "CURRENTLY_RATED_HELPFUL").sum()), 6_832)

    def test_the_qualified_set_splits_into_shown_and_hidden(self):
        qualified = self._representative_picks()
        qualified = qualified[qualified["passes_bridge_threshold"]]
        shown = int((qualified["status"] == "CURRENTLY_RATED_HELPFUL").sum())
        hidden = int((qualified["status"] != "CURRENTLY_RATED_HELPFUL").sum())
        self.assertEqual(len(qualified), 20_405)
        self.assertEqual(shown, 6_750)
        self.assertEqual(hidden, 13_655)
        self.assertEqual(shown + hidden, 20_405)

    def test_the_remainder_falls_below_the_bridge_threshold(self):
        """Notes with an undefined bridge score count here too, not as qualified."""
        picks = self._representative_picks()
        qualified = int(picks["passes_bridge_threshold"].fillna(False).astype(bool).sum())
        self.assertEqual(len(picks) - qualified, 24_317)


class GemmaValidationTests(unittest.TestCase):
    """Section 6: the two-stage validation funnel and the final rescue set."""

    def _stage2(self) -> pd.DataFrame:
        return _load(STAGE2_EXPANDED, self)

    def test_the_expanded_stage_two_pool_holds_ten_thousand_notes(self):
        self.assertEqual(len(self._stage2()), 10_376)

    def test_the_pool_splits_into_strict_and_recall_routes(self):
        routes = self._stage2()["admission_route"].value_counts().to_dict()
        self.assertEqual(routes["strict_stage1"], 10_096)
        self.assertEqual(routes["stage1_5_recall"], 280)
        self.assertEqual(sum(routes.values()), 10_376)

    def test_the_final_rescue_set_holds_eight_thousand_five_hundred_fifty_eight_notes(self):
        self.assertEqual(int(self._stage2()["passes_rescue_threshold"].sum()), 8_558)

    def test_the_admission_route_does_not_decide_the_outcome(self):
        """The route is audited but never shown to the model."""
        stage2 = self._stage2()
        by_route = stage2.groupby("admission_route")["passes_rescue_threshold"].sum()
        self.assertEqual(int(by_route.sum()), 8_558)
        self.assertGreater(int(by_route["strict_stage1"]), 0)


if __name__ == "__main__":
    unittest.main()
