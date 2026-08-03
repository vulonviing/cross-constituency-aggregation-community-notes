#!/bin/bash

set -euo pipefail

PROJECT_ROOT="${SGE_O_WORKDIR:-$(pwd)}"
cd "$PROJECT_ROOT"

source jobs/_job_helpers.sh
submit_or_require_sge "paper_visuals"
configure_thread_limits

module load conda
source activate python-3.13

FIG_DIR="$(figure_root_from_config)"

run_notebook_stage \
    "paper_visuals" \
    "notebooks/07_paper_visuals.ipynb" \
    "${FIG_DIR}/07_fig1_cluster_signatures.pdf" \
    "${FIG_DIR}/07_fig2_representative_mechanism.pdf" \
    "${FIG_DIR}/07_fig2b_llm_edge_cases.pdf" \
    "${FIG_DIR}/07_fig3_pool_and_topics.pdf" \
    "${FIG_DIR}/07_fig5_rescue_panels.pdf"
