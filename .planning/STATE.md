# STATE: Agent Search HITL + Prompt Customization Milestone

## Project Reference

- **Core value:** Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.
- **Current milestone roadmap:** `.planning/ROADMAP.md`
- **Current focus:** Phase 5 - Prompt Customization and Guidance

## Current Position

- **Current phase:** 5
- **Current plan:** 05-03
- **Status:** Phase 4 completed via Plan 04-03 summary; Phase 5 Plan 05-03 Task 2 implemented
- **Progress:** 4/6 phases complete
- **Progress bar:** `████░░` (67%)

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
- Start Phase 5 Plan 05-03 Task 3.
- Add the root README pointer to the canonical prompt customization guide and safety boundaries.
- Keep prompt precedence work additive so existing advanced RAG callers preserve default behavior.

### Blockers
- None currently.

## Session Continuity

- **Next command:** Implement Section 59 in `IMPLEMENTATION_PLAN.md`
- **Why next:** SDK docs are now aligned to the prompt customization contract, so the next dependency-ordered work item is adding the root README pointer and safety note.
- **Resume note:** State update: `phase=05`, `plan=05-03`, `task=2`, `status=implemented`; `sdk/core/README.md` and `sdk/python/README.md` now document mutable prompt defaults, per-run overrides, merge precedence, and runtime safety boundaries, and the next execution target is the root README update.
