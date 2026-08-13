# Test Results

Last recorded run of the full suite. Reproduce it from the repository root with:

```bash
python -m pip install -r requirements.txt
python run_tests.py          # all 64 tests
python run_tests.py -v       # per-test names
```

The tests need only `pandas`, `numpy`, and `pyarrow` from that requirements
file. `pytest` is not a dependency, and the data-backed tests read parquet files
that ship with this repository, so no Hugging Face download is required.

## Run summary

| | |
|---|---|
| Date | 2026-08-13 15:11 +0200 |
| Command | `python run_tests.py` |
| Result | **64 tests, 64 passed, 0 failed, 0 skipped** (1.11 s) |
| Python | 3.11.9 |
| pandas / numpy / pyarrow | 3.0.0 / 2.3.0 / 23.0.1 |
| Platform | macOS 26.5.2, arm64 |

```text
................................................................
----------------------------------------------------------------------
Ran 64 tests in 1.106s

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

### `tests/test_paper_numbers.py` — 18 tests, committed pipeline data

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
| Representative-picked note universe | 44,722 | `data/processed/selection_log.parquet` |
| CN shown within those picks | 6,832 | same |
| CCA-qualified | 20,405 | same |
| — of which shown by CN | 6,750 | same |
| — of which hidden (rescue pool) | 13,655 | same |
| Below the bridge threshold | 24,317 | same |
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

## Related check

The test suite verifies the numbers; a separate script verifies that the
validation run files themselves are unchanged:

```bash
bash scripts/verify_llm_checksums.sh
```

It checks the SHA-256 manifest of all three Gemma run directories, 176 files in
total.
