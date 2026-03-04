# IMPLEMENTATION_PLAN

## Scope
- Frontend-only planning for "all frontend work" against `specs/*` and current code in `src/frontend/*`.
- Planning mode only: no implementation in this run.

## Status Snapshot (2026-03-04)
- Confirmed frontend is scaffold-only today:
  - `src/frontend/src/App.tsx` renders static scaffold text only.
  - `src/frontend/src/App.test.tsx` has one heading-render test only.
- Confirmed no `src/lib/*` exists in repo (searched with `rg --files src/lib`), so shared frontend utilities currently live in `src/frontend/src/utils/*`.
- Confirmed backend has non-streaming endpoints needed by UI (`/api/internal-data/load`, `/api/agents/run`) and does not yet expose a streaming endpoint/protocol for heartbeat delivery.

## Completed (Frontend Scope)
- [x] Scaffold React + TypeScript + Vite frontend shell exists.
- [x] Basic frontend test harness exists (Vitest + Testing Library + jsdom).
- [x] Shared API base URL helper exists in `src/frontend/src/utils/config.ts`.

## Remaining Work (Highest Priority First)
- [ ] P0 - Build typed frontend API layer for existing endpoints
  - Scope:
    - Add frontend request/response types and API helpers for `/api/internal-data/load` and `/api/agents/run`.
    - Centralize fetch error handling and request-state normalization for deterministic UI behavior.
  - Verification requirements (outcome-focused):
    - Unit tests verify successful parsing of load and run responses into UI-consumable shapes.
    - Unit tests verify non-2xx responses surface user-visible error state payloads (not silent failures).
    - Unit tests verify invalid/missing response fields are handled as failures with stable error messaging.

- [ ] P0 - Implement demo UI core flow in TypeScript (`specs/demo-ui-typescript.md`)
  - Scope:
    - Replace scaffold page with: query input, run trigger, load/vectorize trigger area, status panels, sub-query/progress display, and final answer output.
    - Wire UI actions to typed API layer for load and run flows.
  - Verification requirements (outcome-focused):
    - Render test verifies the app shows query input, run action, load action, and output regions.
    - Interaction test verifies load action shows a loading state then explicit success outcome when API succeeds.
    - Interaction test verifies load action shows explicit error outcome when API fails.
    - Interaction test verifies run action shows final synthesized answer from API response.

- [ ] P0 - Implement heartbeat/progress presentation contract for streamed updates (`specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`)
  - Scope:
    - Add frontend event-consumption layer for heartbeat messages (sub-queries + progress states + completion).
    - Until backend streaming endpoint exists, support a deterministic fallback path from final `/api/agents/run` payload (`sub_queries`, `tool_assignments`, `validation_results`, `graph_state.timeline`) so UI can still present progress structure.
  - Verification requirements (outcome-focused):
    - Unit tests verify incoming heartbeat events append/update visible sub-query/progress state in order.
    - Unit tests verify duplicate/out-of-order event sequences do not corrupt displayed progress state.
    - Interaction test verifies completion event (or fallback completed payload) renders final answer and terminal status.

- [ ] P1 - Add explicit UI states for run lifecycle and resilience
  - Scope:
    - Add idle/running/completed/error states for both load and run actions.
    - Prevent duplicate submits while a run or load is active.
    - Provide retry affordance after failures.
  - Verification requirements (outcome-focused):
    - Interaction test verifies run button is disabled during active run and re-enabled after completion/error.
    - Interaction test verifies repeated quick clicks trigger only one in-flight request.
    - Interaction test verifies error state is visible and retry can successfully complete a later request.

- [ ] P1 - Add frontend utility consolidation for shared presentation logic
  - Scope:
    - Create/extend `src/frontend/src/utils/*` helpers for transforming run payloads and heartbeat events into normalized view models.
    - Keep rendering components thin and deterministic.
  - Verification requirements (outcome-focused):
    - Unit tests verify deterministic mapping from API/stream payloads to rendered list items and status labels.
    - Unit tests verify empty-results edge cases produce valid empty UI states (not crashes).

- [ ] P2 - Visual polish pass to satisfy "simple and sleek" requirement (`specs/demo-ui-typescript.md`)
  - Scope:
    - Upgrade layout/typography/states from scaffold card to intentional, production-demo-ready styling.
    - Ensure responsive behavior for desktop and mobile widths.
  - Verification requirements (outcome-focused):
    - Render tests verify key regions remain visible/accessible at narrow viewport widths.
    - Manual verification checklist confirms readable hierarchy, clear progress emphasis, and clear success/error contrast.

## Dependency / Sequencing Notes
- Streaming-backed real-time UI acceptance cannot be fully validated until backend streaming service is implemented (`specs/streaming-agent-heartbeat.md`).
- Frontend tasks above are sequenced to deliver value with existing APIs first, then adopt live streaming with minimal refactor.

## Frontend Quality Gates
- [ ] For each new UI behavior, add at least one render/interaction test first or in same change.
- [ ] Keep frontend tests deterministic and independent from hidden network dependencies.
- [ ] Before implementation commits: run `docker compose exec frontend npm run test`, `docker compose exec frontend npm run typecheck`, and `docker compose exec frontend npm run build`.
