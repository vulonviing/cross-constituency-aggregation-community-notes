#!/bin/bash

set -euo pipefail

if [ "${CN_LLM_SUBMIT_HELPER:-}" != "1" ] || [ -z "${JOB_ID:-}" ]; then
    echo "Use jobs/submit_llm_validation.sh setup." >&2
    exit 64
fi

PROJECT_ROOT="${SGE_O_WORKDIR:-$(pwd)}"
cd "$PROJECT_ROOT"

ENV_DIR="${LLM_VALIDATION_ENV_DIR:-/work/$USER/envs/community-notes-gemma4-v1}"
HF_HOME="${HF_HOME:-/work/$USER/hf_cache}"
MODEL="google/gemma-4-31B-it"
REVISION="518276fb130dc81caf9a4f772e65e63ef2526493"

module load conda
source /software/packages/anaconda/2024.10/etc/profile.d/conda.sh

if [ ! -x "$ENV_DIR/bin/python" ]; then
    conda create -y -p "$ENV_DIR" python=3.12 pip
fi

"$ENV_DIR/bin/python" -m pip install --upgrade pip
"$ENV_DIR/bin/python" -m pip install -r notebooks/llm_validation/requirements-scckn.txt
# torchcodec is an optional video backend for this text-only run. Its import
# requires cluster FFmpeg shared libraries even when no media input is used.
"$ENV_DIR/bin/python" -m pip uninstall -y torchcodec
"$ENV_DIR/bin/python" - <<'PY'
import openai
import pandas
import pyarrow
import torch
import transformers
import vllm

print("torch", torch.__version__)
print("transformers", transformers.__version__)
print("vllm", vllm.__version__)
print("openai", openai.__version__)
print("pandas", pandas.__version__)
print("pyarrow", pyarrow.__version__)
PY
"$ENV_DIR/bin/python" - <<'PY'
import importlib.util
import vllm.multimodal.video

if importlib.util.find_spec("torchcodec") is not None:
    raise RuntimeError("torchcodec must remain absent in the text-only runtime")
print("vllm text-only CLI imports OK")
PY

export HF_HOME
"$ENV_DIR/bin/hf" download "$MODEL" --revision "$REVISION"
echo "Setup complete: env=$ENV_DIR model=$MODEL revision=$REVISION HF_HOME=$HF_HOME"
