"""Unit tests for the scoring rules that implement Cross-Constituency Aggregation.

These tests use small synthetic frames only; they never touch repository data, so
they run on a fresh clone with nothing downloaded. Each test pins one property the
paper argues for, so a silent change in the aggregation rule breaks a named claim
rather than only a number.
"""

from __future__ import annotations

import math
import unittest

import numpy as np
import pandas as pd

from src.config import ScoringConfig
from src.scoring import (
    compute_note_scores,
    geometric_mean,
    get_cluster_approval_columns,
    simulate_models,
)


def _rating_rows(note_id, tweet_id, cluster, votes, status, classification="MISINFORMED_OR_POTENTIALLY_MISLEADING"):
    """Expand one (note, cluster) block into individual rating rows."""
    return [
        {
            "noteId": note_id,
            "tweetId": tweet_id,
            "cluster": cluster,
            "vote": vote,
            "currentStatus": status,
            "classification": classification,
            "summary": f"text of {note_id}",
        }
        for vote in votes
    ]


def build_fixture() -> pd.DataFrame:
    """A five-note universe covering every branch of the coverage rule.

    A  tweet T1  3 approvals from each camp                -> bridge defined, 1.0
    B  tweet T1  3 from camp 0, only 2 from camp 1         -> camp 1 below the floor
    C  tweet T2  3 from camp 0, none at all from camp 1    -> camp 1 absent
    D  tweet T2  2 ratings in total                        -> below the note minimum
    E  tweet T3  camp 0 unanimous yes, camp 1 unanimous no -> maximal disagreement
    """
    rows = []
    rows += _rating_rows("A", "T1", 0, [1, 1, 1], "NEEDS_MORE_RATINGS")
    rows += _rating_rows("A", "T1", 1, [1, 1, 1], "NEEDS_MORE_RATINGS")
    rows += _rating_rows("B", "T1", 0, [1, 1, 1], "NEEDS_MORE_RATINGS")
    rows += _rating_rows("B", "T1", 1, [1, 1], "NEEDS_MORE_RATINGS")
    rows += _rating_rows("C", "T2", 0, [1, 1, 1], "NEEDS_MORE_RATINGS")
    rows += _rating_rows("D", "T2", 0, [1, 1], "NEEDS_MORE_RATINGS")
    rows += _rating_rows("E", "T3", 0, [1, 1, 1, 1], "NEEDS_MORE_RATINGS")
    rows += _rating_rows("E", "T3", 1, [0, 0, 0, 0], "NEEDS_MORE_RATINGS")
    return pd.DataFrame(rows)


class GeometricMeanTests(unittest.TestCase):
    """P2, non-compensation: a veto cannot be bought off by the other camp."""

    def test_agreement_is_returned_unchanged(self):
        frame = pd.DataFrame({"c0": [0.8], "c1": [0.8]})
        self.assertAlmostEqual(float(geometric_mean(frame).iloc[0]), 0.8, places=6)

    def test_it_is_the_geometric_not_the_arithmetic_mean(self):
        frame = pd.DataFrame({"c0": [1.0], "c1": [0.25]})
        value = float(geometric_mean(frame).iloc[0])
        self.assertAlmostEqual(value, 0.5, places=6)
        self.assertNotAlmostEqual(value, 0.625, places=3)

    def test_a_single_rejection_collapses_the_score(self):
        frame = pd.DataFrame({"c0": [1.0], "c1": [0.0]})
        value = float(geometric_mean(frame, eps=1e-6).iloc[0])
        self.assertLess(value, 1e-2)
        self.assertGreater(value, 0.0)

    def test_it_is_symmetric_in_its_arguments(self):
        """P3, symmetry: relabeling the camps must not move the score."""
        forward = pd.DataFrame({"c0": [0.9], "c1": [0.3]})
        reversed_ = pd.DataFrame({"c0": [0.3], "c1": [0.9]})
        self.assertAlmostEqual(
            float(geometric_mean(forward).iloc[0]),
            float(geometric_mean(reversed_).iloc[0]),
            places=12,
        )

    def test_it_penalizes_disagreement_relative_to_averaging(self):
        """The score sits between the weaker camp and the arithmetic mean.

        Staying at or below the arithmetic mean is what makes disagreement
        costly; staying at or above the weaker camp is what keeps the rule from
        being a pure minimum.
        """
        rng = np.random.default_rng(0)
        frame = pd.DataFrame(rng.uniform(0.01, 1.0, size=(200, 2)), columns=["c0", "c1"])
        scores = geometric_mean(frame)
        self.assertTrue((scores >= frame.min(axis=1) - 1e-9).all())
        self.assertTrue((scores <= frame.mean(axis=1) + 1e-9).all())


