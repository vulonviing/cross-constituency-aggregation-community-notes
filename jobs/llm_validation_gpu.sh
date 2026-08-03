#!/bin/bash

set -euo pipefail

if [ "${CN_LLM_SUBMIT_HELPER:-}" != "1" ] || [ -z "${JOB_ID:-}" ]; then
    echo "Use jobs/submit_llm_validation.sh smoke|stage1|stage2." >&2
    exit 64
fi

PROJECT_ROOT="${SGE_O_WORKDIR:-$(pwd)}"
cd "$PROJECT_ROOT"

ACTION="${LLM_VALIDATION_ACTION:?LLM_VALIDATION_ACTION is required}"
MAX_NOTES="${LLM_VALIDATION_MAX_NOTES:-}"
CONCURRENCY="${LLM_VALIDATION_CONCURRENCY:-32}"
ENV_DIR="${LLM_VALIDATION_ENV_DIR:-/work/$USER/envs/community-notes-gemma4-v1}"
export HF_HOME="${HF_HOME:-/work/$USER/hf_cache}"
export LLM_VALIDATION_MODEL="google/gemma-4-31B-it"
export LLM_VALIDATION_MODEL_REVISION="518276fb130dc81caf9a4f772e65e63ef2526493"
export LLM_VALIDATION_CONCURRENCY="$CONCURRENCY"
export VLLM_VERSION="$($ENV_DIR/bin/python -c 'import vllm; print(vllm.__version__)')"

RUN_LOG_ID="gemma-4-31b-it-scckn-v1"
if [ "$ACTION" = "stage1-5" ]; then
    RUN_LOG_ID="gemma-4-31b-it-scckn-stage1-5-opinion-v1"
elif [ "$ACTION" = "stage2-expanded-shard" ]; then
    RUN_LOG_ID="gemma-4-31b-it-scckn-stage2-expanded-v1"
fi
LOG_ROOT=".artifacts/logs/llm_validation/$RUN_LOG_ID"
mkdir -p "$LOG_ROOT"
TASK_ID=0
if [[ "${SGE_TASK_ID:-}" =~ ^[0-9]+$ ]]; then
    TASK_ID="$SGE_TASK_ID"
fi
PORT="$((20000 + (JOB_ID % 20000) + TASK_ID))"
export LLM_VALIDATION_BASE_URL="http://127.0.0.1:${PORT}/v1"
LOG_SUFFIX="$JOB_ID"
if [ "$TASK_ID" -gt 0 ]; then
    LOG_SUFFIX="${JOB_ID}.${TASK_ID}"
fi
SERVER_LOG="$LOG_ROOT/vllm-${LOG_SUFFIX}.log"
SERVER_PID=""
RUNNER_PID=""
STOP_REQUESTED=0

if [ "$ACTION" = "stage1-shard" ]; then
    if [ "$TASK_ID" -lt 2 ]; then
        echo "stage1-shard requires SGE_TASK_ID >= 2" >&2
        exit 64
    fi
    SHARD_SIZE="${LLM_VALIDATION_SHARD_SIZE:-2000}"
    SHARD_ROOT="data/llm_validation/runs/gemma-4-31b-it-scckn-v1/shards/stage1-batch-$(printf '%04d' "$TASK_ID")"
    mkdir -p "$SHARD_ROOT"
    exec 9>"$SHARD_ROOT/task.lock"
    if ! flock -n 9; then
        echo "Stage 1 shard batch $TASK_ID is already running" >&2
        exit 73
    fi
fi

if [ "$ACTION" = "stage2-expanded-shard" ]; then
    if [ "$TASK_ID" -lt 1 ]; then
        echo "stage2-expanded-shard requires SGE_TASK_ID >= 1" >&2
        exit 64
    fi
    SHARD_SIZE="${LLM_VALIDATION_SHARD_SIZE:-2000}"
    SHARD_ROOT="data/llm_validation/runs/gemma-4-31b-it-scckn-stage2-expanded-v1/shards/stage2-batch-$(printf '%04d' "$TASK_ID")"
    mkdir -p "$SHARD_ROOT"
    exec 9>"$SHARD_ROOT/task.lock"
    if ! flock -n 9; then
        echo "Expanded Stage 2 shard batch $TASK_ID is already running" >&2
        exit 73
    fi
fi

cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill -TERM "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}

graceful_stop() {
    STOP_REQUESTED=1
    echo "[scheduler] notification received; stopping new validation work"
    if [ -n "$RUNNER_PID" ] && kill -0 "$RUNNER_PID" 2>/dev/null; then
        kill -USR1 "$RUNNER_PID" 2>/dev/null || true
    fi
}

