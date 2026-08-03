# Canonical Pipeline Submission

Run all commands from the repository root on SCCKN.

## Validate

```bash
for stage in ingest clustering scoring topics plots paper_visuals; do
  jobs/submit_stage.sh --dry-run "$stage"
done
```

## Submit

```bash
jobs/submit_stage.sh ingest
jobs/submit_stage.sh clustering
jobs/submit_stage.sh scoring
jobs/submit_stage.sh topics
jobs/submit_stage.sh plots
jobs/submit_stage.sh paper_visuals
```

Wait for each data-producing stage to finish before submitting its dependent
stage. The helper reads `TEST_MODE` and `FULL_RESOURCE_PROFILE` from
`config.txt`, then submits the matching script with the approved SGE resources.

The historical Gabriel notebook is deprecated and is not an active stage.
Canonical validation uses the separate Gemma GPU workflow below.

## Canonical Gemma 4 Validation

The isolated Gabriel-free validation has its own GPU submission helper:

```bash
jobs/submit_llm_validation.sh setup
jobs/submit_llm_validation.sh smoke
```

Review the smoke `benchmark.json` before submitting a bounded production batch:

```bash
jobs/submit_llm_validation.sh stage1 <max_notes> <concurrency>
```

The job requests two L40 GPUs and 64 GB `h_vmem` per SMP process, stores the
model and environment under `/work`, and commits each completed note before
moving to the next queue item.

After the first canonical 2,000-note batch, submit the six disjoint remaining
Stage 1 shards with at most three concurrent tasks:

```bash
jobs/submit_llm_validation.sh --dry-run stage1-array 2-7 3 64
jobs/submit_llm_validation.sh stage1-array 2-7 3 64
python3 notebooks/llm_validation/run_validation.py shard-status
```

Each task writes its own SQLite database and artifacts below the production
run's `shards/` directory. The array is pinned to `gpu@scc213`, and the wrapper
verifies both allocated devices are L40S before loading the model. Re-running a
task resumes only its pending notes.

The reviewed production run is complete. Its expanded Stage 2 used six shards:

```bash
jobs/submit_llm_validation.sh stage2-expanded-array 1-6 3 64
python3 notebooks/llm_validation/run_validation.py stage2-expanded-shard-status
python3 notebooks/llm_validation/run_validation.py merge-stage2-expanded-shards
```

The merged canonical result is
`data/llm_validation/runs/gemma-4-31b-it-scckn-stage2-expanded-v1/stage2_results.parquet`.
Filter `passes_rescue_threshold == True` for the 8,558-note final rescue set.
See `notebooks/llm_validation/README.md` before any reproduction run.

## Monitor

```bash
qstat -u emrecan.ulu
qstat -j <job-id>
qacct -j <job-id>
qdel <job-id>
```

Production logs are under `.artifacts/logs/`. Smoke logs are under
`.artifacts/smoke/logs/`.

## Environment

The job scripts currently activate SCCKN's Python 3.13 environment:

```bash
module load conda
source activate python-3.13
```

Before the first run, verify imports and install missing requirements in an
appropriate user environment:

```bash
python -c "import pyamg, pandas, pyarrow, sklearn"
```
