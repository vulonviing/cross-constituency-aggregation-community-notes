#!/bin/bash

set -euo pipefail

PROJECT_ROOT="${SGE_O_WORKDIR:-$(pwd)}"
cd "$PROJECT_ROOT"

source jobs/_job_helpers.sh
submit_or_require_sge "ingest"
configure_thread_limits

module load conda
source activate python-3.13

DATA_ROOT="$(data_root_from_config)"

run_notebook_stage \
    "ingest" \
    "notebooks/00_ingest.ipynb" \
    "${DATA_ROOT}/master_full.parquet"
