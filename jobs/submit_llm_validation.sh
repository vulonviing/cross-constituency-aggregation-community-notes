#!/bin/bash

set -euo pipefail

usage() {
    echo "Usage: jobs/submit_llm_validation.sh [--dry-run] setup|smoke|stage1|stage1-5|stage2 [max_notes] [concurrency]" >&2
    echo "       jobs/submit_llm_validation.sh [--dry-run] stage1-array [task_range] [max_concurrent] [concurrency]" >&2
    echo "       jobs/submit_llm_validation.sh [--dry-run] stage2-expanded-array [task_range] [max_concurrent] [concurrency]" >&2
    exit 64
}

dry_run=0
if [ "${1:-}" = "--dry-run" ]; then
    dry_run=1
    shift
fi

action="${1:-}"
[ -n "$action" ] || usage
shift || true
max_notes="${1:-}"
concurrency="${2:-32}"

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
RUN_LOG_ID="gemma-4-31b-it-scckn-v1"
if [ "$action" = "stage1-5" ]; then
    RUN_LOG_ID="gemma-4-31b-it-scckn-stage1-5-opinion-v1"
elif [ "$action" = "stage2-expanded-array" ]; then
    RUN_LOG_ID="gemma-4-31b-it-scckn-stage2-expanded-v1"
fi
LOG_ROOT=".artifacts/logs/llm_validation/$RUN_LOG_ID"
mkdir -p "$LOG_ROOT"

case "$action" in
    setup)
        script="jobs/llm_validation_setup.sh"
        qsub_args=(
            -S /bin/bash -N cn_gemma_setup -q scc -pe smp 2
            -l h_vmem=32G,h_rt=06:00:00
            -o "$LOG_ROOT" -e "$LOG_ROOT" -cwd
            -v CN_LLM_SUBMIT_HELPER=1
            "$script"
        )
        ;;
    smoke)
        script="jobs/llm_validation_gpu.sh"
        qsub_args=(
            -S /bin/bash -N cn_gemma_smoke -q gpu -pe smp 8
            -l gpu=2,tesla_l40=1,h_vmem=64G,s_rt=05:58:30,h_rt=06:00:00
            -notify -o "$LOG_ROOT" -e "$LOG_ROOT" -cwd
            -v "CN_LLM_SUBMIT_HELPER=1,LLM_VALIDATION_ACTION=smoke,LLM_VALIDATION_CONCURRENCY=32"
            "$script"
        )
        ;;
    stage1|stage1-5|stage2)
        [[ "$max_notes" =~ ^[1-9][0-9]*$ ]] || usage
        [[ "$concurrency" =~ ^[1-9][0-9]*$ ]] || usage
        if [ "$action" = "stage1-5" ] && [ "$concurrency" -ne 64 ]; then
            echo "Stage 1.5 concurrency is frozen at 64" >&2
            exit 64
        fi
        script="jobs/llm_validation_gpu.sh"
        job_stage="$action"
        if [ "$action" = "stage1-5" ]; then
            job_stage="s15"
        fi
        qsub_args=(
            -S /bin/bash -N "cn_gemma_${job_stage}" -q gpu -pe smp 8
            -l gpu=2,tesla_l40=1,h_vmem=64G,s_rt=11:58:30,h_rt=12:00:00
            -notify -o "$LOG_ROOT" -e "$LOG_ROOT" -cwd
            -v "CN_LLM_SUBMIT_HELPER=1,LLM_VALIDATION_ACTION=${action},LLM_VALIDATION_MAX_NOTES=${max_notes},LLM_VALIDATION_CONCURRENCY=${concurrency}"
            "$script"
        )
        ;;
    stage1-array)
        task_range="${1:-2-7}"
        max_concurrent="${2:-3}"
        request_concurrency="${3:-64}"
        [[ "$task_range" =~ ^([2-9][0-9]*|[2-9][0-9]*-[2-9][0-9]*)$ ]] || usage
        [[ "$max_concurrent" =~ ^[1-9][0-9]*$ ]] || usage
        [[ "$request_concurrency" =~ ^[1-9][0-9]*$ ]] || usage
        script="jobs/llm_validation_gpu.sh"
        qsub_args=(
            -S /bin/bash -N cn_gemma_s1_shard -q gpu@scc213 -pe smp 8
            -l gpu=2,tesla_l40=1,h_vmem=64G,s_rt=11:45:00,h_rt=12:00:00
            -notify -t "$task_range" -tc "$max_concurrent"
            -o "$LOG_ROOT" -e "$LOG_ROOT" -cwd
            -v "CN_LLM_SUBMIT_HELPER=1,LLM_VALIDATION_ACTION=stage1-shard,LLM_VALIDATION_SHARD_SIZE=2000,LLM_VALIDATION_CONCURRENCY=${request_concurrency}"
            "$script"
        )
        ;;
    stage2-expanded-array)
        task_range="${1:-1-6}"
        max_concurrent="${2:-3}"
        request_concurrency="${3:-64}"
        [[ "$task_range" =~ ^([1-9][0-9]*|[1-9][0-9]*-[1-9][0-9]*)$ ]] || usage
        [[ "$max_concurrent" =~ ^[1-9][0-9]*$ ]] || usage
        [[ "$request_concurrency" =~ ^[1-9][0-9]*$ ]] || usage
        if [ "$request_concurrency" -ne 64 ]; then
            echo "Expanded Stage 2 concurrency is frozen at 64" >&2
            exit 64
        fi
        script="jobs/llm_validation_gpu.sh"
        qsub_args=(
            -S /bin/bash -N cn_gemma_s2e -q gpu@scc213 -pe smp 8
            -l gpu=2,tesla_l40=1,h_vmem=64G,s_rt=11:45:00,h_rt=12:00:00
            -notify -t "$task_range" -tc "$max_concurrent"
            -o "$LOG_ROOT" -e "$LOG_ROOT" -cwd
            -v "CN_LLM_SUBMIT_HELPER=1,LLM_VALIDATION_ACTION=stage2-expanded-shard,LLM_VALIDATION_SHARD_SIZE=2000,LLM_VALIDATION_CONCURRENCY=${request_concurrency}"
            "$script"
        )
        ;;
    *)
        usage
        ;;
esac

if [ "$dry_run" -eq 1 ]; then
    printf "qsub"
    printf " %q" "${qsub_args[@]}"
    printf "\n"
    exit 0
fi

qsub -terse "${qsub_args[@]}"
