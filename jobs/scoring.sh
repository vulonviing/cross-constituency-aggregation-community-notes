#!/bin/bash

set -euo pipefail

PROJECT_ROOT="${SGE_O_WORKDIR:-$(pwd)}"
cd "$PROJECT_ROOT"

source jobs/_job_helpers.sh
submit_or_require_sge "scoring"
configure_thread_limits

module load conda
source activate python-3.13

PROCESSED_DIR="$(data_root_from_config)/processed"

run_notebook_stage \
    "scoring" \
    "notebooks/02_scoring.ipynb" \
    "${PROCESSED_DIR}/scores.parquet" \
    "${PROCESSED_DIR}/final_table.parquet" \
    "${PROCESSED_DIR}/rescue_summary.parquet" \
    "${PROCESSED_DIR}/pluralistic_breakdown.parquet" \
    "${PROCESSED_DIR}/selection_log.parquet" \
    "${PROCESSED_DIR}/selection_status_summary.parquet" \
    "${PROCESSED_DIR}/diagnostic_notes.parquet"
