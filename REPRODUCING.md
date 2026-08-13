# Reproducing the Paper

This document maps every headline number, table, and figure in
[`paper/03-07-2026-1550-edition/main.pdf`](paper/03-07-2026-1550-edition/main.pdf)
to the artifact that produced it.

**The fastest check is two commands.** From the repository root:

```bash
python -m pip install -r requirements.txt
python run_tests.py
```

That re-derives the paper's headline numbers from the parquet files committed
here and reports 64 passing tests. No data has to be downloaded first. See
[tests/RESULTS.md](tests/RESULTS.md) for the last recorded run.

To confirm the Gemma validation files are themselves unchanged:

```bash
bash scripts/verify_llm_checksums.sh
```

## Three tiers of reproducibility

| Tier | What it needs | What it covers |
|---|---|---|
| **A** | This repository only | Every result from clustering onward: cluster structure, scoring, selection, topics, Gemma validation. All of Tables 1 and 4–6 and Figures 1, 3, 4, and 5. |
| **B** | Tier A plus three large files from Hugging Face (~12.6 GB) | Re-running clustering and scoring from ratings; the 1.7M → 510k → 100k sample-construction chain and Figure 2, which both need the rating-level tables. |
| **C** | Tier B plus a raw X snapshot | Ingestion from scratch. **Not bit-reproducible** — see the warning below. |

### The Tier C warning

