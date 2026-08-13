# data/scale-ladder/

The evidence behind Table 1 of the paper and behind its footnote about what
bootstrap stability does and does not certify.

## What this is

Before settling on 200,000 raters, we clustered the same data at many different
scales and with three different eigensolvers, then compared what each run
produced. Forty-five runs were launched; forty-two produced output and are kept
here, one directory per run.

The directory name encodes the run: `full_spectral_fast_<solver>_<scale>`, where
the solver is `amg`, `lobpcg`, `arpack_xl`, or absent for the earliest ARPACK
runs. A `_reassigned` suffix means the run was followed by outlier
reassignment.

Each directory holds the five small diagnostic tables the clustering stage
writes:

| File | What it holds |
|---|---|
| `stability_over_k.parquet` | Mean bootstrap ARI for `k = 2..7`. The maximum picks `k`. |
| `silhouette_over_k.parquet` | Silhouette score for the same range, reported alongside because the two criteria disagree. |
| `cluster_summary.parquet` | Size, vote counts, and approval rates of each resulting cluster. |
| `graph_diagnostics.parquet` | Shape of the k-NN affinity graph the run was built on. |
| `runtime_diagnostics.parquet` | Wall-clock seconds per stage. |

## What backs which claim

**Table 1** reads its six rows from six of these directories:

| Paper row | Directory |
|---|---|
| 60k | `full_spectral_fast_60k` |
| 150k | `full_spectral_fast_amg_150k` |
| 200k (production) | `full_spectral_fast_amg_200k` |
| 210k | `full_spectral_fast_amg_210k` |
| 240k | `full_spectral_fast_amg_240k` |
| 250k | `full_spectral_fast_amg_250k` |

**The footnote** — that eight of the nineteen AMG variants selected a degenerate
`k = 2` isolating 55 to 70 power-voters at ARI between 0.976 and 1.000 — reads
across all nineteen `full_spectral_fast_amg_*` directories. The eight are 90k,
100k, 160k, 170k, 180k, 220k, 230k, and 250k.

Both are asserted by `ScaleLadderTests` in
[`tests/test_paper_numbers.py`](../../tests/test_paper_numbers.py), so a change
in any of these files breaks a named claim rather than only a number.

## What is missing and why

Three of the forty-five directories are empty on the cluster and therefore absent
here:

- `full_spectral_fast_70k` and `full_spectral_fast_80k` — early runs that failed
  before writing output. They were left in place on the cluster as a record that
  the attempt happened.
- `full_spectral_fast_amg_200k_reassigned` — the production run. Its output was
  promoted into [`data/interim/`](../interim/), which is where the pipeline reads
  it from, so nothing is lost.

## The heavy files

Each run directory on the cluster also holds `ratings_filtered.parquet` and
`ratings_clustered.parquet` (1.2 to 3.3 GB apiece, 373 GB across the ladder),
`embedding.parquet`, `user_clusters*.parquet`, and `user_stats.parquet`. None of
those are in Git.

The per-rater cluster assignments are mirrored on Hugging Face; the rating tables
are not, because they can be rebuilt from `master_full.parquet` and the
assignments. See the ladder-mirror section of the root
[README](../../README.md#the-scale-ladder-mirror).
