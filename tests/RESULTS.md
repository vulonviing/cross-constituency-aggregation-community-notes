# Test Results

Last recorded run of the full suite. Reproduce it from the repository root with:

```bash
python run_tests.py          # all 60 tests
python run_tests.py -v       # per-test names
```

Only the standard library is needed to run the tests; `pytest` is not a
dependency. The data-backed tests read parquet files that ship with this
repository, so no Hugging Face download is required.

## Run summary

| | |
|---|---|
| Date | 2026-08-13 14:45 +0200 |
| Command | `python run_tests.py` |
| Result | **60 tests, 60 passed, 0 failed, 0 skipped** (1.07 s) |
| Python | 3.11.9 |
| pandas / numpy / pyarrow | 3.0.0 / 2.3.0 / 23.0.1 |
| Platform | macOS 26.5.2, arm64 |

```text
............................................................
----------------------------------------------------------------------
Ran 60 tests in 1.067s

OK
```

## What the three suites cover

### `tests/test_scoring_units.py` — 15 tests, synthetic data only

Pins the properties the paper claims for the aggregation rule, independent of
any dataset:

- **P2, non-compensation** — a camp scoring 0 collapses the bridge score even
  when the other camp is unanimous in favor; the score is the geometric, not the
  arithmetic, mean; it always sits between the weaker camp and the arithmetic
  mean.
- **P3, symmetry** — swapping the two camps leaves the score bit-identical.
- **P1, presence** — a camp with fewer than three raters on a note blocks the
  bridge score entirely; a camp with no raters receives the 0.5 neutral fallback
  in its approval column but still fails the coverage gate, so abstention never
  reads as support.
- **Selection** — a note is counted as rescued only when its bridge score clears
  0.5 *and* the platform had not already shown it.

### `tests/test_paper_numbers.py` — 14 tests, committed pipeline data

Re-derives each headline number from the artifact that produced it. A test skips
with an explicit message if its input file is missing.

| Assertion | Value | Source file |
|---|---|---|
| Bootstrap stability selects `k` | 3 (mean ARI 0.971) | `data/interim/stability_over_k.parquet` |
| `k=2` is markedly less stable | 0.593 | same |
| Cluster sizes | 107,680 / 92,256 / 64 | `data/interim/cluster_summary.parquet` |
| Median votes per cluster | 121 / 101 / 1,269 | same |
| Raters covered by both reassignment rules | 200,000 | `user_clusters_method_{a,b}_*.parquet` |
| Method A vs Method B disagreement | 29 raters | same |
| Both rules leave exactly two camps | `{0, 1}` | same |
| Scored slice | 100,000 notes | `data/processed/scores.parquet` |
| Diagnostic subset (≥10 raters per camp) | 98,442 notes | same |
| Between-camp Pearson correlation | −0.620 | same |
| Discriminating share (gap > 0.3) | 81.4% | same |
| Expanded Stage 2 pool | 10,376 notes | `…stage2-expanded-v1/stage2_results.parquet` |
| Admission routes | 10,096 strict + 280 recall | same |
| **Final rescue set** | **8,558 notes** | same |

The one headline chain not covered here is 1.7M English notes → 510,212 eligible
notes; it needs `data/master_full.parquet`, which is too large for Git. See
[REPRODUCING.md](../REPRODUCING.md), tier B.

### `notebooks/llm_validation/test_validation.py` — 31 tests

The existing Gemma validation suite, unchanged. Every model call is mocked, so
no GPU, no vLLM server, and no network access are needed. It covers prompt
freezing, deterministic per-attempt seeds, the strict post-hoc response schema,
the three-attempt retry limit and the `unresolved` outcome, manifest hashing,
shard preparation and merging for Stages 1, 1.5, and 2, and the SQLite call
store.
