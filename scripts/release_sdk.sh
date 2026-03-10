#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SDK_DIR="${SDK_DIR:-$REPO_ROOT/sdk/core}"
DIST_DIR="$SDK_DIR/dist"
PUBLISH="${PUBLISH:-0}"
RELEASE_TAG="${RELEASE_TAG:-}"

log() {
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") INFO release_sdk: $*"
}

error() {
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") ERROR release_sdk: $*" >&2
}

run_build() {
  if command -v uv >/dev/null 2>&1; then
    (cd "$SDK_DIR" && uvx --from build python -m build .)
  else
    (cd "$SDK_DIR" && python3 -m build)
  fi
}

run_twine_check() {
  if command -v uv >/dev/null 2>&1; then
    uvx twine check "$DIST_DIR"/*
  else
    python3 -m twine check "$DIST_DIR"/*
  fi
}

run_twine_upload() {
  if command -v uv >/dev/null 2>&1; then
    TWINE_USERNAME="__token__" uvx twine upload "$DIST_DIR"/*
  else
    TWINE_USERNAME="__token__" python3 -m twine upload "$DIST_DIR"/*
  fi
}

verify_wheel_contents() {
  local wheel_path
  wheel_path="$(ls "$DIST_DIR"/agent_search_core-*.whl | head -n 1)"
  if [[ -z "$wheel_path" ]]; then
    error "wheel not found under $DIST_DIR"
    exit 1
  fi

  python3 - <<'PY' "$wheel_path"
import sys
import zipfile

wheel_path = sys.argv[1]
with zipfile.ZipFile(wheel_path) as zf:
    names = zf.namelist()

if not any(name.startswith("agent_search/") for name in names):
    raise SystemExit(f"wheel missing agent_search package: {wheel_path}")
PY

  log "wheel content check passed wheel=$wheel_path"
}

if [[ ! -f "$SDK_DIR/pyproject.toml" ]]; then
  error "sdk pyproject not found path=$SDK_DIR/pyproject.toml"
  exit 1
fi

PACKAGE_VERSION="$(sed -nE 's/^version = \"([^\"]+)\"/\1/p' "$SDK_DIR/pyproject.toml" | head -n 1)"
if [[ -z "$PACKAGE_VERSION" ]]; then
  error "unable to determine project version from $SDK_DIR/pyproject.toml"
  exit 1
fi

EXPECTED_TAG="agent-search-core-v${PACKAGE_VERSION}"
if [[ -n "$RELEASE_TAG" && "$RELEASE_TAG" != "$EXPECTED_TAG" ]]; then
  error "release tag mismatch expected=$EXPECTED_TAG actual=$RELEASE_TAG"
  exit 1
fi

log "starting sdk_dir=$SDK_DIR version=$PACKAGE_VERSION publish=$PUBLISH"
log "cleaning dist directory path=$DIST_DIR"
rm -rf "$DIST_DIR"

log "building sdist and wheel"
run_build

log "verifying wheel contents"
verify_wheel_contents

log "running twine check"
run_twine_check

if [[ "$PUBLISH" == "1" ]]; then
  if [[ -z "${TWINE_API_TOKEN:-}" ]]; then
    error "PUBLISH=1 requires TWINE_API_TOKEN"
    exit 1
  fi

  log "uploading distributions to PyPI"
  run_twine_upload
  log "publish complete version=$PACKAGE_VERSION"
else
  log "dry run complete; skipping upload (set PUBLISH=1 to publish)"
fi