trap graceful_stop USR1 TERM XCPU
trap cleanup EXIT

module load cuda/13.2
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

mapfile -t allocated_gpu_names < <("$ENV_DIR/bin/python" - <<'PY'
import torch
for index in range(torch.cuda.device_count()):
    print(torch.cuda.get_device_name(index))
PY
)
if [ "${#allocated_gpu_names[@]}" -ne 2 ]; then
    echo "Expected exactly two allocated GPUs, found ${#allocated_gpu_names[@]}" >&2
    exit 2
fi
printf 'Allocated GPU: %s\n' "${allocated_gpu_names[@]}"
for gpu_name in "${allocated_gpu_names[@]}"; do
    if [ "$gpu_name" != "NVIDIA L40S" ]; then
        echo "Expected NVIDIA L40S, found $gpu_name" >&2
        exit 6
    fi
done
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

if ss -ltn "sport = :$PORT" | grep -q LISTEN; then
    echo "Selected local vLLM port $PORT is already in use" >&2
    exit 5
fi

load_started="$(date +%s)"
"$ENV_DIR/bin/vllm" serve "$LLM_VALIDATION_MODEL" \
    --revision "$LLM_VALIDATION_MODEL_REVISION" \
    --tensor-parallel-size 2 \
    --dtype bfloat16 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.90 \
    --max-num-seqs 64 \
    --max-num-batched-tokens 32768 \
    --enable-prefix-caching \
    --async-scheduling \
    --language-model-only \
    --reasoning-parser gemma4 \
    --host 127.0.0.1 \
    --port "$PORT" >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

ready=0
for _ in $(seq 1 120); do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "vLLM exited during startup" >&2
        tail -n 120 "$SERVER_LOG" >&2 || true
        exit 3
    fi
    if curl --silent --fail "http://127.0.0.1:${PORT}/health" >/dev/null; then
        ready=1
        break
    fi
    sleep 10
done
if [ "$ready" -ne 1 ]; then
    echo "vLLM did not become healthy within 20 minutes" >&2
    tail -n 120 "$SERVER_LOG" >&2 || true
    exit 4
fi
export VLLM_LOAD_SECONDS="$(( $(date +%s) - load_started ))"
echo "vLLM ready in ${VLLM_LOAD_SECONDS}s; action=$ACTION concurrency=$CONCURRENCY"

case "$ACTION" in
    smoke)
        command=("$ENV_DIR/bin/python" notebooks/llm_validation/run_validation.py smoke)
        ;;
    stage1|stage2)
        if [ -z "$MAX_NOTES" ]; then
            echo "LLM_VALIDATION_MAX_NOTES is required for $ACTION" >&2
            exit 64
        fi
        command=("$ENV_DIR/bin/python" notebooks/llm_validation/run_validation.py \
            --concurrency "$CONCURRENCY" "$ACTION" --max-notes "$MAX_NOTES")
        ;;
    stage1-5)
        if [ -z "$MAX_NOTES" ]; then
            echo "LLM_VALIDATION_MAX_NOTES is required for $ACTION" >&2
            exit 64
        fi
        command=("$ENV_DIR/bin/python" notebooks/llm_validation/run_validation.py \
            --concurrency "$CONCURRENCY" stage1-5 --max-notes "$MAX_NOTES")
        ;;
    stage1-shard)
        command=("$ENV_DIR/bin/python" notebooks/llm_validation/run_validation.py \
            --concurrency "$CONCURRENCY" stage1-shard \
            --batch-number "$TASK_ID" --batch-size "$SHARD_SIZE")
        ;;
    stage2-expanded-shard)
        command=("$ENV_DIR/bin/python" notebooks/llm_validation/run_validation.py \
            --concurrency "$CONCURRENCY" stage2-expanded-shard \
            --batch-number "$TASK_ID" --batch-size "$SHARD_SIZE")
        ;;
    *)
        echo "Unknown action: $ACTION" >&2
        exit 64
        ;;
esac

"${command[@]}" &
RUNNER_PID=$!
while true; do
    set +e
    wait "$RUNNER_PID"
    runner_rc=$?
    set -e
    if kill -0 "$RUNNER_PID" 2>/dev/null; then
        continue
    fi
    break
done
RUNNER_PID=""

if [ "$runner_rc" -ne 0 ]; then
    if [ "$STOP_REQUESTED" -eq 1 ] && [ "$runner_rc" -eq 75 ]; then
        echo "Validation checkpointed after scheduler notification" >&2
    fi
    echo "Validation runner exited with code $runner_rc" >&2
    exit "$runner_rc"
fi
echo "Validation action completed: $ACTION"
