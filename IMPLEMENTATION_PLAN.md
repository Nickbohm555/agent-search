# IMPLEMENTATION_PLAN

## Scope
- Frontend-only scoped planning for "all frontend work".
- Inputs reviewed: `specs/*`, existing `IMPLEMENTATION_PLAN.md`, `src/frontend/*`, `src/backend/routers/*`, `src/backend/schemas/*`, `src/backend/agents/langgraph_agent.py`.
- Planning mode only; no implementation in this run.

## Current State (2026-03-04)
- `src/frontend/src/App.tsx` and `src/frontend/src/App.test.tsx` are scaffold-only.
- `src/lib/*` does not exist in this repository (confirmed by file search).
- Frontend shared utility location is `src/frontend/src/utils/*`.
- Backend contracts already available for frontend:
- `POST /api/internal-data/load` returns load outcome (`status`, `documents_loaded`, `chunks_created`).
- `POST /api/agents/run` returns run outcome (`sub_queries`, `tool_assignments`, `retrieval_results`, `validation_results`, `graph_state.timeline`, `output`).
- No backend streaming endpoint is currently exposed by routers; true real-time heartbeat UI is blocked pending backend delivery.

## Completed (Frontend Scope)
- [x] React + TypeScript + Vite scaffold is present.
- [x] Frontend test harness is configured (`vitest`, Testing Library, jsdom).
- [x] API base URL helper exists in `src/frontend/src/utils/config.ts`.

## Remaining Frontend Work (Priority Ordered)
- [ ] P0 - Build the demo UI surface for load + run + progress + answer (`specs/demo-ui-typescript.md`)
- Implement a TypeScript UI with:
- query input and run action,
- load/vectorize action and visible status,
- sub-query/progress panel,
- final answer panel.
- Verification requirements (outcome-based):
- Render test: all required regions (load, query/run, progress/sub-queries, final answer) are visible on initial render.
- Interaction test: triggering load shows explicit lifecycle states (idle/loading/success) with returned counts.
- Interaction test: load failure shows explicit error state that the user can see.
- Interaction test: triggering run with a valid query renders returned final answer text.

- [ ] P0 - Add typed frontend API module for `/api/internal-data/load` and `/api/agents/run` (`specs/demo-ui-typescript.md`, `specs/data-loading-vectorization.md`)
- Centralize request/response types and fetch wrappers in shared frontend utilities.
- Normalize API failures into deterministic user-displayable error outcomes.
- Verification requirements (outcome-based):
- Unit test: load API success returns observable load outcome fields (`documents_loaded`, `chunks_created`).
- Unit test: run API success returns UI-consumable outputs (sub-queries, progress-capable graph state, final answer).
- Unit test: non-2xx or malformed payloads produce stable error outcomes.

- [ ] P0 - Implement progress timeline rendering from available run response (non-stream fallback) (`specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`)
- Map `sub_queries`, `tool_assignments`, `validation_results`, and `graph_state.timeline` into ordered progress events for display.
- Keep this as the default progress source until backend streaming endpoint exists.
- Verification requirements (outcome-based):
- Unit test: response-to-timeline mapping preserves meaningful order of steps/sub-queries.
- Unit test: missing or partial graph fields still render a stable progress view (no crash, no undefined UI text).
- Interaction test: completed run displays sub-query/progress history plus final answer in one flow.

- [ ] P1 - Add request lifecycle guardrails and retry behavior for load/run (`specs/demo-ui-typescript.md`)
- Prevent duplicate submissions while each request is active.
- Support retry after error without full page reload.
- Verification requirements (outcome-based):
- Interaction test: load/run controls are disabled only during active request and re-enabled afterward.
- Interaction test: rapid repeat submit does not create duplicate concurrent in-flight requests.
- Interaction test: after a failed request, retry can succeed and UI reflects recovered success state.

- [ ] P1 - Keep response transforms in shared frontend utilities (`src/frontend/src/utils/*`) instead of component internals
- Consolidate mapping/formatting logic so UI components stay declarative and behavior is deterministic.
- Verification requirements (outcome-based):
- Unit test: transform helpers produce consistent UI models for normal, empty, and partial responses.
- Unit test: tool assignments and validation statuses are surfaced in display-ready form without component-specific assumptions.

- [ ] P2 - Apply simple, sleek, responsive styling consistent with the demo spec (`specs/demo-ui-typescript.md`)
- Keep state visibility clear for idle/loading/success/error/progress/final-answer.
- Ensure layout remains usable on desktop and mobile widths.
- Verification requirements (outcome-based):
- Render test: core controls and result/progress regions remain present and operable at narrow viewport widths.
- Manual QA: users can visually distinguish loading, success, error, and completion states.

- [ ] P2 - Integrate true streaming heartbeat once backend stream endpoint exists (`specs/streaming-agent-heartbeat.md`)
- Connect frontend progress UI to streaming transport (SSE/WebSocket) when backend exposes it.
- Retain non-stream fallback for environments where stream is unavailable.
- Verification requirements (outcome-based):
- Integration test: running a query yields near real-time sub-query updates on the UI.
- Integration test: UI progress updates continue through completion and final answer.
- Reliability test: a typical run preserves user-visible ordering of streamed progress updates.

## Dependency / Blocker Notes
- True streaming heartbeat UI is blocked by missing backend streaming endpoint and contract in current routers.

## Frontend Quality Gates
- [ ] Every new UI behavior includes at least one render or interaction test.
- [ ] Tests are deterministic with explicit API/stream mocking (no hidden network dependency).
- [ ] Before commit for frontend implementation work, pass:
- `docker compose exec frontend npm run test`
- `docker compose exec frontend npm run typecheck`
- `docker compose exec frontend npm run build`
