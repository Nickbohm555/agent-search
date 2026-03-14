# STATE: Agent Search HITL + Prompt Customization Milestone

## Project Reference

- **Core value:** Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.
- **Current milestone roadmap:** `.planning/ROADMAP.md`
- **Current focus:** Phase 6 - SDK Contract Parity and PyPI Release

## Current Position

- **Current phase:** 6
- **Current plan:** 06-01
- **Status:** Phase 6 Plan 06-01 Task 2 implemented; Task 3 is next
- **Progress:** 5/6 phases complete
- **Progress bar:** `█████░` (83%)

## Performance Metrics

- **Roadmap depth:** comprehensive
- **v1 requirements total:** 24
- **Mapped requirements:** 24
- **Coverage:** 100%
- **Orphaned requirements:** 0

## Accumulated Context

### Decisions
- Phase structure is requirement-driven: foundation -> two HITL loops -> control surfaces -> prompt customization -> external release.
- HITL default-off compatibility is front-loaded in Phase 1 to protect existing users.
- SDK/PyPI release finalization is isolated in Phase 6 to avoid contract drift and premature publication.

### TODOs
- Start Phase 6 Plan 06-01 Task 3.
- Add release-blocking parity regressions for backend/api/runtime-config contract fields and OpenAPI drift validation.

### Blockers
- None currently.

## Session Continuity

- **Next command:** Implement Section 69 in `IMPLEMENTATION_PLAN.md`
- **Why next:** Plan 06-01 Task 2 refreshed `openapi.json` and generated `sdk/python` artifacts, so the next dependency-ordered step is adding release-blocking parity regressions against the locked contract surface.
- **Resume note:** State update: `phase=06`, `plan=06-01`, `task=2`, `status=implemented`; OpenAPI and generated Python SDK artifacts now match the backend contract, and the next target is Task 3 regression coverage.
