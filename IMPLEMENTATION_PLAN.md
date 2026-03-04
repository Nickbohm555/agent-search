# IMPLEMENTATION_PLAN

## Scope
- Scoped planning target: `all frontend work` only.
- Reviewed this run: `specs/*`, `src/frontend/*`, `src/backend/routers/*`, `src/backend/schemas/agent.py`, existing `IMPLEMENTATION_PLAN.md`.
- Planning mode only: no implementation in this run.

## Current Frontend Status (2026-03-04)
- [x] TypeScript React/Vite demo shell exists with load and run actions.
- [x] Typed frontend API client exists for `POST /api/internal-data/load` and `POST /api/agents/run` with deterministic error handling.
- [x] Frontend tests exist for API behavior and core load/run interactions.
- [x] Non-stream fallback progress rendering exists from `graph_state.timeline` or returned run payload arrays.
- [ ] Real-time streaming heartbeat UI is not implemented (`EventSource`/WebSocket client not present).
- [ ] Cyberpunk visual theme is not implemented (current UI is light theme; no neon-noir token system).
- [ ] Deck-style layout/chrome is not implemented (controls/progress/result are not framed as distinct instrument panels).
- [ ] Readout-style presentation is minimal and not yet themed as cohesive terminal/deck output.
- [ ] Motion/retro feedback treatment is not implemented beyond basic loading label changes.
- [ ] Accessibility constraints specific to the cyberpunk theme are not yet implemented/tested (focus treatment, reduced motion behavior, contrast checks).
- [ ] Repo-level `src/lib/*` standard-library path is missing; shared frontend utilities currently live in `src/frontend/src/lib/*`.

## Prioritized Frontend Tasks (Highest Priority First)

- [ ] P0 - Implement streaming heartbeat UI integration once backend stream endpoint/contract is available
- Why:
  - `specs/demo-ui-typescript.md` requires streamed sub-queries/progress in near real-time.
  - `specs/streaming-agent-heartbeat.md` requires live heartbeat consumption by UI.
- Confirmed gap:
  - Backend exposes `RuntimeAgentStreamEvent` schema but no streaming route in `src/backend/routers/*`; frontend has no streaming client code.
- Verification requirements (outcome-focused):
  - Integration test: during a run, streamed sub-queries appear incrementally in the UI before completion.
  - Integration test: streamed progress/status updates change the visible current state as events arrive.
  - Integration test: completion event (or terminal stream payload) renders final answer and marks run complete.
  - Resilience test: if stream disconnects mid-run, UI shows clear degraded state and still reaches stable success/error via fallback.
  - Determinism check: mocked stream source drives tests without external network dependencies.
- Blockers:
  - Requires backend streaming transport and concrete event contract (SSE/WebSocket route + payload shape).

- [ ] P0 - Implement cyberpunk visual foundation (theme tokens, typography, status colors)
- Why:
  - Required by `specs/visual-theme.md` and prerequisite for other aesthetic specs.
- Verification requirements (outcome-focused):
  - Render test: on load, app uses dark/noir base surfaces with at least one neon accent on interactive/status elements.
  - Render test: heading/body/readout text hierarchy is visually distinct and readable.
  - Render test: panel surfaces are visually distinct from page background.
  - Manual QA check: reviewer can reasonably identify the UI as cyberpunk/neon-noir.

- [ ] P0 - Implement deck-style layout and chrome for controls, progress, and result areas
- Why:
  - Required by `specs/layout-and-chrome.md`; current structure does not yet present clear instrument-panel framing.
- Verification requirements (outcome-focused):
  - Render test: controls area, progress/status area, and result/readout area are visually distinct sections.
  - Render test: section boundaries/chrome (frames, dividers, labels) are consistently visible.
  - Interaction test: first-time user path remains clear (where to act vs where to read) throughout load/run lifecycle.
  - Responsive render test: layout remains usable on desktop and preserves section hierarchy at narrow widths.

- [ ] P1 - Implement readout-oriented content treatment for status, progress, and final answer
- Why:
  - Required by `specs/content-and-readouts.md`; current output is functional but not yet a cohesive readout surface.
- Verification requirements (outcome-focused):
  - Render test: load/run outcomes (success/error/counts) are visible in readout-style treatment.
  - Render test: final answer remains the dominant content in result area.
  - Render test: sub-queries/progress appear in ordered, scannable form aligned with themed readout styling.
  - Interaction test: users can distinguish query input, system progress, and final answer from layout/styling alone.

- [ ] P1 - Add motion and feedback patterns consistent with retro-tech aesthetic
- Why:
  - Required by `specs/motion-and-feedback.md`.
- Verification requirements (outcome-focused):
  - Interaction test: triggering load/run shows a visible processing state tied to that action.
  - Interaction test: progress/status updates are perceptibly apparent as state changes occur.
  - Render/interaction test: any decorative effect does not obscure controls or answer content.
  - Consistency check: transitions are consistent across major UI state changes.

- [ ] P1 - Enforce accessibility constraints within the cyberpunk theme
- Why:
  - Required by `specs/accessibility-within-aesthetic.md`; must be validated alongside theme/chrome/motion changes.
- Verification requirements (outcome-focused):
  - Accessibility test: interactive controls expose visible keyboard focus state.
  - Interaction test: keyboard-only user can complete load and run flows in logical focus order.
  - Reduced-motion test: with `prefers-reduced-motion: reduce`, non-essential motion is reduced while status/feedback remains visible.
  - Readability check: final answer and primary statuses remain readable with theme applied, including 200% zoom sanity pass.
  - Contrast audit task: verify WCAG AA contrast targets for body/labels, or document explicit exceptions.

- [ ] P2 - Align shared frontend primitives with project standard library path (`src/lib/*`)
- Why:
  - Run instructions treat `src/lib/*` as the shared utility/component location; currently absent.
- Verification requirements (outcome-focused):
  - Build/typecheck: shared imports resolve cleanly from standardized path.
  - Regression test: existing load/run/progress UI behavior remains unchanged after consolidation.
  - Determinism check: test suite remains stable with no added hidden network dependencies.

## Completed Frontend Work (Already Implemented)
- [x] Typed API client for load/run with deterministic error mapping and payload guards.
- [x] Demo UI flow for load, run, final answer display.
- [x] Progress-history fallback rendering from non-stream run payload.
- [x] Request lifecycle protections (in-flight lockout, duplicate prevention, retry-after-failure).

## Out Of Scope For This Frontend Plan
- Backend implementation details for LangGraph orchestration, retrieval internals, validation internals, and MCP server behavior.
- Backend streaming route implementation (not frontend scope), except frontend integration tasking once contract exists.

## Frontend Quality Gates
- [ ] Every new UI behavior includes at least one render/interaction test in the same change.
- [ ] Tests verify user-observable outcomes, not internal implementation details.
- [ ] Tests remain deterministic with explicit mocks/stubs and no hidden network dependency.
- [ ] Before frontend completion: `docker compose exec frontend npm run test`.
- [ ] Before frontend completion: `docker compose exec frontend npm run typecheck`.
- [ ] Before frontend completion: `docker compose exec frontend npm run build`.
