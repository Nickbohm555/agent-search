# IMPLEMENTATION_PLAN

## Scope
- Frontend-only scoped planning for "all frontend work".
- Inputs reviewed this run: `specs/*`, `src/frontend/*`, `src/backend/schemas/*`, `src/backend/routers/*`, `src/backend/tests/api/*`, and existing `IMPLEMENTATION_PLAN.md`.
- Planning mode only: no implementation in this run.

## Status Snapshot (2026-03-04)
- `src/frontend/src/App.tsx` is scaffold text only; no load/run/progress UI exists.
- `src/frontend/src/App.test.tsx` has only a scaffold-heading render assertion.
- `src/lib/*` is not present in this repository; shared frontend utilities currently live in `src/frontend/src/utils/*`.
- Backend contracts available now for frontend integration:
  - `POST /api/internal-data/load`
  - `POST /api/agents/run`
- No backend streaming endpoint is currently exposed (confirmed by code search), so true real-time heartbeat consumption is blocked pending backend streaming work.

## Completed (Frontend Scope)
- [x] React + TypeScript + Vite scaffold exists.
- [x] Frontend test harness exists (`vitest` + Testing Library + jsdom).
- [x] Frontend API base config helper exists in `src/frontend/src/utils/config.ts`.

## Remaining Frontend Work (Highest Priority First)
- [ ] P0 - Build typed frontend API layer for run/load flows (`specs/demo-ui-typescript.md`)
  - Task:
    - Add typed request/response contracts for `POST /api/internal-data/load` and `POST /api/agents/run`.
    - Centralize fetch behavior, non-2xx handling, and deterministic UI-safe error objects.
  - Verification requirements (acceptance-driven outcomes):
    - Unit test: successful load call returns typed outcome including observable `documents_loaded` and `chunks_created`.
    - Unit test: successful run call returns typed outcome including `sub_queries`, `graph_state`, and final `output` for UI rendering.
    - Unit test: non-2xx responses surface deterministic user-displayable error state (not silent failure).
    - Unit test: malformed payloads are rejected and surfaced as explicit client error outcomes.

- [ ] P0 - Implement demo UI workflow: load data, run query, show final answer (`specs/demo-ui-typescript.md`)
  - Task:
    - Replace scaffold page with TypeScript UI containing query input, run trigger, load/vectorize trigger, and result/status regions.
    - Wire controls to API layer with explicit pending/success/error state transitions.
  - Verification requirements (acceptance-driven outcomes):
    - Render test: page exposes load trigger, query input, run trigger, progress/sub-query region, and final-answer region.
    - Interaction test: user can trigger load and sees clear loading then success outcome.
    - Interaction test: load failure shows a clear error outcome.
    - Interaction test: user can run query and final answer is displayed from API response.

- [ ] P0 - Implement frontend progress timeline model with stream-ready interface (`specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`)
  - Task:
    - Add a frontend event/timeline abstraction that can accept heartbeat/sub-query/progress/final events.
    - Implement immediate fallback projection from `/api/agents/run` payload (`sub_queries`, `tool_assignments`, `validation_results`, `graph_state.timeline`) until backend streaming endpoint exists.
  - Verification requirements (acceptance-driven outcomes):
    - Unit test: fallback projection produces ordered sub-query/progress entries visible to the UI.
    - Unit test: duplicate or out-of-order events are normalized so timeline state remains consistent.
    - Interaction test: completion state renders terminal progress and final answer.
    - Deterministic timing test: burst event fixture updates UI without dropping entries.

- [ ] P1 - Add request lifecycle guardrails and retry UX (`specs/demo-ui-typescript.md`)
  - Task:
    - Prevent duplicate submissions while load/run is active.
    - Provide retry flows after failed load/run attempts.
  - Verification requirements (acceptance-driven outcomes):
    - Interaction test: load/run controls are disabled during active requests and re-enabled after settle.
    - Interaction test: rapid repeated clicks issue only one in-flight request per action.
    - Interaction test: after error, retry can succeed and UI reflects recovered success state.

- [ ] P1 - Consolidate frontend shared transforms/utilities in `src/frontend/src/utils/*` (repo standard)
  - Task:
    - Keep mapping/normalization logic in shared utils; keep UI components focused on rendering and interaction.
    - Reuse utility modules for API and timeline shaping to avoid component-level duplication.
  - Verification requirements (acceptance-driven outcomes):
    - Unit test: backend payload -> UI model mapping is deterministic for sub-queries, statuses, and answer block.
    - Unit test: empty/partial payloads yield valid empty/partial UI states rather than crashes.

- [ ] P2 - Apply simple, sleek, responsive visual pass (`specs/demo-ui-typescript.md`)
  - Task:
    - Deliver polished, minimal styling for desktop and mobile while preserving clear state feedback.
  - Verification requirements (acceptance-driven outcomes):
    - Render test: core controls and output/progress regions remain present and usable at narrow viewport widths.
    - Manual QA check: success/error/progress states are visually distinct and easy to scan.

## Blockers / Dependencies
- Frontend true real-time heartbeat (SSE/WebSocket) remains blocked until backend streaming endpoint exists (see `specs/streaming-agent-heartbeat.md`).
- Plan intentionally sequences fallback-first UI so frontend delivery can proceed with existing backend contracts.

## Frontend Quality Gates
- [ ] For each new UI behavior, include at least one render or interaction test in the same change.
- [ ] Keep tests deterministic with explicit network/event mocking.
- [ ] Before implementation commit, pass:
  - `docker compose exec frontend npm run test`
  - `docker compose exec frontend npm run typecheck`
  - `docker compose exec frontend npm run build`
