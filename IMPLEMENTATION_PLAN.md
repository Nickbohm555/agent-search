# IMPLEMENTATION_PLAN

## Scope
- Frontend-only scoped planning for "all frontend work".
- Inputs reviewed: `specs/*`, `src/frontend/*`, `src/backend/routers/*`, `src/backend/schemas/*`, `src/backend/agents/langgraph_agent.py`, and existing `IMPLEMENTATION_PLAN.md`.
- Planning mode only in this run (no implementation).

## Current State (2026-03-04)
- [x] Frontend scaffold exists: React + TypeScript + Vite (`src/frontend/src/App.tsx`).
- [x] Frontend test harness exists: Vitest + Testing Library (`src/frontend/src/App.test.tsx`).
- [x] API base URL helper exists (`src/frontend/src/utils/config.ts`).
- [ ] Demo UI behavior from spec is not implemented (load/run/progress/final answer).
- [ ] Frontend API client wrappers and typed response normalization are not implemented.
- [ ] Streaming heartbeat UI integration is not implemented.
- [ ] `src/lib/*` does not exist in this repository; shared frontend utilities currently live in `src/frontend/src/utils/*`.

## Remaining Frontend Work (Highest Priority First)
- [ ] P0 - Implement typed frontend API client layer for load/run (`specs/demo-ui-typescript.md`, `specs/data-loading-vectorization.md`)
- Deliverables:
  - Add centralized frontend request/response types and fetch wrappers for `POST /api/internal-data/load` and `POST /api/agents/run` in `src/frontend/src/utils/*`.
  - Normalize backend/non-2xx/payload-shape failures into deterministic UI error objects.
- Verification from spec acceptance criteria:
  - Unit test: successful load response exposes `documents_loaded` and `chunks_created` for UI status display.
  - Unit test: successful run response exposes at least `sub_queries`, `tool_assignments`, `validation_results`, `graph_state` (if present), and final `output`.
  - Unit test: API/network/invalid-payload failures produce consistent user-facing error messages.

- [ ] P0 - Implement demo UI flow for load -> run -> progress -> final answer (`specs/demo-ui-typescript.md`)
- Deliverables:
  - Replace scaffold page with a TypeScript UI containing: load/vectorize controls, query input + run trigger, progress panel, and final answer panel.
  - Show explicit lifecycle states for both actions (idle/loading/success/error/running/completed).
- Verification from spec acceptance criteria:
  - Render test: load area, query input, run action, progress area, and final answer area are visible on initial render.
  - Interaction test: user triggers load and sees a clear success outcome with returned counts.
  - Interaction test: load failure renders clear error state.
  - Interaction test: user runs query and final synthesized answer is displayed.

- [ ] P0 - Implement non-stream progress rendering from run payload as interim heartbeat (`specs/demo-ui-typescript.md`, `specs/query-decomposition.md`, `specs/tool-selection-per-subquery.md`, `specs/retrieval-validation.md`)
- Deliverables:
  - Derive a stable UI timeline/list from `sub_queries`, `tool_assignments`, `validation_results`, and `graph_state.timeline`.
  - Show per-subquery progress and validation outcome so users can observe pipeline progress before final answer.
- Verification from spec acceptance criteria:
  - Unit test: progress mapping preserves user-visible order across decomposition, tool assignment, retrieval/validation, and synthesis completion.
  - Unit test: missing optional graph fields do not crash rendering and still show available progress.
  - Interaction test: completed run shows both progress history and final answer in one user flow.

- [ ] P1 - Add request lifecycle controls and retry behavior (`specs/demo-ui-typescript.md`)
- Deliverables:
  - Prevent duplicate submissions while load/run requests are in-flight.
  - Allow retry after failures without page reload.
- Verification from spec acceptance criteria:
  - Interaction test: active request disables only relevant controls and re-enables them after completion.
  - Interaction test: rapid repeated clicks/submit events do not create duplicate concurrent requests.
  - Interaction test: failed request can be retried successfully in the same session.

- [ ] P1 - Integrate streaming heartbeat UI once backend stream endpoint/contract exists (`specs/streaming-agent-heartbeat.md`, `specs/demo-ui-typescript.md`)
- Deliverables:
  - Add stream client handling (SSE/WebSocket, per backend contract) for near real-time sub-query/progress/final-answer updates.
  - Keep non-stream run-response progress path as fallback when stream is unavailable.
- Verification from spec acceptance criteria:
  - Integration test: during a run, streamed sub-queries appear in near real time.
  - Integration test: streamed progress updates proceed through completion and final answer.
  - Reliability test: event ordering shown to users remains stable in typical runs.

- [ ] P2 - UI polish for simple/sleek responsive demo UX (`specs/demo-ui-typescript.md`)
- Deliverables:
  - Refine typography/layout/state styling so key states are visually distinct and readable.
  - Ensure mobile/desktop usability for controls and results.
- Verification from spec acceptance criteria:
  - Render test: at narrow viewport widths, load/run controls and progress/final-answer regions remain usable.
  - Manual QA checklist: users can clearly distinguish success/error/loading/running/completed states.

## Blockers / Dependencies
- Backend currently exposes `POST /api/internal-data/load` and `POST /api/agents/run`, but no streaming endpoint in `src/backend/routers/*`; streaming UI completion depends on that backend contract.

## Quality Gates (Frontend Scope)
- [ ] For every new UI behavior, add at least one render or interaction test first or in the same change.
- [ ] Keep frontend tests deterministic with explicit API/stream mocks and no hidden network dependencies.
- [ ] Before frontend implementation commits, pass:
  - `docker compose exec frontend npm run test`
  - `docker compose exec frontend npm run typecheck`
  - `docker compose exec frontend npm run build`
