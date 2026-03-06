#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

SPEC_PATH="${1:-openapi.json}"
OUTPUT_DIR="${2:-sdk/python}"

echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO update_sdk: start spec=$SPEC_PATH output=$OUTPUT_DIR"

(
  cd "$REPO_ROOT"
  uv run --project src/backend python scripts/export_openapi.py --output "$SPEC_PATH"
)
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO update_sdk: openapi export complete spec=$SPEC_PATH"

"$REPO_ROOT/scripts/generate_sdk.sh" "$SPEC_PATH" "$OUTPUT_DIR"
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO update_sdk: sdk refresh complete spec=$SPEC_PATH output=$OUTPUT_DIR"
