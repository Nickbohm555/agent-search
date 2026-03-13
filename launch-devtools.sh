#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-9222}"
APP_URL="${1:-${APP_URL:-http://localhost:5173}}"
HOST="${HOST:-127.0.0.1}"
PROFILE_DIR="${CHROME_PROFILE_DIR:-$HOME/.chrome-devtools-codex}"
LIST_ENDPOINT="http://${HOST}:${PORT}/json/list"
NEW_ENDPOINT="http://${HOST}:${PORT}/json/new"
CHROME_BIN="${CHROME_BIN:-}"

wait_for_endpoint() {
  local attempts="${1:-20}"
  local delay_s="${2:-1}"
  local index
  for index in $(seq 1 "${attempts}"); do
    if curl -fsS "${LIST_ENDPOINT}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay_s}"
  done
  return 1
}

endpoint_is_live() {
  curl -fsS "${LIST_ENDPOINT}" >/dev/null 2>&1
}

port_is_busy() {
  command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1
}

resolve_chrome_bin() {
  if [ -n "${CHROME_BIN}" ] && [ -x "${CHROME_BIN}" ]; then
    printf '%s\n' "${CHROME_BIN}"
    return 0
  fi

  if [ -x "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" ]; then
    printf '%s\n' "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"
    return 0
  fi

  if [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
    printf '%s\n' "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    return 0
  fi

  if command -v google-chrome >/dev/null 2>&1; then
    command -v google-chrome
    return 0
  fi

  if command -v chromium >/dev/null 2>&1; then
    command -v chromium
    return 0
  fi

  return 1
}

pick_target() {
  python3 - "${APP_URL}" <<'PY'
import json
import sys
import urllib.request

app_url = sys.argv[1]
pages = json.load(urllib.request.urlopen("http://127.0.0.1:" + __import__("os").environ.get("PORT", "9222") + "/json/list"))

preferred = None
fallback = None
for page in pages:
    if fallback is None and page.get("type") == "page":
        fallback = page
    if page.get("type") == "page" and str(page.get("url", "")).startswith(app_url):
        preferred = page
        break

chosen = preferred or fallback or {}
print(json.dumps(chosen))
PY
}

print_targets() {
  python3 - <<'PY'
import json
import urllib.request

pages = json.load(urllib.request.urlopen("http://127.0.0.1:" + __import__("os").environ.get("PORT", "9222") + "/json/list"))
for page in pages:
    title = page.get("title", "")
    url = page.get("url", "")
    target_id = page.get("id", "")
    ws = page.get("webSocketDebuggerUrl", "")
    print(f"- id={target_id} title={title!r} url={url} ws={ws}")
PY
}

open_target_for_app() {
  local encoded_url
  encoded_url="$(python3 - "${APP_URL}" <<'PY'
import sys
import urllib.parse
print(urllib.parse.quote(sys.argv[1], safe=":/?&=%"))
PY
)"
  curl -fsS "${NEW_ENDPOINT}?${encoded_url}" >/dev/null 2>&1 || true
}

reuse_or_fail_for_busy_port() {
  if ! port_is_busy; then
    return 1
  fi

  if ! endpoint_is_live; then
    echo "Port ${PORT} is already in use, but ${LIST_ENDPOINT} is not responding."
    echo "Stop the stale listener on ${PORT} or rerun with a different PORT."
    exit 1
  fi

  open_target_for_app
  echo "Reusing active local Chrome DevTools session on port ${PORT}."
  echo "App URL: ${APP_URL}"
  echo "DevTools endpoint: ${LIST_ENDPOINT}"
  echo
  echo "Targets:"
  print_targets
  echo
  echo "Preferred target:"
  pick_target
  exit 0
}

launch_chrome() {
  local chrome_bin
  chrome_bin="$(resolve_chrome_bin)" || {
    echo "Chrome binary not found. Install Chrome/Canary or set CHROME_BIN."
    exit 1
  }

  mkdir -p "${PROFILE_DIR}"

  if command -v open >/dev/null 2>&1 && [ "${chrome_bin}" = "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" ]; then
    open -na "Google Chrome Canary" --args \
      --remote-debugging-port="${PORT}" \
      --remote-allow-origins='*' \
      --user-data-dir="${PROFILE_DIR}" \
      --no-first-run \
      --no-default-browser-check \
      --new-window \
      "${APP_URL}" >/dev/null 2>&1
    return 0
  fi

  if command -v open >/dev/null 2>&1 && [ "${chrome_bin}" = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
    open -na "Google Chrome" --args \
      --remote-debugging-port="${PORT}" \
      --remote-allow-origins='*' \
      --user-data-dir="${PROFILE_DIR}" \
      --no-first-run \
      --no-default-browser-check \
      --new-window \
      "${APP_URL}" >/dev/null 2>&1
    return 0
  fi

  "${chrome_bin}" \
    --remote-debugging-port="${PORT}" \
    --remote-allow-origins='*' \
    --user-data-dir="${PROFILE_DIR}" \
    --no-first-run \
    --no-default-browser-check \
    --new-window \
    "${APP_URL}" >/dev/null 2>&1 &
}

reuse_or_fail_for_busy_port || true
launch_chrome

if ! wait_for_endpoint 20 1; then
  echo "Chrome launched, but the DevTools endpoint did not become ready at ${LIST_ENDPOINT}."
  exit 1
fi

open_target_for_app

echo "Started local Chrome DevTools session."
echo "App URL: ${APP_URL}"
echo "DevTools endpoint: ${LIST_ENDPOINT}"
echo
echo "Targets:"
print_targets
echo
echo "Preferred target:"
pick_target
