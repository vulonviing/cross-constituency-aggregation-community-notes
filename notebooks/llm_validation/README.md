# Canonical Gemma 4 Validation

This folder contains the canonical two-stage validation over the frozen 13,655
Representative rescue candidates. The completed production run uses
`google/gemma-4-31B-it` on SCCKN; it does not call OpenCode or Gabriel. The
merged expanded Stage 2 result retains 8,558 notes at the threshold of 50.

## Frozen Method

- Input: the tracked frozen manifest at
  `data/llm_validation/runs/gemma-4-31b-it-scckn-v1/input_manifest.parquet`.
  Historical Gabriel fields remain only as provenance and are never sent to
  the model.
- Model: `google/gemma-4-31B-it`, revision
  `518276fb130dc81caf9a4f772e65e63ef2526493`.
- Inference: vLLM 0.25.0, two L40 GPUs, BF16, thinking enabled,
  temperature 0.2, and a stable per-attempt seed.
- Context: one note per independent prompt; no tweet retrieval, URL fetching,
  Gabriel scaffold, upstream score, embedding, or vector store.
- Stage 1: one accepted judgment across the five fixed labels.
- Stage 2: one integer `rescue_worthiness` score for each Stage 1 sourced pass.
- Recovery: at most two technical retries after a failed first attempt. Every
  attempt is auditable; the first valid judgment is final.

The prompt templates in `prompts.py` remain unchanged. Their SHA-256 values are
stored in each run manifest.

## SCCKN Setup

From the SCCKN repository root:

```bash
jobs/submit_llm_validation.sh --dry-run setup
jobs/submit_llm_validation.sh setup
```

The setup job creates a pinned Python environment under `/work`, installs
vLLM, removes its optional `torchcodec` video backend for this text-only run,
and downloads the 62.6 GB model into the existing `/work` Hugging Face cache.
No API key is required.

## Smoke

```bash
jobs/submit_llm_validation.sh --dry-run smoke
jobs/submit_llm_validation.sh smoke
```

The fixed 128-note smoke runs only Stage 1 and writes under
`.artifacts/smoke/llm_validation/gemma-4-31b-it-scckn-v1/`. It tests
concurrency 16, 32, and 64 without evaluating any note more than once, checks
resume-safe storage, and writes `benchmark.json` with the recommended
production concurrency and batch cap.

Production must not start unless `benchmark.json` reports `accepted: true`.

## Stage 1 Production

After reviewing the smoke recommendation:

```bash
jobs/submit_llm_validation.sh stage1 <max_notes> <concurrency>
jobs/submit_llm_validation.sh stage2 <max_notes> <concurrency>
```

After the first canonical 2,000-note Stage 1 batch, the remaining fixed
manifest can run as disjoint SGE array tasks:

```bash
jobs/submit_llm_validation.sh --dry-run stage1-array 2-7 3 64
jobs/submit_llm_validation.sh stage1-array 2-7 3 64
python3 notebooks/llm_validation/run_validation.py shard-status
```

Tasks 2-7 cover canonical manifest rows 2,000-13,655 in five 2,000-note
shards and one 1,655-note shard. `-tc 3` permits at most three tasks (six L40S
GPUs) to run concurrently. The array is pinned to SCCKN's verified L40S host,
and each task rejects any non-L40S allocation before model startup. Each task
uses a distinct local vLLM port, log,
exclusive lock, and SQLite database under
`data/llm_validation/runs/gemma-4-31b-it-scckn-v1/shards/`. Resubmitting the
same task reads its existing database and evaluates only pending notes.

Shard calls are not merged into the canonical production database
automatically. Review remains mandatory before a controlled merge.

After transferring and auditing the complete run directory locally, merge the
reviewed shards with:

```bash
python3 notebooks/llm_validation/run_validation.py merge-stage1-shards
```

The command verifies each shard manifest and run contract, rejects conflicting
attempt records, builds and validates a temporary SQLite database, and only
then atomically replaces the canonical database. It is idempotent: an exact
attempt already present in the canonical database is retained, while a record
with the same logical key and attempt number but different content stops the
merge. Final Parquet, raw JSONL, summary, and SQLite backup exports are rebuilt
from the merged canonical database.

The reviewed Stage 1 shards have been merged. Stage 2 refuses to start while
any Stage 1 note is pending. Calls exhausted after three invalid attempts are
terminal `unresolved`, not silently retried by later jobs.

## Isolated Stage 1.5 Opinion Recall

The optional Stage 1.5 analysis does not modify the canonical Stage 1 result.
It freezes the exact 1,703 notes resolved as `opinion_or_speculation` and asks
whether a substantial sourced factual core remains after subjective wording is
removed. The model receives only raw note text; parent labels, reasons, Gabriel
metadata, and upstream scores are excluded from the prompt.

Prepare locally without inference and inspect the frozen manifest:

```bash
python3 notebooks/llm_validation/run_validation.py stage1-5-prepare
```

