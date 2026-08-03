#!/usr/bin/env bash

# Fetch the two large canonical 200k interim files from Hugging Face.
set -euo pipefail

REPO_ID="vulonviing/community-notes-rescue-interim"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$ROOT/data/_hf_cache"
INTERIM="$ROOT/data/interim"

mkdir -p "$CACHE" "$INTERIM"
hf download "$REPO_ID" \
    --repo-type=dataset \
    --include "200k/ratings_filtered.parquet" "200k/ratings_clustered.parquet" \
    --local-dir "$CACHE"

mv "$CACHE/200k/ratings_filtered.parquet" "$INTERIM/ratings_filtered.parquet"
mv "$CACHE/200k/ratings_clustered.parquet" "$INTERIM/ratings_clustered.parquet"
rmdir "$CACHE/200k" "$CACHE" 2>/dev/null || true

ls -lh "$INTERIM/ratings_filtered.parquet" "$INTERIM/ratings_clustered.parquet"
