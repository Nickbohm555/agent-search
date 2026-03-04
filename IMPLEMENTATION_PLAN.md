# IMPLEMENTATION_PLAN

## Scope
- Frontend-only scoped planning for "all frontend work".
- Reviewed inputs: `specs/*`, `src/frontend/*`, `src/backend/schemas/*`, `src/backend/routers/*`, `src/backend/tests/api/*`, existing `IMPLEMENTATION_PLAN.md`.
- Planning mode only; no implementation in this run.

## Status Snapshot (2026-03-04)
- `src/frontend/src/App.tsx` and `src/frontend/src/App.test.tsx` remain scaffold-only.
- `src/lib/*` is not present (confirmed by file search); frontend shared utilities currently live in `src/frontend/src/utils/*`.
- Backend endpoints available now for frontend wiring:
- `POST /api/internal-data/load`
- `POST /api/agents/run`
- No streaming endpoint is currently exposed by backend routers; real-time heartbeat integration is blocked pending backend streaming delivery.

## Completed (Frontend Scope)
- [x] React + TypeScript + Vite scaffold exists.
- [x] Frontend test harness exists (`vitest` + Testing Library + jsdom).
- [x] API base URL helper exists in `src/frontend/src/utils/config.ts`.

## Remaining Work (Frontend Only, Highest Priority First)
- [ ] P0 - Replace scaffold page with end-to-end demo UI (`specs/demo-ui-typescript.md`)
- Build a TypeScript UI with:
- query input + run trigger,
- load/vectorize trigger + load status,
- sub-query/progress display region,
- final answer display region.
- Verification (outcome-based):
- Render test: all four required UI regions are present and usable.
- Interaction test: user triggers load and sees explicit loading then success outcome.
- Interaction test: failed load shows explicit error outcome.
- Interaction test: user runs a query and sees final answer output from API.

- [ ] P0 - Add typed frontend API client for run/load contracts (`specs/demo-ui-typescript.md`, `specs/data-loading-vectorization.md`)
- Implement shared request/response types and API calls for `/api/internal-data/load` and `/api/agents/run`.
- Keep error handling deterministic for user-visible outcomes.
- Verification (outcome-based):
- Unit test: load API success exposes observable load outcome values (`documents_loaded`, `chunks_created`).
- Unit test: run API success exposes sub-queries, graph/progress payload, and final answer output for UI rendering.
- Unit test: non-2xx responses map to stable user-displayable error outcomes.

- [ ] P0 - Implement progress/sub-query timeline model with non-stream fallback (`specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`)
- Add a frontend timeline/event model that can consume progress events and render ordered status updates.
- Until backend stream exists, project progress from `/api/agents/run` response (`sub_queries`, `tool_assignments`, `validation_results`, `graph_state.timeline`).
- Verification (outcome-based):
- Unit test: fallback mapping produces ordered sub-query/progress timeline entries.
- Unit test: partial or missing graph state still yields a stable, non-crashing progress view.
- Interaction test: run completion shows completed progress state and final answer in UI.

- [ ] P1 - Add request lifecycle guardrails and retry UX (`specs/demo-ui-typescript.md`)
- Prevent duplicate run/load submissions while requests are active.
- Allow retry after failed load/run without full page refresh.
- Verification (outcome-based):
- Interaction test: run/load controls are disabled while request is active and re-enabled after completion.
- Interaction test: rapid repeat click produces one active request, not duplicate concurrent submissions.
- Interaction test: after an error, retry succeeds and UI reflects recovered success state.

- [ ] P1 - Consolidate frontend shared transforms in `src/frontend/src/utils/*` (repo convention)
- Keep API response shaping and progress mapping in shared utilities instead of UI components.
- Verification (outcome-based):
- Unit test: API payload-to-UI model mapping is deterministic for sub-queries, progress states, and final answer blocks.
- Unit test: empty/partial payloads return valid empty/partial UI states.

- [ ] P2 - Apply simple, sleek, responsive styling pass (`specs/demo-ui-typescript.md`)
- Deliver polished, minimal styling for desktop and mobile while keeping progress/success/error states distinct.
- Verification (outcome-based):
- Render test: required controls and output/progress regions remain visible and usable at narrow viewport width.
- Manual QA: load, progress, error, and final-answer states are visually distinct and legible.

- [ ] P2 - Integrate true streaming heartbeat UI once backend endpoint exists (`specs/streaming-agent-heartbeat.md`)
- Connect frontend timeline to backend stream transport (SSE/WebSocket) after backend exposes the streaming route.
- Keep existing non-stream fallback path for environments where stream is unavailable.
- Verification (outcome-based):
- Integration test: during a run, UI receives and renders streamed sub-queries in near real time.
- Integration test: UI reflects live step progress from stream updates through completion/final answer.
- Reliability test: typical run does not lose ordered progress updates visible to user.

## Dependencies / Blockers
- Frontend real-time heartbeat work depends on backend streaming endpoint implementation (not present in current routers).

## Frontend Quality Gates
- [ ] Each new UI behavior ships with at least one render or interaction test.
- [ ] Tests remain deterministic with explicit API/stream mocking.
- [ ] Before implementation commit, pass:
- `docker compose exec frontend npm run test`
- `docker compose exec frontend npm run typecheck`
- `docker compose exec frontend npm run build`
