#!/usr/bin/env bash

# Upload the three large canonical files to Hugging Face: the raw ingest
# output (master_full.parquet) and the two 200k interim ratings files.
set -euo pipefail

REPO_ID="vulonviing/community-notes-rescue-interim"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# local path (relative to repo root) | remote path in the HF dataset repo
pairs=(
    "data/master_full.parquet|master/master_full.parquet"
    "data/interim/ratings_filtered.parquet|200k/ratings_filtered.parquet"
    "data/interim/ratings_clustered.parquet|200k/ratings_clustered.parquet"
)

for pair in "${pairs[@]}"; do
    local_rel="${pair%%|*}"
    remote_path="${pair##*|}"
    local_path="$ROOT/$local_rel"
    if [ ! -f "$local_path" ]; then
        echo "Missing required file: $local_path" >&2
        exit 1
    fi
    hf upload "$REPO_ID" "$local_path" "$remote_path" --repo-type=dataset
done