X's published Community Notes snapshot is live: notes, ratings, and status
updates are added continuously. The snapshot behind every artifact in this
repository was retrieved on **2026-05-08**. Re-downloading today and re-running
`00_ingest.ipynb` will produce a different `master_full.parquet`, and the
downstream numbers will move. Anyone who needs *these* results should use the
committed artifacts (Tier A) or fetch the interim files (Tier B) rather than
starting from raw inputs. The README's
[Raw Data Provenance](README.md#raw-data-provenance) section documents the
snapshot and the Hugging Face mirror.

---

## Tier A — verifiable from this repository alone

Every row below is asserted by a test in
[`tests/test_paper_numbers.py`](tests/test_paper_numbers.py). The snippets are
runnable as-is from the repository root.

### Cluster structure (Section 3, Table 1)

| Claim in the paper | Value | File |
|---|---|---|
| Bootstrap stability selects `k` | **3** (mean ARI 0.971) | `data/interim/stability_over_k.parquet` |
| `k = 2` is far less stable | 0.593 | same |
| Silhouette prefers `k = 2` | 0.997 | `data/interim/silhouette_over_k.parquet` |
| Cluster sizes | 107,680 / 92,256 / **64** | `data/interim/cluster_summary.parquet` |
| Median votes per cluster | 121 / 101 / **1,269** | same |

```python
import pandas as pd
s = pd.read_parquet("data/interim/stability_over_k.parquet")
print(s[["k", "mean_ari"]])                       # k=3 is the maximum
print(pd.read_parquet("data/interim/cluster_summary.parquet"))
```

### Reassignment robustness (Section 6.2)

| Claim | Value | File |
|---|---|---|
| Raters covered by both rules | 200,000 | `data/interim/user_clusters_method_a_embedding.parquet`, `..._method_b_voteprofile.parquet` |
| Method A vs Method B disagreement | **29 raters** | same |
| Between-camp Pearson correlation | **−0.620** | `data/processed/scores.parquet` |
| Discriminating share (gap > 0.3) | **81.4%** | same |
| Notes in the diagnostic subset | 98,442 | same |

Both diagnostics are measured on notes with at least ten raters in each camp.

```python
import numpy as np, pandas as pd
sc = pd.read_parquet("data/processed/scores.parquet")
f = sc[(sc.cluster_0_count >= 10) & (sc.cluster_1_count >= 10)]
print(len(f))                                                        # 98442
print(np.corrcoef(f.cluster_0_approval, f.cluster_1_approval)[0, 1])  # -0.6204
gap = (f.cluster_0_approval - f.cluster_1_approval).abs()
print((gap > 0.3).mean() * 100)                                       # 81.43
```

### Selection and the rescue pool (Section 6, Table 4)

| Row of Table 4 | Value | File |
|---|---|---|
| Representative-picked note universe | 44,722 | `data/processed/selection_log.parquet` |
| CN shown within representative picks | 6,832 | same |
| CCA-qualified | 20,405 | same |
| — shown by CN | 6,750 | same |
| — hidden (**the rescue pool**) | **13,655** | same |
| Below CCA threshold | 24,317 | same |

```python
import pandas as pd
log = pd.read_parquet("data/processed/selection_log.parquet")
rep = log[(log.strategy == "Representative") & (log.selection_scope == "single_pick")]
q = rep[rep.passes_bridge_threshold.fillna(False).astype(bool)]
print(len(rep), (rep.status == "CURRENTLY_RATED_HELPFUL").sum(), len(q))
print((q.status == "CURRENTLY_RATED_HELPFUL").sum(), (q.status != "CURRENTLY_RATED_HELPFUL").sum())
```

### Gemma validation (Section 6, Figure 4)

| Claim | Value | File |
|---|---|---|
| Stage 1 strict passes | 10,096 | `…/gemma-4-31b-it-scckn-v1/stage1_results.parquet` |
| Stage 1.5 recall admissions | 280 | `…/gemma-4-31b-it-scckn-stage1-5-opinion-v1/stage1_5_results.parquet` |
| Expanded Stage 2 pool | 10,376 | `…/gemma-4-31b-it-scckn-stage2-expanded-v1/stage2_results.parquet` |
| **Final rescue set** | **8,558** | same |
| Below the score-50 threshold | 1,818 | same |
| Stopped at the content screen | 3,279 | 13,655 − 10,376 |

All three run directories live under `data/llm_validation/runs/`.

```python
import pandas as pd
r = pd.read_parquet(
    "data/llm_validation/runs/gemma-4-31b-it-scckn-stage2-expanded-v1/stage2_results.parquet"
)
print(len(r), int(r.passes_rescue_threshold.sum()))   # 10376 8558
print(r.admission_route.value_counts())               # 10096 strict + 280 recall
```

Each run directory also carries `run_manifest.json` (model, seeds, prompt hash),
`checksums.sha256`, the frozen prompt text, `raw_calls.jsonl.gz` with every
model response, and `calls.sqlite3` with the per-attempt call store, so the
validation is auditable call by call without re-running the model.

### Figures

The paper's five figures each regenerate from a same-named script in
`figures/script_figures/`:

```bash
python figures/script_figures/fig1-rater-dominance.py        # Figure 1
python figures/script_figures/fig2-dataset-construction.py   # Figure 2
python figures/script_figures/fig3-rescue-panels.py          # Figure 3
python figures/script_figures/cn-gemma-validation-funnel.py  # Figure 4
python figures/script_figures/cn-topic-signatures.py         # Figure 5
```

Each writes its own `.pdf` and `.png` beside itself at 300 dpi. Four of the five
run on a fresh clone. Figure 2 is the exception: it reports the total
rating-edge count, which only `data/interim/ratings_clustered.parquet` carries,
so it belongs to tier B below. Running it without that file stops with a message
naming the fetch script.

### Rebuilding the manuscript

```bash
cd paper/03-07-2026-1550-edition
latexmk -pdf main.tex          # 18 pages, no undefined references
```

---

## Tier B — re-running the pipeline from ratings

Three files exceed GitHub's size limits and are mirrored on the
`vulonviing/community-notes-rescue-interim` Hugging Face dataset. Fetch them
with:

```bash
scripts/fetch_interim_from_hf.sh
```

| File | Size | Unlocks |
|---|---|---|
| `data/interim/ratings_filtered.parquet` | ~3 GB | re-running `01_clustering` |
| `data/interim/ratings_clustered.parquet` | ~3 GB | re-running `02_scoring`, `03_topics`; regenerating Figure 2 |
| `data/master_full.parquet` | ~6.6 GB | the sample-construction chain behind Figure 2 |

With those in place, the stages run in order:

```bash
jobs/submit_stage.sh clustering
jobs/submit_stage.sh scoring
jobs/submit_stage.sh topics
jobs/submit_stage.sh plots
jobs/submit_stage.sh paper_visuals
```

Set `TEST_MODE=1` in `config.txt` first for a small smoke run that writes only
under `.artifacts/smoke/` and leaves the committed artifacts untouched.

### The sample-construction chain (Figure 2)

These are the numbers a reader most often wants to check and the only headline
chain not covered by the test suite, because it needs `master_full.parquet`:

| Step | Count | Where it is computed |
|---|---|---|
| English notes in the snapshot | 1,693,711 | `notebooks/00_ingest.ipynb` |
| Tweets with ≥3 English candidate notes | 132,010 | `notebooks/00_ingest.ipynb`, cell 3 |
| Notes on those tweets | 533,510 | same |
| Notes with ≥3 eligible ratings within 48 h | **510,212** | `src/io.py`, `min_note_ratings` filter |
| Dense analysis slice | 100,000 notes | `src/clustering.py:select_analysis_slice` |
| Active raters retained | 200,000 | same |

The two "at least three" thresholds apply at different levels: the first counts
candidate notes **per tweet**, the second counts eligible ratings **per note**.

---

## Tier C — ingestion from scratch

Place the official snapshot files (`notes-*.tsv`, `ratings-*.tsv`,
`noteStatusHistory-00000.tsv`) and the FastText language model under `raw/`, then
run `jobs/submit_stage.sh ingest`. See `raw/PUT_SOURCE_FILES_HERE.md`.

Read the Tier C warning above before relying on the output: a snapshot taken
today will not reproduce these results.

---

## Where things live

| Looking for | Path |
|---|---|
| The paper | `paper/03-07-2026-1550-edition/main.pdf` |
| Method implementation | `src/` |
| Stage-by-stage pipeline | `notebooks/` |
| Gemma validation code | `notebooks/llm_validation/` |
| Committed results | `data/processed/`, `data/interim/`, `data/llm_validation/` |
| Figure scripts and outputs | `figures/script_figures/` |
| Tests and their last run | `tests/`, `tests/RESULTS.md` |
| Cluster job submission | `jobs/` |
| Presentations | `docs/presentations/` |
| What each data file holds | `data/README.md` |
