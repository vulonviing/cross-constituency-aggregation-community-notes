#!/bin/bash

set -euo pipefail

PROJECT_ROOT="${SGE_O_WORKDIR:-$(pwd)}"
cd "$PROJECT_ROOT"

source jobs/_job_helpers.sh
submit_or_require_sge "clustering"
configure_thread_limits

module load conda
source activate python-3.13

INTERIM_DIR="$(data_root_from_config)/interim"

run_notebook_stage \
    "clustering" \
    "notebooks/01_clustering.ipynb" \
    "${INTERIM_DIR}/ratings_filtered.parquet" \
    "${INTERIM_DIR}/ratings_clustered.parquet" \
    "${INTERIM_DIR}/user_clusters.parquet" \
    "${INTERIM_DIR}/user_clusters_method_b_voteprofile.parquet" \
    "${INTERIM_DIR}/silhouette_over_k.parquet" \
    "${INTERIM_DIR}/stability_over_k.parquet" \
    "${INTERIM_DIR}/user_stats.parquet" \
    "${INTERIM_DIR}/cluster_summary.parquet"
