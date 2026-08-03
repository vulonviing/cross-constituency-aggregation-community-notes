# Goyal et al. (2026): Real Contribution Is ρ, Not i_u

- **Date:** 2026-06-26 14:48 +0200
- **Source:** Paper discussion — Conceptual Map analogy revision

## Context
In the Conceptual Map section, the "teacher with few notes" analogy had been
attributed to Goyal. However, examining the body of the Goyal paper (arXiv
2604.11224), it became clear that Goyal draws an explicit orthogonality line
between the rater intercept `i_u` (strictness/generosity) and his own contribution
ρ (quality-sensitivity). The paper distinguishes its novelty as follows: "rater
baseline: μ+αᵢ, quality channel: ρᵢβⱼ, ideology channel: γᵢδⱼ." The school/teacher
analogy does not appear anywhere in the paper. This note was created so that
Goyal's real contribution is not lost when the analogy is removed from the section.

## Idea
Goyal's main novelty is **ρ (per-rater quality-sensitivity parameter)**:
- Not `i_u` (being strict or lenient = strictness).
- Definition: "ρ̂ᵢ measures the magnitude of quality tracking — how strongly rater i's
  de-ideologized ratings respond to note quality."
- Practical effect: raters whose historically de-ideologized votes have consistently
  tracked true quality receive more weight in quality estimation. The baseline model
  weights all raters equally; QSMF breaks this assumption.
- Result: the same accuracy with 26–40% fewer ratings, and meaningfully more resistant
  to coordinated attacks.

## Why It Matters
1. **Supports our thesis, but from a different level.** Even Goyal's solution advances
   the algorithm in the direction of "estimate rater reliability," not "evaluate
   content." Goyal is therefore a sub-case of our profiling/intent-reading critique:
   it makes the base model's rater-judging mechanism *more sophisticated*, not
   abandons it.
2. **Confirms the hyperactive minority vulnerability.** The base model's assumption of
   "equal weight for all raters" is precisely Goyal's attack surface; this is a
   different manifestation of the same structural weakness that Nudo identifies.
3. **Can be framed as a contrasting approach to CCA.** Goyal filters by quality by
   asking "whose vote should we trust?" Our CCA asks "which constituency is
   approving?" The two are not mutually exclusive, but their priorities differ.

## Follow-up
- Goyal should not enter the analogy box; leave the existing citations where they
  already stand correctly: `main.tex` around line ~119 (manipulation/manipulation
  resistance) and ~239 (hyperactive minority critique). These citations are
  load-bearing; do not remove them.
- In a future Discussion section: position QSMF as an alternative/complement/
  contrasting approach to CCA. "QSMF asks who is more reliable; we ask which
  constituency is approving — the two represent different governance principles."
- The Goyal bib entry (`goyal2026qsmf`, arXiv 2604.11224) is correct and in place;
  do not touch it.
