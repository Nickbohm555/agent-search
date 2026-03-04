# IMPLEMENTATION_PLAN

## Scope
- Frontend-only scoped planning for "all frontend work".
- Inputs reviewed: `specs/*`, `src/frontend/*`, `src/backend/schemas/*`, `src/backend/routers/*`, and existing `IMPLEMENTATION_PLAN.md`.
- Planning mode only: no implementation in this run.

## Status Snapshot (2026-03-04)
- `src/frontend/src/App.tsx` is scaffold text only; no load/run/progress UI exists.
- `src/frontend/src/App.test.tsx` has one scaffold heading render test only.
- `src/lib/*` is not present in this repo; shared frontend utilities currently live in `src/frontend/src/utils/*`.
- Confirmed backend endpoints available for frontend integration now:
  - `POST /api/internal-data/load`
  - `POST /api/agents/run`
- Confirmed no backend streaming endpoint currently exposed, so live heartbeat UI cannot be fully completed yet.

## Completed (Frontend Scope)
- [x] React + TypeScript + Vite scaffold exists.
- [x] Frontend test harness exists (Vitest + Testing Library + jsdom).
- [x] API base URL helper exists in `src/frontend/src/utils/config.ts`.

## Remaining (Highest Priority First)
- [ ] P0 - Build typed frontend API client and deterministic error model (`specs/demo-ui-typescript.md`)
  - Scope:
    - Add typed request/response contracts for `POST /api/internal-data/load` and `POST /api/agents/run`.
    - Centralize fetch, HTTP error handling, timeout/cancellation handling, and user-safe error messages.
  - Verification requirements (derived from UI load/run acceptance criteria):
    - Unit test: successful `load` response maps to a UI-ready success payload with observable counts (`documents_loaded`, `chunks_created`).
    - Unit test: successful `run` response maps to a UI-ready result with `sub_queries`, progress source data, and final `output`.
    - Unit test: non-2xx responses produce stable error objects that the UI can display directly.
    - Unit test: malformed or missing response fields fail fast with deterministic error messaging (no silent success).

- [ ] P0 - Implement demo UI core workflow in TypeScript (`specs/demo-ui-typescript.md`)
  - Scope:
    - Replace scaffold page with query input, run action, load/vectorize action, status regions, sub-query/progress region, and final-answer region.
    - Wire actions to the typed API client.
  - Verification requirements (derived from demo UI acceptance criteria):
    - Render test: UI exposes query input, run trigger, load trigger, progress area, and final answer area.
    - Interaction test: user can trigger load and sees explicit loading -> success state.
    - Interaction test: load failure surfaces explicit error state.
    - Interaction test: user can trigger run and sees final answer from API output.

- [ ] P0 - Implement heartbeat/progress consumption for frontend (`specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`)
  - Scope:
    - Add client-side stream consumer abstraction (SSE/WebSocket-ready interface) for heartbeat/sub-query/progress/final events.
    - Until backend stream exists, implement deterministic fallback that projects progress from `/api/agents/run` response (`sub_queries`, `tool_assignments`, `validation_results`, `graph_state.timeline`).
  - Verification requirements (derived from streaming + demo UI acceptance criteria):
    - Unit test: streamed sub-query/progress events appear in UI state in event order.
    - Unit test: duplicate or out-of-order events do not corrupt the visible progress timeline.
    - Interaction test: completion event (or fallback completed projection) updates terminal state and renders final answer.
    - Performance-focused test: a burst of heartbeat events (deterministic fixture) is rendered without dropping items and updates are visible near-real-time in test-controlled timing.

- [ ] P1 - Add robust run/load lifecycle UX states and retry behavior (`specs/demo-ui-typescript.md`)
  - Scope:
    - Explicit idle/running/success/error states for load and run flows.
    - Prevent duplicate submissions while request is active; provide retry path after failure.
  - Verification requirements:
    - Interaction test: run and load triggers are disabled during active requests and re-enabled on completion/failure.
    - Interaction test: repeated rapid clicks produce only one in-flight request per action.
    - Interaction test: after error, retry can complete successfully and UI reflects recovered success state.

- [ ] P1 - Consolidate frontend shared transformation helpers in `src/frontend/src/utils/*`
  - Scope:
    - Add pure helpers that normalize API and stream payloads into UI view models.
    - Keep components focused on rendering and user interaction only.
  - Verification requirements:
    - Unit test: deterministic mapping from backend payloads to UI view models (sub-query rows, statuses, answer block).
    - Unit test: empty results and partial-progress payloads produce valid empty/partial UI states instead of crashes.

- [ ] P2 - Deliver "simple and sleek" responsive visual design pass (`specs/demo-ui-typescript.md`)
  - Scope:
    - Replace scaffold styling with intentional demo-ready layout, typography, and state styling.
    - Ensure mobile and desktop readability/accessibility.
  - Verification requirements:
    - Render test: key controls and status/output regions remain present and usable at narrow viewport sizes.
    - Manual verification: visual hierarchy is clear, progress is easy to scan, and success/error states are clearly distinguishable.

## Dependencies / Constraints
- Full real-time acceptance for streaming depends on backend streaming service work from `specs/streaming-agent-heartbeat.md`.
- Plan sequencing above is designed to deliver value now using existing non-streaming endpoints, then swap in live stream delivery with minimal frontend refactor.

## Frontend Quality Gates
- [ ] For each new UI behavior, add at least one render/interaction test in the same change.
- [ ] Keep tests deterministic; mock network and stream sources explicitly.
- [ ] Before implementation commits, pass:
  - `docker compose exec frontend npm run test`
  - `docker compose exec frontend npm run typecheck`
  - `docker compose exec frontend npm run build`
