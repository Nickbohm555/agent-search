# STATE: Agent Search HITL + Prompt Customization Milestone

## Project Reference

- **Core value:** Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.
- **Current milestone roadmap:** `.planning/ROADMAP.md`
- **Current focus:** Phase 6 - SDK Contract Parity and PyPI Release

## Current Position

- **Current phase:** 6
- **Current plan:** 06-01
- **Status:** Phase 6 Plan 06-01 Task 1 implemented; Task 2 is next
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
- Start Phase 6 Plan 06-01 Task 2.
- Regenerate OpenAPI and generated SDK artifacts after locking backend/sdk-core parity fields.

### Blockers
- None currently.

## Session Continuity

- **Next command:** Implement Section 68 in `IMPLEMENTATION_PLAN.md`
- **Why next:** Plan 06-01 Task 1 locked backend and sdk/core contract fields, so the next dependency-ordered step is regenerating OpenAPI and generated SDK artifacts.
- **Resume note:** State update: `phase=06`, `plan=06-01`, `task=1`, `status=implemented`; backend and sdk/core now expose the Phase 1-5 HITL/control/prompt/sub-answer contract surface, and the next target is Task 2 artifact regeneration.
