# IMPLEMENTATION_PLAN

## Scope
- Scoped target: `all frontend work` only.
- Reviewed: `specs/*`, `src/frontend/*`, `src/frontend/src/lib/*`, and frontend-facing backend contracts in `src/backend/routers/*` + `src/backend/schemas/*`.
- Iteration mode: complete one highest-priority frontend item per run with tests.
- Note: `src/lib/*` does not exist in this repo; shared frontend library code is in `src/frontend/src/lib/*`.

## Completed Frontend Tasks (Merged to `main`)
- [x] Typed frontend API layer for load/run flows with deterministic error mapping.
- [x] Demo UI workflow closure for load -> run -> final-answer path (non-stream baseline).
- [x] Non-stream progress timeline/readout fallback rendering.
- [x] Request lifecycle protections: in-flight duplicate prevention and retry handling.
- [x] Cyberpunk visual-theme baseline implementation.
- [x] Deck layout/chrome framing for controls, progress, and result panels.

## Current Frontend Coverage (2026-03-04)
- [x] TypeScript React/Vite demo shell with load/run controls is present.
- [x] Frontend API client supports `POST /api/internal-data/load` and `POST /api/agents/run` with deterministic error handling.
- [x] Final answer and fallback progress history rendering exist for non-stream response payloads.
- [x] Frontend tests cover core load/run happy paths, failures, and in-flight duplicate prevention.
- [ ] Streaming heartbeat consumption in UI is missing (no EventSource/WebSocket client path).
- [x] Cyberpunk visual-theme baseline is implemented (dark/noir base, neon action/readout accents, panel/surface separation).
- [x] Deck chrome framing with explicit controls/progress/result panel separation is implemented.
- [ ] Readout polish, motion tuning, and accessibility hardening remain.

## Prioritized Frontend Tasks (Highest Priority Incomplete First)

- [ ] P0 - Add streaming heartbeat run experience (`specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`)
- Confirmed gap:
  - Frontend currently waits for final `POST /api/agents/run` response; it does not render incremental stream events.
  - Backend router still exposes `POST /api/agents/run` only; no stream endpoint is exposed yet (`src/backend/routers/agent.py`), so this task remains blocked on backend contract/endpoint availability.
- Verification requirements (outcome-based):
  - Test: when run starts, streamed sub-queries appear incrementally before completion.
  - Test: streamed progress updates are visible during the run (not only after completion).
  - Test: completion event updates UI to a terminal state and shows final answer.
  - Test: interrupted stream shows explicit degraded/error status and keeps UI responsive for retry.
  - Test: stream tests use deterministic mocked transport (no live network dependency).

- [x] P0 - Implement deck layout and chrome framing (`specs/layout-and-chrome.md`)
- Verification requirements (outcome-based):
  - Test: controls, progress/status, and result/readout are visually distinct sections.
  - Test: section boundaries/chrome are consistently visible.
  - Test: first-time user can identify where to act vs where to read without ambiguity.
  - Test: on narrow viewport widths, sections remain usable with preserved hierarchy.

- [ ] P1 - Upgrade status/progress/answer into consistent readouts (`specs/content-and-readouts.md`)
- Verification requirements (outcome-based):
  - Test: load/run success and error outcomes render in a coherent readout style.
  - Test: final answer remains dominant and easy to scan.
  - Test: progress and sub-query output remains ordered/scannable.
  - Test: user can visually distinguish asked query vs system progress vs final answer.

- [ ] P1 - Add motion and feedback treatment for action/state changes (`specs/motion-and-feedback.md`)
- Verification requirements (outcome-based):
  - Test: triggering load/run immediately shows visible processing feedback tied to the action.
  - Test: incoming progress/status changes are perceptible when they occur.
  - Test: decorative motion does not hide or hinder controls/content readability.
  - Test: transition behavior is consistent across major state changes.

- [ ] P1 - Accessibility hardening for themed UI (`specs/accessibility-within-aesthetic.md`)
- Verification requirements (outcome-based):
  - Test: all interactive controls have visible keyboard focus indication.
  - Test: keyboard-only user can complete load and run flows in logical focus order.
  - Test: with `prefers-reduced-motion: reduce`, non-essential motion is reduced while essential status remains visible.
  - Test: final answer and primary statuses remain readable at 200% zoom.
  - Audit: WCAG AA contrast is met for core text/labels, or exceptions are explicitly documented.

## Completed Frontend Work (Tracked)
- [x] Load/vectorize trigger + status reporting.
- [x] Query run trigger + final answer rendering.
- [x] API error mapping for HTTP/network/timeout/malformed payloads.
- [x] Duplicate request prevention while in-flight + same-session retry behavior.
- [x] Non-stream progress fallback rendering from `graph_state`, sub-queries, and validation data.
- [x] Cyberpunk visual-theme baseline (`specs/visual-theme.md`) with deterministic render coverage (`src/frontend/src/App.test.tsx`).

## Run Notes (2026-03-04)
- Completed this iteration: P0 deck layout and chrome framing.
- Streaming heartbeat remains blocked by backend contract availability (`/api/agents/run` is request/response only; no stream endpoint yet).
- Verified after fresh rebuild/start: `curl -sSf http://localhost:8000/api/health`, `docker compose exec backend uv run pytest`, `docker compose exec frontend npm run test`, `docker compose exec frontend npm run typecheck`, `docker compose exec frontend npm run build`.

## Frontend Quality Gates (Per Change)
- [x] Add at least one render/interaction test for each new frontend behavior.
- [x] Keep tests outcome-based (avoid implementation-detail assertions).
- [x] Keep frontend tests deterministic (mock transport/network).
- [x] Pass: `docker compose exec frontend npm run test`.
- [x] Pass: `docker compose exec frontend npm run typecheck`.
- [x] Pass: `docker compose exec frontend npm run build`.
