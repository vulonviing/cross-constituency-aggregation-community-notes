#!/usr/bin/env bash

# Upload the two large canonical 200k interim files to Hugging Face.
set -euo pipefail

REPO_ID="vulonviing/community-notes-rescue-interim"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

for name in ratings_filtered.parquet ratings_clustered.parquet; do
    local_path="$ROOT/data/interim/$name"
    if [ ! -f "$local_path" ]; then
        echo "Missing required file: $local_path" >&2
        exit 1
    fi
    hf upload "$REPO_ID" "$local_path" "200k/$name" --repo-type=dataset
done
