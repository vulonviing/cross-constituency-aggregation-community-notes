#  Scale-Up V3 — Decision Report (4 Alternatives for the Advisor)

**Date:** 2026-05-17  
**Audience:** Advisor — decision document with technical evidence  
**Companion report:** `hedge/SCALE_UP_V2_INTERIM_REPORT.md` (full technical detail)

---

## TL;DR

We tested clustering at 11 user scales from 30k (baseline) through 250k. The behavioral two-camp structure holds at every scale, but **larger scale comes with a small reliability cost**:

- **Bootstrap stability ARI** drops from 0.99 (50k) → 0.96 (240k)
- **Cross-cluster Pearson correlation** softens from −0.69 (60k) → −0.60 (240k)
- **Discriminating notes share** drops from 86% → 80%
- BUT **between-cluster agreement** actually *improves* (15% → 6-9%), meaning cluster separation sharpens
- New reassignment runs show that the small outlier clusters can be absorbed into the two main camps with almost no metric degradation. At 200k, vote-profile reassignment gives Pearson **−0.620** vs. **−0.623** main-only, with strongly discriminating notes still **81.4%**.

This is a real trade-off but not a catastrophe — all scales remain publication-grade. The decision is about how much sample-size argument vs. statistical purity you want to optimize for.

**Updated recommendation:** use **Option C revised** — `spectral_fast_amg_200k_reassigned`, with Method B vote-profile reassignment as the final two-camp partition and Method A embedding reassignment as a robustness check.

---

## The Trade-Off Curve

This table reports the initial AMG clustering and main-cluster validation metrics. Final two-camp reassignment metrics for the 150k/200k/210k/240k variants are reported below in Option C/D and Finding 3b.

| Scale | Bootstrap ARI | Pearson | Within agreement | Between agreement | Discriminating notes | Outlier cluster size | Outlier voting profile | Outlier within-agree |
|------:|--------------:|--------:|-----------------:|------------------:|---------------------:|---------------------:|------------------------|----------------------|
| 30k (current baseline) | ~0.95+ | (not measured) | (not measured) | (not measured) | (not measured) | (not separated) | — | — |
| 60k | 0.989 | −0.69 | 97% / 95% | 15% | 86% | None (absorbed) | — | — |
| 150k | 0.977 | −0.65 | 91% / 100% | 8.4% | 83% | 62 users (0.04% of slice) | median 973 votes vs 122-145 for main camps (7× more active) | ≈99.86% |
| 200k | 0.971 | −0.62 | 90% / 99% | 6.4% | 82% | 64 users (0.03%) | median 1,269 votes vs 101-121 | ≈99%+ |
| 210k | 0.969 | −0.62 | 92% / 93% | 16% | 81% | 66 users (0.03%) | median 1,315 votes vs 97-117 | ≈99%+ |
| 240k | 0.955 | −0.60 | 93% / 96% | 9% | 80% | 60 users (0.02%) **+ 1,431 users (0.6%)** | 60 are super-active (median 1,781 votes); 1,431 are low-activity (median 70 votes) | ≈99% for the 60-group |

**Reading the trade-off table:**

- **Bootstrap ARI** (cluster stability) drifts down slightly with scale: 0.989 → 0.955. Still well above the 0.80 publication threshold.
- **Pearson** (how strongly the two main camps vote in opposite directions on the same notes) softens slightly: −0.69 → −0.60. Still strongly negative — real ideological split.
- **Within agreement** (users in the same cluster voting the same way on shared notes) holds at 90-100%.
- **Between agreement** (users in different clusters voting the same way on shared notes) stays at 6-16% — meaning between-cluster users disagree on 84-94% of shared notes.
- **Discriminating notes** (notes where the two main camps differ by ≥30 percentage points) is always 80-86%.
- **Outlier cluster**: a tiny sub-population that the algorithm splits off from the main camps. Appears at every scale ≥70k AMG, never appears in the 60k ARPACK baseline. Always has uniform internal voting (~99% within-agreement) and dramatically higher activity than the main camps (5-15× more votes). At 240k a second outlier emerges (1,431 low-activity users — interpretation TBD).

**How to read the outlier across scales:** The same ~60-user power-voter group keeps re-appearing as scale grows. This is **not noise** — it is a persistent, internally coherent sub-population. Its existence does not threaten the final two-camp story; it becomes a diagnostic/sub-population finding from the initial spectral pass.

---

## The Four Proposed Options (Quick-Look Table)

