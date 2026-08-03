#!/usr/bin/env bash

# Fetch the three large canonical files from Hugging Face: the raw ingest
# output (master_full.parquet) and the two 200k interim ratings files.
set -euo pipefail

REPO_ID="vulonviing/community-notes-rescue-interim"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$ROOT/data/_hf_cache"

mkdir -p "$CACHE"
hf download "$REPO_ID" \
    --repo-type=dataset \
    --include "master/master_full.parquet" "200k/ratings_filtered.parquet" "200k/ratings_clustered.parquet" \
    --local-dir "$CACHE"

mkdir -p "$ROOT/data/interim"
mv "$CACHE/master/master_full.parquet" "$ROOT/data/master_full.parquet"
mv "$CACHE/200k/ratings_filtered.parquet" "$ROOT/data/interim/ratings_filtered.parquet"
mv "$CACHE/200k/ratings_clustered.parquet" "$ROOT/data/interim/ratings_clustered.parquet"
rmdir "$CACHE/master" "$CACHE/200k" "$CACHE" 2>/dev/null || true

ls -lh "$ROOT/data/master_full.parquet" \
    "$ROOT/data/interim/ratings_filtered.parquet" \
    "$ROOT/data/interim/ratings_clustered.parquet"
