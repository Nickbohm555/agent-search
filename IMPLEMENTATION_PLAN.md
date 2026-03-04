# IMPLEMENTATION_PLAN

## Scope
- Frontend-only scoped planning for "all frontend work".
- Inputs reviewed: `specs/*`, existing `IMPLEMENTATION_PLAN.md`, `src/frontend/*`, `src/backend/routers/*`, `src/backend/schemas/*`, `src/backend/agents/langgraph_agent.py`.
- Planning mode only; no implementation in this run.

## Current State (2026-03-04)
- `src/frontend/src/App.tsx` is scaffold-only and does not implement load/run/progress UX.
- Frontend tests currently only verify scaffold heading.
- `src/lib/*` is not present in this repository; shared frontend utilities currently live in `src/frontend/src/utils/*`.
- Backend contracts available to frontend today:
  - `POST /api/internal-data/load`
  - `POST /api/agents/run`
- Missing for true frontend heartbeat requirements:
  - No backend streaming endpoint exposed in `src/backend/routers/*`.
  - No frontend streaming client (`EventSource`/WebSocket) in `src/frontend/*`.

## Completed (Frontend Scope)
- [x] React + TypeScript + Vite scaffold exists.
- [x] Vitest + Testing Library test harness exists.
- [x] API base URL helper exists in `src/frontend/src/utils/config.ts`.

## Remaining Frontend Work (Highest Priority First)
- [ ] P0 - Implement demo UI workflow for load/vectorize + run + final answer (`specs/demo-ui-typescript.md`)
- Outcome targets:
  - User can trigger load from UI and sees clear success/error outcome.
  - User can submit a query and sees final synthesized answer.
  - UI exposes distinct sections for load status, query/run, progress, and final answer.
- Verification requirements:
  - Render test: required regions are visible on initial render.
  - Interaction test: successful load shows explicit success state including returned counts.
  - Interaction test: failed load shows explicit error state.
  - Interaction test: successful run displays returned final answer text.

- [ ] P0 - Add typed frontend API client layer for `/api/internal-data/load` and `/api/agents/run` (`specs/demo-ui-typescript.md`, `specs/data-loading-vectorization.md`)
- Outcome targets:
  - Frontend has centralized request/response types and wrappers in `src/frontend/src/utils/*`.
  - UI receives normalized success and error outcomes without per-component parsing logic.
- Verification requirements:
  - Unit test: load success exposes `documents_loaded` and `chunks_created` for UI.
  - Unit test: run success exposes sub-queries, progress-capable graph data, and final answer.
  - Unit test: non-2xx and invalid payloads map to deterministic user-facing error objects.

- [ ] P0 - Build non-stream progress view from run response data as current heartbeat fallback (`specs/demo-ui-typescript.md`, `specs/query-decomposition.md`, `specs/tool-selection-per-subquery.md`, `specs/retrieval-validation.md`)
- Outcome targets:
  - UI presents ordered progress history using `sub_queries`, `tool_assignments`, `validation_results`, and `graph_state.timeline`.
  - Sub-query and validation status are visible to users in a stable timeline/list.
- Verification requirements:
  - Unit test: response-to-progress mapping preserves meaningful ordering.
  - Unit test: partial/missing graph fields still render stable output (no crash/undefined text).
  - Interaction test: completed run shows both progress history and final answer in one flow.

- [ ] P1 - Add request lifecycle controls and retry behavior for load/run (`specs/demo-ui-typescript.md`)
- Outcome targets:
  - Duplicate submissions are prevented while request is in-flight.
  - User can retry after error without reload.
- Verification requirements:
  - Interaction test: controls disable only while active request is pending and re-enable on completion.
  - Interaction test: rapid repeat submit does not create duplicate concurrent requests.
  - Interaction test: failed request can be retried to a successful outcome.

- [ ] P1 - Implement streaming heartbeat UI integration once backend endpoint + event contract exist (`specs/streaming-agent-heartbeat.md`, `specs/demo-ui-typescript.md`)
- Outcome targets:
  - Frontend consumes real-time stream updates for sub-queries/progress/final answer.
  - Non-stream fallback remains available when stream is unavailable.
- Verification requirements:
  - Integration test: query run displays sub-queries from stream in near real time.
  - Integration test: progress continues through completion and final answer event.
  - Reliability test: user-visible event ordering remains stable during typical runs.

- [ ] P2 - UI polish for simple/sleek responsive UX (`specs/demo-ui-typescript.md`)
- Outcome targets:
  - UI state transitions (idle/loading/success/error/running/completed) are visually clear.
  - Layout remains usable on mobile and desktop.
- Verification requirements:
  - Render test: core controls and result/progress regions remain present and operable at narrow viewport widths.
  - Manual QA: users can distinguish all major lifecycle states without ambiguity.

## Blockers / Dependencies
- True streaming heartbeat acceptance is blocked until backend streaming endpoint and message contract are implemented/exposed.

## Frontend Quality Gates
- [ ] Every new UI behavior includes at least one render or interaction test.
- [ ] Tests remain deterministic with explicit API/stream mocking.
- [ ] Before frontend implementation commits, pass:
  - `docker compose exec frontend npm run test`
  - `docker compose exec frontend npm run typecheck`
  - `docker compose exec frontend npm run build`