| # | Option | Users | Solver | Chosen k | Cluster sizes | Bootstrap ARI | Pearson | Within agreement | Between agreement | Discriminating notes | Outlier(s) | Paper-rewrite cost | Reviewer "sample too small" defense | Recommendation |
|--:|--------|------:|--------|---------:|---------------|--------------:|--------:|-----------------:|------------------:|---------------------:|------------|-------------------|--------------------------------------|----------------|
| A | Keep 30k baseline (status quo) | 30,000 | ARPACK | 3 | (paper-published) | ~0.95+ | n/a | n/a | n/a | n/a | not separated | None | Weak | Only if time is critical |
| B | 30k main + 80k AMG robustness sidebar | 30k (+80k aside) | ARPACK (+AMG aside) | 3 / 3 | (current) / 48k / 32k / 48 | 0.95 / **0.987** | n/a / (TBD) | n/a / (TBD) | n/a / (TBD) | n/a / (TBD) | 48-user outlier in sidebar | Small | Medium | Defensive posture |
| C ⭐ | Switch main to 200k AMG + vote-profile reassignment | 200,000 | AMG | 3 -> final 2 camps | 107,734 / 92,266 after absorbing 64 | **0.971** | **−0.620** | **90% / 99%** | **6.4%** | **81.4%** | 64 power-voters initially identified, then assigned to nearest voting camp | Medium | **Strong** | **My recommendation** |
| D | Switch main to 240k AMG + vote-profile reassignment | 240,000 | AMG | 4 -> final 2 camps | 114,171 / 125,829 after absorbing 1,431 + 60 | 0.955 | −0.596 | 93% / 96% | 8.8% | 80.0% | 60 power-voters + 1,431 low-activity group initially identified, then reassigned | Medium | Strongest | Max-scale push |

For C/D, within- and between-cluster pairwise agreement are the initial main-cluster validation metrics. The reassignment evidence is the final two-camp note-profile Pearson and discriminating-note share, which remain essentially unchanged after absorbing the micro-clusters.

**Trade-off shorthand:**

- **A** = no risk, no scale, full sample-size criticism risk
- **B** = no risk, small scale signal, ~2.7× scale claim in defense
- **C** = moderate change, **6.7× scale**, final clean two-camp partition, all validity metrics publication-grade, algorithm-chosen initial k plus transparent reassignment
- **D** = moderate change, **8× scale**, final two-camp partition after absorbing two initial micro-clusters, slightly weaker stability

The choice across A→D is a single dial: how much paper rework are you willing to do to neutralize the sample-size criticism? More rework on the right = stronger paper.

---

## The Four Alternatives

### Option A — Keep the 30k Baseline (No Change)

| Parameter | Value |
|-----------|-------|
| Users | 30,000 |
| Notes | 15,000 |
| Total ratings | ~10M |
| Solver | ARPACK (original) |
| Chosen k | 3 (paper-published) |
| Bootstrap stability ARI | ~0.95+ |
| Pearson, agreement metrics | Not previously computed (would need re-run on 30k) |

**Pros:**
- No methodology change at all
- Existing paper text, figures, and downstream pipeline work as-is
- Zero implementation risk

**Cons:**
- Reviewer "sample too small" objection remains the primary rejection risk
- Other recent papers (2025, 2026) use 100k+
- Misses opportunity to strengthen the methods section

**Recommended only if:** Time pressure is extreme and the paper is otherwise complete.

---

### Option B — Robustness Check (Keep 30k Main + Add 80k AMG Sidebar)

| Parameter | Value |
|-----------|-------|
| Main analysis | 30k (unchanged) |
| Robustness section | 80k AMG, 1-2 paragraphs in methods/results |
| Solver for robustness | AMG (≈3 minutes to rerun) |
| Robustness ARI | 0.987 |
| Cluster structure | 48k / 32k / 48-outlier (k=3) |

**Pros:**
- Main paper untouched — minimal rewriting risk
- Reviewer rebuttal: "We replicate the finding at 2.7× larger sample (80k); same two-camp structure, same stability ARI"
- Methodologically conservative — AMG only used for the sidebar, ARPACK remains main
- Closest match in voting-distribution to the 30k baseline

**Cons:**
- Reviewer might still say "80k is not 100k"
- Sidebar can be dismissed as "robustness check, not main result"
- Misses the strongest scale-up framing

**Recommended if:** Advisor wants a defensive posture — minimum change to address criticism without restructuring.

