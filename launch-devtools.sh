#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-9222}"
APP_URL="${1:-${APP_URL:-http://localhost:5173}}"
TARGET="${2:-${TARGET:-chrome}}"
ENDPOINT="http://127.0.0.1:${PORT}/json/list"
CHROME_PROFILE_DIR="${CHROME_PROFILE_DIR:-$HOME/.chrome-devtools-codex}"

wait_for_endpoint() {
  local attempts="${1:-15}"
  local delay_s="${2:-1}"
  local index
  for index in $(seq 1 "${attempts}"); do
    if curl -fsS "${ENDPOINT}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay_s}"
  done
  return 1
}

if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  if curl -fsS "${ENDPOINT}" >/dev/null 2>&1; then
    echo "Reusing active DevTools session on port ${PORT}."
    echo "App URL: ${APP_URL}"
    echo "DevTools endpoint: ${ENDPOINT}"
    echo
    echo "Current targets:"
    curl -fsS "${ENDPOINT}"
    exit 0
  fi
  echo "Port ${PORT} is already in use, but ${ENDPOINT} is not responding."
  echo "Stop the existing listener or choose a different PORT."
  exit 1
fi

launch_chrome() {
  mkdir -p "${CHROME_PROFILE_DIR}"

  if command -v open >/dev/null 2>&1 && [ -d "/Applications/Google Chrome Canary.app" ]; then
    open -na "Google Chrome Canary" --args \
      --remote-debugging-port="${PORT}" \
      --user-data-dir="${CHROME_PROFILE_DIR}" \
      --no-first-run \
      --no-default-browser-check \
      --new-window \
      "${APP_URL}" >/dev/null 2>&1
    return 0
  fi

  if command -v open >/dev/null 2>&1 && [ -d "/Applications/Google Chrome.app" ]; then
    open -na "Google Chrome" --args \
      --remote-debugging-port="${PORT}" \
      --user-data-dir="${CHROME_PROFILE_DIR}" \
      --no-first-run \
      --no-default-browser-check \
      --new-window \
      "${APP_URL}" >/dev/null 2>&1
    return 0
  fi

  if [ -x "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" ]; then
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" \
      --remote-debugging-port="${PORT}" \
      --user-data-dir="${CHROME_PROFILE_DIR}" \
      --no-first-run \
      --no-default-browser-check \
      --new-window \
      "${APP_URL}" >/dev/null 2>&1 &
    return 0
  fi

  if [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
      --remote-debugging-port="${PORT}" \
      --user-data-dir="${CHROME_PROFILE_DIR}" \
      --no-first-run \
      --no-default-browser-check \
      --new-window \
      "${APP_URL}" >/dev/null 2>&1 &
    return 0
  fi

  echo "Chrome binary not found. Install Chrome/Canary or set up Electron mode."
  exit 1
}

launch_electron() {
  local electron_bin="${ELECTRON_BIN:-}"
  local electron_app="${ELECTRON_APP:-}"

  if [ -z "$electron_bin" ] && command -v electron >/dev/null 2>&1; then
    electron_bin="$(command -v electron)"
  fi

  if [ -z "$electron_bin" ] || [ -z "$electron_app" ]; then
    echo "Electron mode requires ELECTRON_APP and (optionally) ELECTRON_BIN."
    echo "Example: ELECTRON_APP=./desktop ELECTRON_BIN=./node_modules/.bin/electron ./launch-devtools.sh http://localhost:5173 electron"
    exit 1
  fi

  "$electron_bin" --remote-debugging-port="${PORT}" "$electron_app" "$APP_URL" >/dev/null 2>&1 &
}

case "$TARGET" in
  chrome)
    launch_chrome
    ;;
  electron)
    launch_electron
    ;;
  *)
    echo "Unknown target '$TARGET'. Use 'chrome' or 'electron'."
    exit 1
    ;;
esac

sleep 1

echo "App URL: ${APP_URL}"
echo "DevTools endpoint: ${ENDPOINT}"

if ! wait_for_endpoint 20 1; then
  echo "Chrome launched, but the DevTools endpoint did not become ready."
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  echo
  echo "Current targets:"
  curl -fsS "$ENDPOINT" || true
fi
