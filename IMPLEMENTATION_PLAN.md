# IMPLEMENTATION_PLAN

## Scope
- Frontend-only scoped planning for: "all frontend work".
- Sources reviewed this run: `specs/*`, `src/frontend/*`, `src/backend/routers/*`, `src/backend/schemas/*`, `src/backend/services/agent_service.py`, `IMPLEMENTATION_PLAN.md`.
- Planning mode only; no implementation in this run.

## Current Status (2026-03-04)
- [x] Frontend scaffold exists in TypeScript/React/Vite (`src/frontend/src/App.tsx`, `src/frontend/src/main.tsx`).
- [x] Frontend test harness exists (Vitest + Testing Library) (`src/frontend/src/App.test.tsx`, `src/frontend/src/test/setup.ts`).
- [x] Frontend API base URL helper exists (`src/frontend/src/utils/config.ts`).
- [x] Confirmed `src/lib/*` is currently missing; no shared cross-app library exists yet.
- [ ] Demo UI workflow from `specs/demo-ui-typescript.md` is not implemented.
- [ ] Streaming heartbeat UI integration from `specs/streaming-agent-heartbeat.md` is not implemented.

## Frontend Tasks Remaining (Highest Priority First)

- [ ] P0 - Build a typed frontend API layer for demo flows (load + run)
- Why: UI work depends on stable contract handling for `/api/internal-data/load` and `/api/agents/run`.
- Spec alignment:
  - `specs/demo-ui-typescript.md` (load trigger, run trigger, final answer display)
  - `specs/data-loading-vectorization.md` (observable load outcome)
- Contract outcomes to support:
  - `POST /api/internal-data/load` returns `status`, `source_type`, `documents_loaded`, `chunks_created`.
  - `POST /api/agents/run` returns `output`, `sub_queries`, `tool_assignments`, `retrieval_results`, `validation_results`, `web_tool_runs`, optional `graph_state`.
- Verification requirements (WHAT must work):
  - Unit test: load success returns usable counts for UI status (`documents_loaded`, `chunks_created`).
  - Unit test: run success returns usable final answer/progress payload (`output`, `sub_queries`, assignments, validation, optional graph state).
  - Unit test: non-2xx API response yields deterministic user-safe error object.
  - Unit test: network failure/timeout yields deterministic retryable error object.
  - Unit test: malformed payload from backend is rejected into deterministic fallback error (no uncaught runtime crash).

- [ ] P0 - Implement demo UI workflow (load/vectorize + query run + final answer)
- Why: This is the core acceptance surface in `demo-ui-typescript`.
- Spec alignment:
  - `specs/demo-ui-typescript.md`
- Required behavior outcomes:
  - User can trigger load and see clear `loading`, `success`, or `error` state.
  - User can enter a query and start a run.
  - User can see final synthesized answer when run completes.
- Verification requirements (WHAT must work):
  - Render test: load control, load status region, query input, run control, progress region, final-answer region are present on initial render.
  - Interaction test: successful load visibly reports success outcome with counts.
  - Interaction test: failed load visibly reports error outcome.
  - Interaction test: successful run renders returned final answer text.
  - Interaction test: failed run visibly reports error outcome while preserving user-entered query for retry.

- [ ] P0 - Render agent progress timeline from run response as pre-stream heartbeat fallback
- Why: No backend stream route exists yet; UI still must show sub-queries/progress for demo utility.
- Spec alignment:
  - `specs/demo-ui-typescript.md` (progress visibility)
  - `specs/streaming-agent-heartbeat.md` (heartbeat intent, pending stream backend)
- Confirmed blocker:
  - No SSE/WebSocket/stream route exists in `src/backend/routers/*`.
- Required behavior outcomes:
  - Ordered progression is visible from run payload (`sub_queries`, `tool_assignments`, `validation_results`, optional `graph_state.timeline`).
  - Final answer and progress history coexist in completed state.
  - Missing `graph_state` does not break progress display.