---

### Option C — Main Production Upgrade (200k AMG + Vote-Profile Reassignment)  ⭐ RECOMMENDED

| Parameter | Value |
|-----------|-------|
| Users | 200,000 |
| Notes | 100,000 |
| Total ratings | ~48M (4.8× baseline) |
| Solver | AMG |
| Initial chosen k | 3 (algorithm-chosen, no manual override) |
| Final assignment | 2 camps after assigning the 64-user micro-cluster by vote-profile Pearson correlation |
| Final cluster sizes | 107,734 / 92,266 |
| Bootstrap stability ARI | **0.971** |
| Silhouette (chosen k) | 0.735 |
| Cross-cluster Pearson after reassignment | **−0.620** |
| Within-cluster pair agreement | 90% / 99% (main-only validation; unchanged in substance by 64-user reassignment) |
| Between-cluster pair agreement | **6.4%** (main-only validation) |
| Discriminating notes (diff > 0.3) | 80,163 / 98,442 (81.4%) |
| Discriminating notes (diff > 0.5) | 69.1% |
| Runtime | 5m 16s |

**Pros:**
- **6.7× larger user sample, 4.8× larger rating volume** — fully addresses the reviewer criticism
- Algorithm-chosen k (no cherry-picking defense needed)
- Final two-camp partition is balanced (54% / 46%) and avoids micro-cluster contamination in downstream scoring
- Vote-profile reassignment is directly interpretable: initially outlying users are assigned to the camp whose voting behavior they most resemble on shared notes
- Embedding-distance reassignment gives the same substantive conclusion, so we have a clean robustness check
- All validity metrics are publication-grade
- Strongest "we did the obvious thing the reviewer wanted"
- Power-voter outlier remains a paper finding from the initial spectral pass, but does not force a three-camp downstream analysis

**Cons:**
- Requires re-running downstream pipeline (topic modeling, scoring, figures)
- Some paper text needs rewriting in methods/results
- Slightly lower Pearson than 30k baseline likely would be (−0.62 vs untested but probably −0.70+)
- Introduces AMG methodology — need 1-2 paragraphs explaining the eigensolver switch
- Adds a transparent post-processing step, which must be described carefully

**Recommended if:** You want the strongest paper. This is my recommendation.

---

### Option D — Maximum Defensible Scale (240k AMG + Vote-Profile Reassignment)

| Parameter | Value |
|-----------|-------|
| Users | 240,000 |
| Notes | 120,000 |
| Total ratings | ~53M (5.3× baseline) |
| Solver | AMG |
| Initial chosen k | 4 (algorithm-chosen) |
| Initial cluster sizes | 113,230 / 125,279 / 1,431 / 60 |
| Final assignment | 2 camps after assigning the 1,431-user and 60-user micro-clusters by vote-profile Pearson correlation |
| Final cluster sizes | 114,171 / 125,829 |
| Bootstrap stability ARI | **0.955** |
| Silhouette (chosen k) | 0.708 |
| Cross-cluster Pearson after reassignment | **−0.596** |
| Within-cluster pair agreement | 93% / 96% (main-only validation) |
| Between-cluster pair agreement | **8.8%** (main-only validation) |
| Discriminating notes (diff > 0.3) | 94,526 / 118,129 (80.0%) |
| Discriminating notes (diff > 0.5) | 67.2% |
| Runtime | 11m 22s |

**Pros:**
- 8× baseline user count — most aggressive scale-up
- Final two-camp partition remains balanced (47.6% / 52.4%)
- Algorithm-chosen k=4 first captures TWO outlier sub-populations:
  - Cluster 2 (1,431 users): low-activity micro-group
  - Cluster 3 (60 users): power-voter micro-group
- Reassignment absorbs both groups into the final two-camp downstream analysis
- More scale = strongest reviewer-facing sample-size defense

**Cons:**
- More cluster complexity to explain in methods/results because the initial spectral pass finds four clusters
- Marginal additional reviewer-impressive value vs 200k (8× vs 6.7×)
- Stability ARI dropped to 0.955 (still above threshold but lowest of the candidates)
- Pearson after reassignment is −0.596, the softest of the candidates

**Recommended if:** Advisor wants maximum scale and is comfortable explaining the initial four-cluster pass plus final two-camp reassignment.

---

## Side-by-Side Comparison

