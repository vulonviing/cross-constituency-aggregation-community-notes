# ai-usage/

This directory holds an **append-only** record of the work done by models and agents
running in the repository. The purpose is to maintain an auditable, continuous history
of which model did what and when.

## Rule (HARD RULE)

The use of this directory is defined as a **HARD RULE** in `AGENTS.md` and is binding
for every model and agent. Summary:

> After completing each meaningful unit of work, every agent must **append** a step
> entry to `ai-usage/step_logs/STEP_LOG.md`. Existing entries must never be touched,
> overwritten, or renumbered.

## File Structure

```
ai-usage/
├── README.md          ← this file
└── step_logs/
    └── STEP_LOG.md    ← single rolling log file
```

## Numbering

The step number increases **globally and continuously**. Each new entry takes the
number one above the last step in the file. It does not reset on session, day, or
model change.

## Granularity

Each **meaningful unit of work** is one step — not "every model turn." Examples:

- `jobs/` refactored → 1 step
- Hard rule added to `AGENTS.md` → 1 step
- Multiple small file edits that are part of a single task → 1 step

## Canonical Format

```markdown
## Step <N> — <short title>
- **Date:** YYYY-MM-DD HH:MM ±TZ
- **Model:** <model-id, e.g. claude-sonnet-4-6>
- <what was done, bullet>
- <bullet>
- <verification/result, bullet>
```

### Example

```markdown
## Step 3 — removed executed notebook generation from jobs/
- **Date:** 2026-06-25 14:40 +0200
- **Model:** claude-sonnet-4-6
- `jobs/_job_helpers.sh` refactored; notebook output suppressed with `--stdout > /dev/null`
- Removed `.executed.ipynb` lines from 6 stage scripts
- `bash -n` syntax check passed; `notebooks_executed/` reference cleared
```

## To Append

Write the new entry at the end of STEP_LOG.md. Do not modify previous entries.