- Verification requirements (WHAT must work):
  - Render test: when `graph_state.timeline` exists, UI shows ordered step progression through synthesis completion.
  - Render test: when `graph_state` is missing, UI still shows sub-query and validation outcomes.
  - Interaction test: completed run view includes both progress history and final answer.
  - Edge-case test: empty arrays for optional sections render stable "no data" states without crash.

- [ ] P1 - Add request lifecycle protections (in-flight lockout + same-session retry)
- Why: Required for reliable UX during demo interactions.
- Spec alignment:
  - Supports outcome clarity expectations in `specs/demo-ui-typescript.md`.
- Required behavior outcomes:
  - Active request disables only related action control.
  - Duplicate concurrent calls from rapid clicks/submits are prevented.
  - Retry is possible after failure without reload.
- Verification requirements (WHAT must work):
  - Interaction test: load control disables only during load request and re-enables afterward.
  - Interaction test: run control disables only during run request and re-enables afterward.
  - Interaction test: rapid repeated click/submit triggers one in-flight request.
  - Interaction test: failure followed by retry can complete successfully in same session.

- [ ] P1 - Integrate real streaming heartbeat once backend stream contract exists
- Why: Streaming is explicit acceptance criteria, but currently blocked by missing backend route/protocol.
- Spec alignment:
  - `specs/demo-ui-typescript.md`
  - `specs/streaming-agent-heartbeat.md`
- Required behavior outcomes (post-unblock):
  - Sub-queries and progress updates appear near real time during a run.
  - Streamed completion state includes final answer.
  - UI remains usable if stream disconnects/fails and can fall back to non-stream completion handling.
- Verification requirements (WHAT must work):
  - Integration test: stream events render sub-queries/progress incrementally while run is active.
  - Integration test: completion event (or final payload) renders final answer and done state.
  - Resilience test: stream interruption shows clear degraded state and fallback path still yields stable completed/error UI.
  - Timeliness test: once an event is emitted by test stream source, UI reflects it within deterministic near-real-time threshold (project-defined threshold in test).

- [ ] P1 - Establish shared frontend standard library structure (`src/lib/*`) and consume it from demo UI
- Why: Repo guidance treats `src/lib/*` as shared utility/component library, and it does not exist yet.
- Scope note:
  - Keep this focused to frontend-shared API/util/component primitives directly used by demo flow.
- Verification requirements (WHAT must work):
  - Unit test: shared helpers/components used by main UI behave consistently across success/error states.
  - Integration test: App uses shared library exports without behavior regression in load/run flow.
  - Build/typecheck outcome: shared imports resolve cleanly in frontend build.

- [ ] P2 - Apply simple/sleek responsive polish for demo readability
- Why: Acceptance criteria requires simple/sleek TypeScript UI.
- Spec alignment:
  - `specs/demo-ui-typescript.md`
- Required behavior outcomes:
  - Clear visual distinction across `idle`, `loading`, `success`, `error`, and `completed`.
  - Usable layout at narrow mobile widths and desktop.
- Verification requirements (WHAT must work):
  - Render test: core controls, progress, and final answer remain visible/usable at narrow viewport width.
  - Interaction/render test: state transitions remain visually distinguishable.
  - Manual QA check: end-to-end demo flow is readable and coherent on desktop and mobile.

## Out Of Scope For This Frontend Plan
- Backend implementation of streaming service, orchestration graph internals, retrieval internals, and MCP server behavior.
- Non-frontend tracing/backend observability implementation.

## Frontend Quality Gates
- [ ] For each new UI behavior, add at least one render/interaction test in the same change.
- [ ] Keep tests deterministic with explicit mocks/stubs (no hidden network dependencies).
- [ ] Before frontend completion/commit, pass:
  - `docker compose exec frontend npm run test`
  - `docker compose exec frontend npm run typecheck`
  - `docker compose exec frontend npm run build`