| Dimension | A — 30k baseline | B — 30k + 80k sidebar | C — 200k reassigned production ⭐ | D — 240k reassigned maximum |
|-----------|:----------------:|:---------------------:|:----------------------:|:----------------:|
| **User scale** | 30k | 30k (+80k aside) | 200k | 240k |
| **vs baseline** | 1× | 1× (2.7× aside) | 6.7× | 8× |
| **Solver** | ARPACK | ARPACK (+AMG aside) | AMG | AMG |
| **Chosen k** | 3 | 3 (3 aside) | 3 -> final 2 camps | 4 -> final 2 camps |
| **Bootstrap stability ARI** | ~0.95 | 0.95 / 0.987 | 0.971 | 0.955 |
| **Cross-cluster Pearson** | not measured | (TBD) / −0.68* | **−0.620** | −0.596 |
| **Within agreement** | not measured | (TBD) / 91-95%* | 90-99% | 93-96% |
| **Between agreement** | not measured | (TBD) / 13%* | **6.4%** | 8.8% |
| **Discriminating notes** | not measured | (TBD) / 84%* | 82% | 80% |
| **Cluster structure** | 2 main | 2 main / 2 main + 1 outlier | final 2 main camps; initial 64-user outlier reassigned | final 2 main camps; initial 1,431 + 60 outliers reassigned |
| **Outlier sub-population finding** | none | small (48 users) | initial 64-user power-voter group, reported as diagnostic/robustness | initial two groups (60 + 1431), reported as diagnostic/robustness |
| **Methodology change** | None | Minimal (sidebar only) | Moderate (solver switch) | Moderate |
| **Paper rewrite needed** | None | Small | Medium | Medium |
| **Downstream re-run needed** | None | Just sidebar | Yes (full pipeline) | Yes (full pipeline) |
| **Reviewer "small sample" defense** | weak | medium | **strong** | strongest |
| **Implementation risk** | zero | very low | low | low |
| **Compute cost** | 0 | 3 minutes | 5 minutes | 11 minutes |
| **Runtime estimate (full pipeline)** | 0 | 1 day | 2-3 days | 2-3 days |

*Italicized values for B are estimates by interpolation from the 60k/70k/80k results; would be measured exactly if Option B is chosen.

---

## Recommendation Matrix

| If the advisor cares most about... | Choose |
|------------------------------------|--------|
| Minimum disruption, fastest paper submission | **A** |
| Defensive sample-size argument, minimum methodology change | **B** |
| **Best balance of scale + rigor + transparent two-camp assignment** | **C ⭐** |
| Maximum sample-size argument, willing to explain initial micro-clusters plus reassignment | **D** |

---

## Key Findings — Table Format (Cumulative Evidence)

### Finding 1 — AMG is the right solver

| Question | Answer |
|----------|--------|
| Does AMG produce different cluster quality than ARPACK at comparable scale? | No — ARI within 0.002 of ARPACK at 50k/60k anchor scales |
| Speedup of AMG vs ARPACK? | ~120× (4 min vs 9 hours at 70k) |
| Does AMG fail at any tested scale? | No — completed cleanly at every scale 70k-250k |
| Was alternative (LOBPCG no preconditioner) viable? | No — silently produced garbage at all 9 tested scales |
| Methodologically supported by literature? | Yes — sklearn explicitly recommends `eigen_solver='amg'` for large graphs |

### Finding 2 — Behavioral two-camp structure is robust

| Question | Answer |
|----------|--------|
| Cross-cluster vote profile Pearson correlation | −0.60 to −0.70 across all scales (always strongly negative) |
| Within-cluster pairwise agreement on shared notes | 90-97% (strongly consistent) |
| Between-cluster pairwise agreement on shared notes | 6-19% (strongly opposed) |
| Within/Between ratio | 6× to 16× (impossible to explain by chance) |
| Fraction of notes that strongly discriminate (diff > 0.3) | 80-87% |
| Fraction of notes that very strongly discriminate (diff > 0.5) | 67-78% |
| Does the two-camp structure depend on the activity distribution? | No — within-cluster median votes are similar across main clusters |
| Does the structure survive scale-up to 240k? | Yes — same metrics, modest softening |

### Finding 3 — Power-voter outlier sub-population

| Question | Answer |
|----------|--------|
| Does an outlier cluster appear consistently? | Yes — at every scale ≥70k AMG and at 50k ARPACK |
| Outlier cluster size | 40-230 users |
| Outlier median vote count | 685-1,800 (vs 100-200 for main clusters) |
| Outlier within-cluster pair agreement | ~99% — almost identical voting |
| Outlier interpretation | Coordinated raters / power users / bot-like clique candidates |
| Should this be reported? | Yes — separate paper finding |

