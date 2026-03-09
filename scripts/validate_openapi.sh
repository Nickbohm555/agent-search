#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

SPEC_PATH="${1:-openapi.json}"
SDK_DIR="${2:-sdk/python}"
GENERATOR_IMAGE="${OPENAPI_GENERATOR_IMAGE:-openapitools/openapi-generator-cli}"
GENERATOR_LANG="${OPENAPI_GENERATOR_LANG:-python}"

ABS_SPEC_PATH="$REPO_ROOT/$SPEC_PATH"
ABS_SDK_DIR="$REPO_ROOT/$SDK_DIR"

TMP_ROOT="$(mktemp -d "$REPO_ROOT/.openapi-drift.XXXXXX")"
TMP_SPEC_PATH="$TMP_ROOT/runtime-openapi.json"
TMP_SPEC_REL_PATH="${TMP_SPEC_PATH#"$REPO_ROOT/"}"
TMP_SPEC_NORMALIZED="$TMP_ROOT/runtime-openapi.normalized.json"
SPEC_NORMALIZED="$TMP_ROOT/committed-openapi.normalized.json"
TMP_SDK_DIR="$TMP_ROOT/generated-sdk"
TMP_SDK_REL_PATH="${TMP_SDK_DIR#"$REPO_ROOT/"}"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT INT TERM

if [ ! -f "$ABS_SPEC_PATH" ]; then
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") ERROR validate_openapi: spec not found at $ABS_SPEC_PATH" >&2
  exit 1
fi

if [ ! -d "$ABS_SDK_DIR" ]; then
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") ERROR validate_openapi: sdk directory not found at $ABS_SDK_DIR" >&2
  exit 1
fi

echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: starting validation spec=$ABS_SPEC_PATH"
docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "$REPO_ROOT:/local" \
  "$GENERATOR_IMAGE" validate \
  -i "/local/$SPEC_PATH"
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: validation passed spec=$ABS_SPEC_PATH"

echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: exporting runtime OpenAPI for parity check output=$TMP_SPEC_PATH"
if docker compose ps --status running backend >/dev/null 2>&1; then
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: exporting OpenAPI via backend container"
  docker compose exec -T backend uv run python - <<'PY' > "$TMP_SPEC_PATH"
import json
from main import app

print(json.dumps(app.openapi(), indent=2, sort_keys=True))
PY
else
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: backend container unavailable; falling back to local uv export"
  (
    cd "$REPO_ROOT"
    uv run --project src/backend python scripts/export_openapi.py --output "$TMP_SPEC_PATH"
  )
fi

python - "$ABS_SPEC_PATH" "$SPEC_NORMALIZED" <<'PY'
import json
import pathlib
import sys

source = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
normalized_path = pathlib.Path(sys.argv[2])
normalized = json.dumps(json.loads(source), indent=2, sort_keys=True) + "\n"
normalized_path.write_text(normalized, encoding="utf-8")
PY
python - "$TMP_SPEC_PATH" "$TMP_SPEC_NORMALIZED" <<'PY'
import json
import pathlib
import sys

source = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
normalized_path = pathlib.Path(sys.argv[2])
normalized = json.dumps(json.loads(source), indent=2, sort_keys=True) + "\n"
normalized_path.write_text(normalized, encoding="utf-8")
PY

if ! cmp -s "$SPEC_NORMALIZED" "$TMP_SPEC_NORMALIZED"; then
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") ERROR validate_openapi: committed OpenAPI differs from runtime export path=$ABS_SPEC_PATH" >&2
  diff -u "$SPEC_NORMALIZED" "$TMP_SPEC_NORMALIZED" | sed -n '1,200p' >&2
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: fix by running ./scripts/update_sdk.sh and committing updated artifacts" >&2
  exit 1
fi
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: OpenAPI parity check passed spec=$ABS_SPEC_PATH"

echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: generating temporary sdk for drift check output=$TMP_SDK_DIR"
mkdir -p "$TMP_SDK_DIR"
cp -R "$ABS_SDK_DIR/." "$TMP_SDK_DIR"
docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "$REPO_ROOT:/local" \
  "$GENERATOR_IMAGE" generate \
  -i "/local/$SPEC_PATH" \
  -g "$GENERATOR_LANG" \
  -o "/local/$TMP_SDK_REL_PATH"

if ! diff -ruN \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  "$ABS_SDK_DIR" "$TMP_SDK_DIR" >/dev/null; then
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") ERROR validate_openapi: generated SDK is stale path=$ABS_SDK_DIR" >&2
  diff -ruN \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    "$ABS_SDK_DIR" "$TMP_SDK_DIR" | sed -n '1,200p' >&2
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: fix by running ./scripts/update_sdk.sh and committing updated artifacts" >&2
  exit 1
fi

echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: sdk drift check passed sdk=$ABS_SDK_DIR"
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO validate_openapi: all checks passed"