class CoverageRuleTests(unittest.TestCase):
    """P1, presence: every camp must actually show up before a note is scored."""

    def setUp(self):
        self.config = ScoringConfig()
        self.scores = compute_note_scores(build_fixture(), self.config).set_index("noteId")

    def test_the_floor_is_three_raters_per_camp(self):
        self.assertEqual(self.config.min_cluster_ratings, 3)
        self.assertEqual(self.config.min_note_ratings, 3)
        self.assertEqual(self.config.bridge_threshold, 0.5)

    def test_a_note_meeting_the_floor_in_both_camps_is_scored(self):
        self.assertAlmostEqual(float(self.scores.loc["A", "bridge_score"]), 1.0, places=6)

    def test_a_camp_below_the_floor_blocks_the_bridge_score(self):
        self.assertEqual(int(self.scores.loc["B", "cluster_1_count"]), 2)
        self.assertTrue(math.isnan(float(self.scores.loc["B", "bridge_score"])))

    def test_an_absent_camp_falls_back_to_neutral_but_is_not_scored(self):
        """The 0.5 fallback fills the approval rate; it must not read as support."""
        self.assertAlmostEqual(float(self.scores.loc["C", "cluster_1_approval"]), 0.5, places=6)
        self.assertEqual(int(self.scores.loc["C", "cluster_1_count"]), 0)
        self.assertTrue(math.isnan(float(self.scores.loc["C", "bridge_score"])))

    def test_notes_under_the_total_rating_minimum_are_dropped(self):
        self.assertNotIn("D", self.scores.index)

    def test_one_sided_approval_yields_a_near_zero_bridge_score(self):
        self.assertAlmostEqual(float(self.scores.loc["E", "global_approval"]), 0.5, places=6)
        self.assertLess(float(self.scores.loc["E", "bridge_score"]), 1e-2)

    def test_cluster_columns_are_discovered_in_index_order(self):
        self.assertEqual(
            get_cluster_approval_columns(self.scores.reset_index()),
            ["cluster_0_approval", "cluster_1_approval"],
        )


class SelectionTests(unittest.TestCase):
    """The display rule: a note is rescued only above the 0.5 bridge threshold."""

    def setUp(self):
        config = ScoringConfig()
        self.scores = compute_note_scores(build_fixture(), config)
        self.results = simulate_models(self.scores, config.bridge_threshold).set_index("tweetId")

    def test_a_cross_camp_note_is_rescued(self):
        self.assertTrue(bool(self.results.loc["T1", "rep_rescued"]))
        self.assertEqual(self.results.loc["T1", "representative_noteId"], "A")

    def test_a_one_sided_note_is_not_rescued(self):
        self.assertFalse(bool(self.results.loc["T3", "rep_rescued"]))

    def test_an_already_helpful_note_is_not_counted_as_a_rescue(self):
        frame = build_fixture()
        frame.loc[frame["noteId"] == "A", "currentStatus"] = "CURRENTLY_RATED_HELPFUL"
        config = ScoringConfig()
        results = simulate_models(
            compute_note_scores(frame, config), config.bridge_threshold
        ).set_index("tweetId")
        self.assertFalse(bool(results.loc["T1", "rep_rescued"]))
        self.assertTrue(bool(results.loc["T1", "simple_majoritarian_published"]))


if __name__ == "__main__":
    unittest.main()
