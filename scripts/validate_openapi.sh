#!/usr/bin/env sh
set -eu

SPEC_PATH="${1:-openapi.json}"
REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ABS_SPEC_PATH="$REPO_ROOT/$SPEC_PATH"

if [ ! -f "$ABS_SPEC_PATH" ]; then
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") ERROR validate_openapi: spec not found at $ABS_SPEC_PATH" >&2
  exit 1
fi

echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: starting validation spec=$ABS_SPEC_PATH"
docker run --rm \
  -v "$REPO_ROOT:/local" \
  openapitools/openapi-generator-cli validate \
  -i "/local/$SPEC_PATH"
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: validation passed spec=$ABS_SPEC_PATH"