Submit the complete bounded run on SCCKN:

```bash
jobs/submit_llm_validation.sh --dry-run stage1-5 1703 64
jobs/submit_llm_validation.sh stage1-5 1703 64
python3 notebooks/llm_validation/run_validation.py stage1-5-status
```

The first candidate judgment doubles as the model/reasoning preflight and is
then reused as its final Stage 1.5 result. All output is isolated under
`data/llm_validation/runs/gemma-4-31b-it-scckn-stage1-5-opinion-v1/`.
The summary reports the unchanged strict sourced count, newly admitted count,
expanded count, URL presence, and historical-label cross-tabs. Stage 2, human
audit, retrieval, and vector storage are outside this run.

## Expanded Stage 2

The expanded Stage 2 run is isolated under
`data/llm_validation/runs/gemma-4-31b-it-scckn-stage2-expanded-v1/`. Its frozen
manifest contains 10,096 strict Stage 1 sourced notes plus the 280 Stage 1.5
recall admissions, with no overlap. `admission_route` is retained for audit and
reporting but is never included in the model prompt. The existing Stage 2
prompt remains byte-for-byte unchanged (SHA-256
`8c98c54b9c413ee70c161f40ec8e89f0b19ac6420b2bfe669e7ee1f9b136c644`).
Each note receives one score, and the preregistered rescue threshold is 50.

The completed result is:

- 10,096 strict Stage 1 candidates, of which 8,527 pass Stage 2;
- 280 Stage 1.5 recall candidates, of which 31 pass Stage 2;
- 10,376 complete judgments and zero unresolved notes;
- **8,558 canonical final rescues** with `passes_rescue_threshold == True`.

Prepare and inspect the immutable 10,376-note contract locally without
inference:

```bash
python3 notebooks/llm_validation/run_validation.py stage2-expanded-prepare
jobs/submit_llm_validation.sh --dry-run stage2-expanded-array 1-6 3 64
```

Submit all six disjoint SCCKN shards after the committed contract is pulled:

```bash
jobs/submit_llm_validation.sh stage2-expanded-array 1-6 3 64
python3 notebooks/llm_validation/run_validation.py stage2-expanded-shard-status
```

Tasks 1-5 contain 2,000 notes each and task 6 contains 376. At most three
tasks run concurrently on `gpu@scc213`. Every shard has a separate manifest,
SQLite database, backup, exports, lock, local vLLM port, and logs. Each attempt
is committed immediately, exports refresh every 100 processed notes and on
graceful scheduler stop, and a resumed task skips terminal notes. The first
note in each shard is the model/reasoning preflight and its accepted score is
reused rather than evaluated twice.

The six production shards were reviewed and merged locally with:

```bash
python3 notebooks/llm_validation/run_validation.py merge-stage2-expanded-shards
```

The command requires every note to be complete or terminally unresolved, validates
route-aware manifest hashes and logical keys, rejects conflicts or missing
reasoning, and atomically replaces the canonical SQLite database only after a
successful temporary merge. Final reporting preserves the strict result
(`strict_stage1` passes at score >=50), expanded result (all passes), and the
Stage 1.5 contribution (`stage1_5_recall` passes).

Production output is isolated under
`data/llm_validation/runs/gemma-4-31b-it-scckn-stage2-expanded-v1/`:

- `calls.sqlite3` and `calls.backup.sqlite3`
- `calls.parquet` and `raw_calls.jsonl.gz`
- `input_manifest.parquet` and `.csv`
- `stage2_results.parquet` and `stage2_unresolved.parquet`
- prompt snapshots, `run_manifest.json`, and `summary.json`

The parent Stage 1 and Stage 1.5 results remain in their separately identified
run directories. The historical `data/gabriel/` tree is not an active output
or runtime dependency.

SGE stdout and stderr use job-specific files under
`.artifacts/logs/llm_validation/gemma-4-31b-it-scckn-v1/`; logs from resumed
batches are not overwritten or appended into one ambiguous file. Array vLLM
logs include both job and task IDs.

SQLite uses rollback journaling and full synchronous commits for SCCKN's NFS
`/work` filesystem. Every accepted note is committed immediately. Scheduler
notifications stop new work, let in-flight calls finish, and refresh atomically
written exports. Array jobs reserve a 15-minute soft-to-hard limit window so
the runner can finish in-flight requests. A hard kill can lose only unfinished
requests.

## Tests

```bash
python3 -m unittest discover -s notebooks/llm_validation -p 'test_*.py'
jobs/submit_llm_validation.sh --dry-run setup
jobs/submit_llm_validation.sh --dry-run smoke
jobs/submit_llm_validation.sh --dry-run stage1 2000 32
jobs/submit_llm_validation.sh --dry-run stage1-array 2-7 3 64
jobs/submit_llm_validation.sh --dry-run stage1-5 1703 64
jobs/submit_llm_validation.sh --dry-run stage2-expanded-array 1-6 3 64
```
