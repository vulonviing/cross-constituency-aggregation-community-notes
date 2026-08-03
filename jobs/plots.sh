#!/bin/bash

set -euo pipefail

PROJECT_ROOT="${SGE_O_WORKDIR:-$(pwd)}"
cd "$PROJECT_ROOT"

source jobs/_job_helpers.sh
submit_or_require_sge "plots"
configure_thread_limits

module load conda
source activate python-3.13

FIG_DIR="$(figure_root_from_config)"

run_notebook_stage \
    "plots" \
    "notebooks/06_plots.ipynb" \
    "${FIG_DIR}/figure_01_cluster_diagnostics.pdf" \
    "${FIG_DIR}/figure_03_strategy_status_counts.pdf" \
    "${FIG_DIR}/figure_04_high_disagreement_topics.pdf" \
    "${FIG_DIR}/figure_05_topic_cluster_polarity.pdf" \
    "${FIG_DIR}/figure_A1_cluster_tfidf.pdf" \
    "${FIG_DIR}/figure_A2a_disagreement_direction_bar.pdf" \
    "${FIG_DIR}/figure_A2b_disagreement_direction_scatter.pdf" \
    "${FIG_DIR}/figure_A3_user_profiling.pdf"
