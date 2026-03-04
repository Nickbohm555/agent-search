# IMPLEMENTATION_PLAN

## Scope
- Scoped target: `all frontend work` only.
- Inputs reviewed: `specs/*`, `src/frontend/*`, `src/frontend/src/lib/*`, existing `IMPLEMENTATION_PLAN.md`, and backend route/schema surface needed for frontend integration.
- Mode: planning only (no feature implementation in this run).

## Current Frontend Status (2026-03-04)
- [x] TypeScript demo UI exists (`React + Vite`) with load and run controls.
- [x] Typed API client exists for `POST /api/internal-data/load` and `POST /api/agents/run` with deterministic error mapping.
- [x] Final answer rendering exists for successful runs.
- [x] Non-stream fallback progress rendering exists (`graph_state.timeline`, sub-queries, validation results).
- [x] Frontend tests exist for core load/run outcomes and API client behavior.
- [ ] Streaming heartbeat consumption is not implemented in frontend (no SSE/WebSocket/EventSource client).
- [ ] Cyberpunk visual theme is not implemented (current CSS is light neutral theme).
- [ ] Deck-style panel/chrome layout is not implemented.
- [ ] Readout-style output treatment is minimal and not themed.
- [ ] Motion and retro-tech feedback treatment is minimal.
- [ ] Accessibility hardening for cyberpunk styling (contrast/focus/reduced-motion/readability) is not implemented.

## Spec Coverage Snapshot (Frontend)
- `specs/demo-ui-typescript.md`: partial (load/run exists; streaming heartbeat UI missing).
- `specs/visual-theme.md`: not implemented.
- `specs/layout-and-chrome.md`: not implemented.
- `specs/content-and-readouts.md`: partially implemented functionally, not aesthetically implemented.
- `specs/motion-and-feedback.md`: minimally implemented functionally, not aesthetically implemented.
- `specs/accessibility-within-aesthetic.md`: not implemented as an explicit themed accessibility pass.

## Prioritized Frontend Tasks (Highest Priority Incomplete First)

- [ ] P0 - Integrate streaming heartbeat into run UX (`demo-ui-typescript`, `streaming-agent-heartbeat`)
- Why:
  - Frontend acceptance requires sub-queries/progress to appear as streamed events in near real-time.
  - Current UI only shows post-response/fallback payload data.
- Confirmed gap:
  - No streaming route in `src/backend/routers/*`; frontend has no stream client.
- Verification requirements (outcome-focused):
  - Test: during a run, sub-queries appear incrementally before final completion.
  - Test: visible progress state updates as heartbeat events arrive.
  - Test: terminal completion event (or equivalent) shows final answer and complete state.
  - Test: stream interruption shows degraded/connection-lost status without freezing the UI.
  - Test: mocked stream transport keeps tests deterministic and offline.
- Dependency:
  - Requires backend streaming endpoint and stable event contract.

- [ ] P0 - Implement cyberpunk visual theme foundation (`visual-theme`)
- Why:
  - Theme is a core explicit frontend requirement and base for all other aesthetic specs.
- Verification requirements (outcome-focused):
  - Test: initial render uses dark/noir base surfaces with at least one neon accent for interactive or status elements.
  - Test: headings, body, and readout text tiers are visually distinct.
  - Test: panels/surfaces are visually distinct from background.
  - QA: reviewer can reasonably identify look as cyberpunk/neon-noir.

- [ ] P0 - Implement deck-style structure and chrome (`layout-and-chrome`)
- Why:
  - Acceptance requires clearly framed control/progress/result instrument areas.
- Verification requirements (outcome-focused):
  - Test: controls, progress/status, and result/readout are distinct sections.
  - Test: section boundaries/chrome are visible and consistent.
  - Test: first-time user path is clear (where to act vs where to read).
  - Test: responsive layout preserves section hierarchy on narrower widths.

- [ ] P1 - Apply readout-oriented content presentation (`content-and-readouts`)
- Why:
  - Functional data exists, but presentation does not yet read as cohesive deck/readout output.
- Verification requirements (outcome-focused):
  - Test: load/run success and error outcomes are displayed in readout-style status treatment.
  - Test: final answer is visually dominant and easy to scan.
  - Test: sub-queries/progress remain ordered and scannable in themed output format.
  - Test: users can distinguish asked query vs system progress vs system answer from UI structure/styling.

- [ ] P1 - Implement motion and action feedback patterns (`motion-and-feedback`)
- Why:
  - Current loading feedback is basic label swaps; spec expects cohesive retro-tech transitions/feedback.
- Verification requirements (outcome-focused):
  - Test: triggering load/run produces immediate, visible processing feedback tied to that action.
  - Test: progress/status changes are perceptibly apparent as updates occur.
  - Test: decorative motion does not obscure controls, progress, or answer readability.
  - Test: transitions are consistent across major state changes.

- [ ] P1 - Accessibility hardening pass within the themed UI (`accessibility-within-aesthetic`)
- Why:
  - Cyberpunk styling must preserve usability and readability.
- Verification requirements (outcome-focused):
  - Test: all interactive controls show visible keyboard focus indicators.
  - Test: keyboard-only user can complete load and run flows in logical focus order.
  - Test: with `prefers-reduced-motion: reduce`, non-essential motion is reduced while essential status remains visible.
  - Test: final answer and primary statuses remain readable at 200% zoom.
  - Audit task: contrast meets WCAG AA for core text/labels, or explicit exceptions are documented.

## Already Completed Frontend Work
- [x] Load/vectorize trigger and status path in UI.
- [x] Query run trigger and final answer rendering.
- [x] API error handling path for HTTP/network/timeout/malformed responses.
- [x] In-flight action safety (duplicate request prevention + retry after failure).
- [x] Progress-history fallback UI from non-stream run payload.

## Frontend Quality Gates
- [ ] Each new UI behavior ships with at least one frontend render/interaction test in the same change.
- [ ] Tests verify user-observable outcomes, not implementation internals.
- [ ] Tests are deterministic (mocked stream/network behavior; no hidden network dependency).
- [ ] Frontend checks pass before completion: `docker compose exec frontend npm run test`.
- [ ] Frontend checks pass before completion: `docker compose exec frontend npm run typecheck`.
- [ ] Frontend checks pass before completion: `docker compose exec frontend npm run build`.
