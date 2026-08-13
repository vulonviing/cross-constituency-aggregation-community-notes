#!/usr/bin/env bash

# Verify the SHA-256 manifest of every Gemma validation run.
#
# Each run directory under data/llm_validation/runs/ carries a checksums.sha256
# listing the hash of every file it contains. This script checks all of them and
# fails if any file is missing or has changed.
#
#     bash scripts/verify_llm_checksums.sh          # summary only
#     bash scripts/verify_llm_checksums.sh -v       # list every file checked
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNS="$ROOT/data/llm_validation/runs"
VERBOSE=0
[[ "${1:-}" == "-v" || "${1:-}" == "--verbose" ]] && VERBOSE=1

if ! command -v shasum >/dev/null 2>&1; then
    echo "error: shasum not found" >&2
    exit 2
fi

if [[ ! -d "$RUNS" ]]; then
    echo "error: $RUNS does not exist" >&2
    exit 2
fi

status=0
checked=0

for run in "$RUNS"/*/; do
    name="$(basename "$run")"
    manifest="$run/checksums.sha256"

    if [[ ! -f "$manifest" ]]; then
        echo "MISSING MANIFEST  $name"
        status=1
        continue
    fi

    total="$(grep -c . "$manifest")"
    output="$(cd "$run" && shasum -a 256 -c checksums.sha256 2>&1)"

    if [[ $VERBOSE -eq 1 ]]; then
        echo "=== $name"
        echo "$output"
    fi

    failed="$(printf '%s\n' "$output" | grep -c "FAILED" || true)"
    if [[ "$failed" -eq 0 ]]; then
        printf 'OK      %-46s %s files\n' "$name" "$total"
    else
        printf 'FAILED  %-46s %s of %s files\n' "$name" "$failed" "$total"
        [[ $VERBOSE -eq 0 ]] && printf '%s\n' "$output" | grep "FAILED" | sed 's/^/          /'
        status=1
    fi
    checked=$((checked + 1))
done

echo
if [[ $status -eq 0 ]]; then
    echo "All $checked run manifests verify clean."
else
    echo "Verification failed. Re-run with -v for the full report." >&2
fi

exit $status
