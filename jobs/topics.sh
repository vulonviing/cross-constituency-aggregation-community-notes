#!/bin/bash

set -euo pipefail

PROJECT_ROOT="${SGE_O_WORKDIR:-$(pwd)}"
cd "$PROJECT_ROOT"

source jobs/_job_helpers.sh
submit_or_require_sge "topics"
configure_thread_limits

module load conda
source activate python-3.13

TOPIC_DIR="$(data_root_from_config)/processed/topics"

run_notebook_stage \
    "topics" \
    "notebooks/03_topics.ipynb" \
    "${TOPIC_DIR}/topic_notes.parquet" \
    "${TOPIC_DIR}/topic_cluster_stats.parquet" \
    "${TOPIC_DIR}/topic_exemplars.parquet" \
    "${TOPIC_DIR}/topic_salience.parquet" \
    "${TOPIC_DIR}/topic_rescue_stats.parquet" \
    "${TOPIC_DIR}/topic_strategy_summary.parquet" \
    "${TOPIC_DIR}/topic_parent_notes_reassigned.parquet" \
    "${TOPIC_DIR}/topic_super_parent_notes.parquet"
