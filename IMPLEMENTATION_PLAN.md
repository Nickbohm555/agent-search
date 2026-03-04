# IMPLEMENTATION_PLAN

## Scope
- Frontend-only scoped planning for: "all frontend work".
- Sources reviewed: `specs/*`, `src/frontend/*`, `src/backend/routers/*`, `src/backend/schemas/*`, `src/backend/services/agent_service.py`, existing `IMPLEMENTATION_PLAN.md`.
- Planning mode only; no implementation in this run.

## Current Status (2026-03-04)
- [x] Frontend scaffold exists in TypeScript/React/Vite (`src/frontend/src/App.tsx`, `src/frontend/src/main.tsx`).
- [x] Frontend test harness exists (Vitest + Testing Library) (`src/frontend/src/App.test.tsx`, `src/frontend/src/test/setup.ts`).
- [x] Frontend env-based API base URL helper exists (`src/frontend/src/utils/config.ts`).
- [x] Confirmed `src/lib/*` does not exist in this repo; shared frontend utilities currently live under `src/frontend/src/*`.
- [ ] Demo UI behavior from `specs/demo-ui-typescript.md` is not implemented.
- [ ] Frontend API typing/error normalization for `/api/internal-data/load` and `/api/agents/run` is not implemented.
- [ ] Streaming heartbeat UI integration is not implemented.

## Frontend Tasks Remaining (Priority Order)

- [ ] P0 - Implement a typed frontend API client for load/run flows
- Spec alignment:
  - `specs/demo-ui-typescript.md` (load action + run action + final answer visibility).
  - `specs/data-loading-vectorization.md` (load outcome must be observable).
- Confirmed contracts to support:
  - `POST /api/internal-data/load` => `{ status, source_type, documents_loaded, chunks_created }`.
  - `POST /api/agents/run` => `{ output, sub_queries, tool_assignments, retrieval_results, validation_results, web_tool_runs, graph_state? }`.
- Verification requirements (outcome-focused):
  - Unit test: successful load call returns UI-consumable counts (`documents_loaded`, `chunks_created`).
  - Unit test: successful run call returns UI-consumable answer/progress fields (`output`, `sub_queries`, `tool_assignments`, `validation_results`, optional `graph_state`).
  - Unit test: network failure and non-2xx response both produce deterministic, user-safe error outcomes.
  - Unit test: malformed payloads produce deterministic fallback error outcomes (no uncaught render/runtime crash).

- [ ] P0 - Replace scaffold screen with demo UI flow (load/vectorize + run query + final answer)
- Spec alignment:
  - `specs/demo-ui-typescript.md` acceptance criteria require load trigger, query input/run action, streamed progress intent, and final answer display.
- Deliverables:
  - Renderable controls for load trigger and query submission.
  - Visible request lifecycle states: `idle`, `loading/running`, `success/completed`, `error`.
  - Final answer region sourced from run result `output`.
- Verification requirements (outcome-focused):
  - Render test: load control, query input, run trigger, progress/status area, and final-answer area are present on first render.
  - Interaction test: load success state is clearly shown with returned counts.
  - Interaction test: load failure state is clearly shown with actionable error text.
  - Interaction test: running a query renders the returned final answer text.

- [ ] P0 - Implement progress timeline UI using existing run payload as non-stream heartbeat fallback
- Spec alignment:
  - `specs/demo-ui-typescript.md` + `specs/streaming-agent-heartbeat.md` require visible sub-query/progress updates; backend stream route is not available yet.
- Deliverables:
  - Show ordered progress from run payload (`sub_queries`, `tool_assignments`, `validation_results`, and `graph_state.timeline` when present).
  - Display per-subquery status through completion next to final answer.
  - Gracefully handle missing optional graph data.
- Verification requirements (outcome-focused):
  - Unit/render test: progress order reflects decomposition/tool-selection/retrieval/validation/synthesis completion when timeline is present.
  - Unit/render test: when `graph_state` is absent, UI still shows available subquery/validation progress and final answer.
  - Interaction test: single run shows both progress history and final answer in the same completed view.

- [ ] P1 - Add request lifecycle safeguards (in-flight lockout + retry in-session)
- Spec alignment:
  - Supports reliable, clear UX outcomes required by `specs/demo-ui-typescript.md`.
- Deliverables:
  - Disable only the relevant control while its request is active.
  - Permit retry after failure without page reload.
  - Prevent duplicate concurrent calls from rapid repeat clicks/submits.
- Verification requirements (outcome-focused):
  - Interaction test: load control disables while load is in flight and re-enables afterward.
  - Interaction test: run control disables while run is in flight and re-enables afterward.
  - Interaction test: rapid repeated actions do not create duplicate concurrent calls.
  - Interaction test: a failed call can be retried successfully in the same session.

- [ ] P1 - Integrate streaming heartbeat when backend stream contract is available
- Spec alignment:
  - `specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`.
- Blocker (confirmed):
  - No streaming endpoint/protocol is currently exposed in backend routers (`src/backend/routers/*` has no SSE/WebSocket stream route).
- Deliverables (once unblocked):
  - Stream client integration (SSE/WebSocket per backend contract).
  - Merge streamed events into the same progress UI used by non-stream fallback.
- Verification requirements (outcome-focused):
  - Integration test: during a run, sub-queries appear near real time from stream events.
  - Integration test: streamed progress reaches completion and final answer is displayed.
  - Resilience test: stream interruption/unavailability falls back to non-stream result handling without UI failure.

- [ ] P2 - Simple/sleek responsive polish for demo presentation
- Spec alignment:
  - UX clause in `specs/demo-ui-typescript.md` (simple and sleek TypeScript UI).
- Deliverables:
  - Improve visual hierarchy for statuses, progress, and final answer readability.
  - Ensure controls and outputs remain usable at narrow mobile widths.
- Verification requirements (outcome-focused):
  - Render test: core controls/status/final answer remain visible and usable at narrow viewport widths.
  - Render/interaction test: loading/success/error/completed states are visually distinguishable.
  - Manual QA check: demo flow remains readable and coherent on desktop and mobile.

## Out of Scope For This Frontend Plan
- Backend pipeline implementation details (decomposition, retrieval, validation, synthesis internals).
- Backend streaming service implementation itself (frontend integration only once available).
- MCP exposure work.

## Frontend Quality Gates
- [ ] For each new UI behavior, add at least one render/interaction test in the same change.
- [ ] Keep tests deterministic with explicit mocks/stubs (no hidden network dependencies).
- [ ] Before frontend completion/commit, pass:
  - `docker compose exec frontend npm run test`
  - `docker compose exec frontend npm run typecheck`
  - `docker compose exec frontend npm run build`
