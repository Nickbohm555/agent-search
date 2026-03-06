#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

SPEC_PATH="${1:-openapi.json}"
OUTPUT_DIR="${2:-sdk/python}"
GENERATOR_IMAGE="${OPENAPI_GENERATOR_IMAGE:-openapitools/openapi-generator-cli}"
GENERATOR_LANG="${OPENAPI_GENERATOR_LANG:-python}"

ABS_SPEC_PATH="$REPO_ROOT/$SPEC_PATH"
ABS_OUTPUT_DIR="$REPO_ROOT/$OUTPUT_DIR"

if [ ! -f "$ABS_SPEC_PATH" ]; then
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") ERROR generate_sdk: spec not found at $ABS_SPEC_PATH" >&2
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO generate_sdk: run 'uv run --project src/backend python scripts/export_openapi.py' first" >&2
  exit 1
fi

mkdir -p "$ABS_OUTPUT_DIR"

echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO generate_sdk: starting image=$GENERATOR_IMAGE lang=$GENERATOR_LANG spec=$ABS_SPEC_PATH output=$ABS_OUTPUT_DIR"
docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "$REPO_ROOT:/local" \
  "$GENERATOR_IMAGE" generate \
  -i "/local/$SPEC_PATH" \
  -g "$GENERATOR_LANG" \
  -o "/local/$OUTPUT_DIR"
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO generate_sdk: generation complete spec=$ABS_SPEC_PATH output=$ABS_OUTPUT_DIR"