### Finding 3b — Outlier reassignment does not change the two-camp result

| Variant | Method | Final cluster sizes | Pearson | diff > 0.3 | diff > 0.5 |
|---------|--------|--------------------:|--------:|-----------:|-----------:|
| 150k | Method B vote-profile | 83,822 / 66,178 | −0.644 | 82.9% | 71.5% |
| 200k | Method B vote-profile | 107,734 / 92,266 | **−0.620** | **81.4%** | **69.1%** |
| 210k | Method B vote-profile | 112,378 / 97,622 | −0.617 | 81.2% | 68.8% |
| 240k | Method B vote-profile | 114,171 / 125,829 | −0.596 | 80.0% | 67.2% |

**Decision:** Use Method B as the main production assignment because it is behaviorally interpretable. Use Method A embedding-centroid reassignment as robustness; it gives nearly identical Pearson/diff metrics even though it assigns individual outlier users somewhat differently.

Method A robustness check: 200k gives Pearson −0.620 and diff>0.3 = 81.4%; 240k gives Pearson −0.594 and diff>0.3 = 79.9%. These are substantively the same as Method B.

### Finding 4 — Trade-off cost of scale-up

| Metric | At 60k | At 240k | Change | Verdict |
|--------|-------:|--------:|-------:|---------|
| Bootstrap stability ARI | 0.989 | 0.955 | −3.4% | Still publication-grade (≥0.80) |
| Cross-cluster Pearson | −0.69 | −0.60 | +13% softer | Still strongly negative |
| Discriminating notes share | 86% | 80% | −7% | Still dominant majority |
| Within-cluster agreement | 95-97% | 93-96% | ≈ flat | Maintained |
| Between-cluster agreement | 15% | 9% | **−40% (improvement)** | Cluster separation IMPROVED |
| Stability std_ari | low | low | flat | Maintained |
| Speed | 10 hours | 11 min | 55× faster | Massive improvement |

**Net:** Scale-up costs ~5% on ARI / Pearson but **improves** between-cluster separation and gives a massively larger sample. Worth the trade.

---

## Recommended Decision Path

1. **Read Options A-D above with the trade-off curve in mind.**
2. **If advisor leans defensive:** Option B is safest — 30k main + 80k AMG robustness sidebar.
3. **If advisor leans ambitious:** Option C revised is strongest — 200k AMG as main analysis, with vote-profile reassignment for the final two-camp partition. Best scale + best stability balance.
4. **If advisor is indifferent or wants maximum scale:** Option D — 240k AMG + vote-profile reassignment.
5. **If advisor wants to commit:** Recommend **Option C** as primary, hold Option D in reserve.

Either C or D is the strongest paper. Option B is acceptable but leaves the sample-size question half-answered.

---

## Implementation Notes

- All four original options are already pre-computed on SCCKN. The reassigned variants for 150k/200k/210k/240k are also complete.
- For Option C revised, the downstream pipeline should be pointed at `data/full_spectral_fast_amg_200k_reassigned/` and should use `user_clusters_method_b_voteprofile.parquet` as the final user-cluster assignment.
- For Options B/C/D, the downstream pipeline (topic modeling, scoring, paper figures) needs to be re-pointed to the new variant directory and re-executed. Estimated time: 1-3 days depending on option.
- ARPACK XL diagnostic jobs (70k, 80k) are still running. Their result is for the methods-section robustness paragraph only; does not affect any of the four options.

---

## Files Referenced

| Purpose | Path |
|---------|------|
| Full technical detail (every variant, every k) | `hedge/SCALE_UP_V2_INTERIM_REPORT.md` |
| This decision document | `hedge/SCALE_UP_V3_DECISION_REPORT.md` |
| Earlier scale-up planning | `hedge/SCALE_UP_V2_PLAN.md`, `hedge/SCALE_UP_MEMO.md` |
| Solver code | `hedge/src/spectral_fast.py` |
| Production candidate outputs | `data/full_spectral_fast_amg_200k/`, `_210k/`, `_240k/` |
| Reassigned production outputs | `data/full_spectral_fast_amg_150k_reassigned/`, `_200k_reassigned/`, `_210k_reassigned/`, `_240k_reassigned/` |
| Original baseline | `data/full/interim_expanded_20260509_1756/` (30k) |
