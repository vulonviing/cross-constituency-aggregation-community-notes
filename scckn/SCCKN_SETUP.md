# SCCKN Setup

## Connection

```text
Host: scc.uni-konstanz.de
User: emrecan.ulu
Work directory: /work/emrecan.ulu/
```

Connect with:

```bash
ssh scckn
```

Store the repository and raw snapshot under `/work`, not under the 100 GB home
directory quota.

## Transfer

Use `rsync` for reproducible transfers:

```bash
rsync -avhSPz ./community-notes-x-rescue-main/ \
  emrecan.ulu@scc.uni-konstanz.de:/work/emrecan.ulu/community-notes-x-rescue-main/
```

Large generated data can be excluded or transferred separately. Never upload
the local `.env`.

## Python

```bash
module load conda
source activate python-3.13
python -c "import pandas, pyarrow, sklearn, pyamg"
```

The active stage commands are documented in
[JOB_SUBMISSION.md](JOB_SUBMISSION.md). General storage and queue information
remains in [STORAGE.md](STORAGE.md), [RULES.md](RULES.md), and
[TIPS.md](TIPS.md).

## Gemma 4 Validation Runtime

The Community Notes validation uses an isolated environment and Hugging Face
cache under `/work`:

```text
Environment: /work/emrecan.ulu/envs/community-notes-gemma4-v1
HF_HOME:     /work/emrecan.ulu/hf_cache
Model:       google/gemma-4-31B-it
GPUs:        2 x NVIDIA L40, BF16 tensor parallel
```

Create or refresh the runtime through SGE rather than installing packages in a
shared system environment:

```bash
jobs/submit_llm_validation.sh setup
```

The setup is idempotent and pins the model revision and vLLM version used by
the run manifest.
