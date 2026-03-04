# IMPLEMENTATION_PLAN

## Scope
- Frontend-only scoped planning for "all frontend work".
- Inputs reviewed: `specs/*`, current frontend code in `src/frontend/*`, backend API contracts in `src/backend/routers/*` + `src/backend/schemas/*`, and existing plan.
- Planning mode only (no implementation in this run).

## Current State (2026-03-04)
- [x] React + TypeScript + Vite scaffold exists (`src/frontend/src/App.tsx`).
- [x] Frontend test harness exists with Vitest + Testing Library (`src/frontend/src/App.test.tsx`).
- [x] Frontend API base URL helper exists (`src/frontend/src/utils/config.ts`).
- [ ] Demo UI behavior from spec is not implemented (load/vectorize, query run, progress, final answer).
- [ ] Frontend API client typing/normalization for backend contracts is not implemented.
- [ ] Streaming heartbeat integration is not implemented and backend stream endpoint/contract is not yet exposed.
- [ ] `src/lib/*` is absent in this repository (confirmed by file search); shared frontend code currently only exists under `src/frontend/src/*`.

## Frontend Tasks Remaining (Highest Priority First)
- [ ] P0 - Implement typed frontend API client for demo UI load/run flows
- Why this priority:
  - The UI acceptance criteria depend on reliable request/response handling for load and run.
  - Centralized typing/error normalization is prerequisite for deterministic UI states/tests.
- Deliverables:
  - Add typed wrappers for `POST /api/internal-data/load` and `POST /api/agents/run`.
  - Add deterministic normalization for transport failures, non-2xx responses, and invalid payload shapes.
  - Keep shared helpers consolidated in `src/frontend/src/utils/*` for now; if cross-app reuse emerges, introduce `src/lib/*` in a follow-up task.
- Verification requirements (outcomes, not implementation):
  - Unit test: successful load call returns UI-consumable `documents_loaded` and `chunks_created` values.
  - Unit test: successful run call returns UI-consumable `sub_queries`, `tool_assignments`, `validation_results`, optional `graph_state`, and `output`.
  - Unit test: network failure and non-2xx API failure both produce consistent, user-safe error objects/messages.
  - Unit test: malformed payloads are rejected into a deterministic error outcome (no uncaught runtime crash).

- [ ] P0 - Implement TypeScript demo UI for load/vectorize + run + final answer
- Why this priority:
  - This is the core acceptance criteria in `specs/demo-ui-typescript.md`.
  - Current app is still scaffold text only.
- Deliverables:
  - Replace scaffold screen with a simple/sleek UI including:
    - load/vectorize action area with visible status
    - query input + run action
    - final answer display
    - explicit UI lifecycle states (`idle`, `loading/running`, `success/completed`, `error`)
- Verification requirements (outcomes, not implementation):
  - Render test: load controls, query input, run trigger, status/progress region, and final-answer region are visible on first render.
  - Interaction test: user triggers load and sees a clear success outcome with returned counts.
  - Interaction test: load failure shows a clear error state and message.
  - Interaction test: user submits a query and sees the final synthesized answer rendered.

- [ ] P0 - Render per-subquery progress from available run payload as non-stream fallback heartbeat
- Why this priority:
  - Streaming backend is not yet exposed; UI still needs observable progress now.
  - Backend already returns progress-compatible fields (`sub_queries`, `tool_assignments`, `validation_results`, `graph_state.timeline`).
- Deliverables:
  - Build a stable progress timeline/list derived from run response fields.
  - Show per-subquery status and validation outcomes before/alongside final answer.
  - Ensure UI tolerates missing optional graph fields without breaking.
- Verification requirements (outcomes, not implementation):
  - Unit test: progress view ordering reflects decomposition -> tool selection -> per-subquery retrieval/validation -> synthesis completion.
  - Unit test: when `graph_state` or `timeline` is missing, UI still renders available progress data and final answer.
  - Interaction test: completed run shows both progress history and final answer in one flow.

- [ ] P1 - Add request lifecycle safeguards (in-flight lockout + retry)
- Why this priority:
  - Prevents duplicate requests and improves recoverability after failures.
- Deliverables:
  - Disable only relevant controls while associated request is in flight.
  - Allow retry for failed load/run without page reload.
- Verification requirements (outcomes, not implementation):
  - Interaction test: while load is in flight, load control is disabled and later re-enabled.
  - Interaction test: while run is in flight, run control is disabled and later re-enabled.
  - Interaction test: repeated rapid submit/click attempts do not create duplicate concurrent calls.
  - Interaction test: failure can be retried successfully in the same session.

- [ ] P1 - Implement streaming heartbeat integration once backend stream contract exists
- Why this priority:
  - Required by `specs/demo-ui-typescript.md` acceptance criteria for near real-time updates.
  - Currently blocked by missing backend stream endpoint/protocol contract.
- Deliverables:
  - Add stream client integration (protocol per backend contract: SSE/WebSocket).
  - Merge streamed events into the progress UI and preserve non-stream fallback path.
- Verification requirements (outcomes, not implementation):
  - Integration test: when a run starts, streamed sub-queries appear in near real time.
  - Integration test: streamed progress reaches completion and final answer is rendered.
  - Reliability test: user-visible event ordering remains stable during typical runs.
  - Resilience test: when stream is unavailable/interrupted, UI falls back to non-stream run result without crashing.

- [ ] P2 - Apply responsive UI polish for "simple and sleek" demo UX
- Why this priority:
  - Lower risk than core behavior; should follow functional completion.
- Deliverables:
  - Improve visual hierarchy and state readability (success/error/loading/running/completed).
  - Ensure usability on desktop and narrow mobile widths.
- Verification requirements (outcomes, not implementation):
  - Render test: at narrow viewport widths, load/run controls remain usable and readable.
  - Render/interaction test: state changes are visually distinguishable and accessible to users.
  - Manual QA: confirm simple/sleek presentation with clear progress + final answer readability.

## Confirmed Dependencies / Blockers
- Streaming UI work depends on backend exposing a documented streaming endpoint/contract. Current backend routes include `POST /api/agents/run` and do not expose `/stream`/SSE/WebSocket endpoint yet.

## Frontend Quality Gates
- [ ] For each new UI behavior, add at least one render or interaction test in the same change.
- [ ] Keep frontend tests deterministic with explicit mocks (no hidden network dependency).
- [ ] Before frontend implementation commits, pass:
  - `docker compose exec frontend npm run test`
  - `docker compose exec frontend npm run typecheck`
  - `docker compose exec frontend npm run build`
