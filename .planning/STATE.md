# STATE: Agent Search HITL + Prompt Customization Milestone

## Project Reference

- **Core value:** Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.
- **Current milestone roadmap:** `.planning/ROADMAP.md`
- **Current focus:** Phase 2 - Subquestion HITL End-to-End

## Current Position

- **Current phase:** 2
- **Current plan:** 02-03
- **Status:** Phase 2 Plan 02-03 summary implemented; next section queued
- **Progress:** 1/6 phases complete
- **Progress bar:** `█░░░░░` (17%)

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
- Start Phase 2 Plan 02-04 Task 1.
- Continue Phase 2 in dependency order after the completed 02-03 summary.
- Keep using git-evidenced summaries before advancing plans.

### Blockers
- None currently.

## Session Continuity

- **Next command:** Implement Section 24 in `IMPLEMENTATION_PLAN.md`
- **Why next:** Phase 2 Plan 02-03 summary is complete, and the next dependency-ordered work item is Phase 2 Plan 02-04 Task 1.
- **Resume note:** State update: `phase=02`, `plan=02-03`, `task=summary`, `status=implemented`; SDK async parity now covers typed HITL enablement, typed approve/edit/deny/skip resumes, malformed envelope errors, and default-off compatibility.
