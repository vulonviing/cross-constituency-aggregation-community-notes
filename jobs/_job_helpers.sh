#!/bin/bash

set -euo pipefail

timestamp() {
    date "+%Y-%m-%dT%H:%M:%S%z"
}

config_value() {
    local key="$1"
    local default="${2:-}"
    local value
    value="$(
        awk -F= -v key="$key" '
            $1 ~ "^[[:space:]]*" key "[[:space:]]*$" {
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2)
                print $2
                exit
            }
        ' config.txt 2>/dev/null || true
    )"
    printf "%s" "${value:-$default}"
}

test_mode_from_config() {
    if [ "$(config_value TEST_MODE 0)" = "1" ]; then
        printf "1"
    else
        printf "0"
    fi
}

run_root_from_config() {
    if [ "$(test_mode_from_config)" = "1" ]; then
        printf ".artifacts/smoke"
    else
        printf "."
    fi
}

data_root_from_config() {
    printf "%s/data" "$(run_root_from_config)"
}

figure_root_from_config() {
    printf "%s/figures/notebook_figures" "$(run_root_from_config)"
}

log_root_from_config() {
    if [ "$(test_mode_from_config)" = "1" ]; then
        printf ".artifacts/smoke/logs"
    else
        printf ".artifacts/logs"
    fi
}

submit_or_require_sge() {
    local stage="$1"

    if [ -z "${JOB_ID:-}" ]; then
        exec jobs/submit_stage.sh "$stage"
    fi

    if [ "${CN_SUBMIT_HELPER:-}" != "1" ]; then
        echo "[$stage] Refusing direct qsub submission." >&2
        echo "[$stage] Use jobs/submit_stage.sh $stage so resources match config.txt." >&2
        exit 64
    fi
}

configure_thread_limits() {
    local threads="${NSLOTS:-1}"

    export OMP_NUM_THREADS="$threads"
    export OPENBLAS_NUM_THREADS="$threads"
    export MKL_NUM_THREADS="$threads"
    export VECLIB_MAXIMUM_THREADS="$threads"
    export NUMEXPR_NUM_THREADS="$threads"

    echo "[resources] JOB_ID=${JOB_ID:-unknown} NSLOTS=${NSLOTS:-1}"
    echo "[resources] Thread limits set to ${threads}"
}

write_stage_status() {
    local status_file="$1"
    local status="$2"
    local exit_code="$3"
    local started_at="$4"
    local finished_at="$5"
    local stage="$6"
    local notebook="$7"
    local nbconvert_stderr="$8"
    shift 8

    {
        printf "status=%s\n" "$status"
        printf "exit_code=%s\n" "$exit_code"
        printf "stage=%s\n" "$stage"
        printf "started_at=%s\n" "$started_at"
        printf "finished_at=%s\n" "$finished_at"
        printf "host=%s\n" "$(hostname)"
        printf "notebook=%s\n" "$notebook"
        printf "nbconvert_stderr=%s\n" "$nbconvert_stderr"
        if [ "$#" -gt 0 ]; then
            printf "expected_outputs=%s\n" "$*"
        fi
    } > "$status_file"
}

run_notebook_stage() {
    local stage="$1"
    local notebook="$2"
    shift 2

    local log_root
    local status_file
    local running_file
    local nbconvert_stderr
    local started_at
    local finished_at
    local rc
    local missing

    log_root="$(log_root_from_config)"
    status_file="${log_root}/${stage}.status"
    running_file="${log_root}/${stage}.running"
    nbconvert_stderr="${log_root}/${stage}.nbconvert.stderr"

    mkdir -p "$log_root"
    rm -f "$status_file" "$running_file" "$nbconvert_stderr"
    for expected_output in "$@"; do
        rm -f "$expected_output"
    done

    started_at="$(timestamp)"
    {
        printf "stage=%s\n" "$stage"
        printf "started_at=%s\n" "$started_at"
        printf "host=%s\n" "$(hostname)"
        printf "notebook=%s\n" "$notebook"
        if [ "$#" -gt 0 ]; then
            printf "expected_outputs=%s\n" "$*"
        fi
    } > "$running_file"

    echo "[$stage] START $(timestamp)"
    echo "[$stage] Notebook: $notebook"

    set +e
    jupyter nbconvert --to notebook --execute \
        "$notebook" \
        --ExecutePreprocessor.timeout=-1 \
        --stdout > /dev/null \
        2> "$nbconvert_stderr"
    rc=$?
    set -e

    finished_at="$(timestamp)"

    if [ "$rc" -ne 0 ]; then
        echo "[$stage] FAILED: nbconvert exited with code $rc" >&2
        tail -n 80 "$nbconvert_stderr" >&2 || true
        write_stage_status "$status_file" "FAILED" "$rc" "$started_at" "$finished_at" \
            "$stage" "$notebook" "$nbconvert_stderr" "$@"
        rm -f "$running_file"
        exit "$rc"
    fi

    missing=0
    for expected_output in "$@"; do
        if [ ! -s "$expected_output" ]; then
            echo "[$stage] FAILED: missing expected output: $expected_output" >&2
            missing=1
        fi
    done

    if [ "$missing" -ne 0 ]; then
        write_stage_status "$status_file" "FAILED" "2" "$started_at" "$finished_at" \
            "$stage" "$notebook" "$nbconvert_stderr" "$@"
        rm -f "$running_file"
        exit 2
    fi

    write_stage_status "$status_file" "OK" "0" "$started_at" "$finished_at" \
        "$stage" "$notebook" "$nbconvert_stderr" "$@"
    rm -f "$running_file"
    echo "[$stage] END $(timestamp)"
}
