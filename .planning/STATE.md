# STATE: Agent Search HITL + Prompt Customization Milestone

## Project Reference

- **Core value:** Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.
- **Current milestone roadmap:** `.planning/ROADMAP.md`
- **Current focus:** Phase 4 - Operator Controls and Result Visibility

## Current Position

- **Current phase:** 4
- **Current plan:** 04-01
- **Status:** Phase 4 Plan 04-01 Task 2 implemented; Phase 4 Plan 04-01 Task 3 queued
- **Progress:** 3/6 phases complete
- **Progress bar:** `███░░░` (50%)

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
- Start Phase 4 Plan 04-01 Task 3.
- Continue Phase 4 in dependency order after Task 2.
- Keep using git-evidenced summaries before advancing plans.

### Blockers
- None currently.

## Session Continuity

- **Next command:** Implement Section 40 in `IMPLEMENTATION_PLAN.md`
- **Why next:** Phase 4 Plan 04-01 Task 2 is complete, and the next dependency-ordered work item is Task 3 regression coverage for additive runtime config forwarding.
- **Resume note:** State update: `phase=04`, `plan=04-01`, `task=2`, `status=implemented`; router and SDK sync/async entrypoints now forward nested `runtime_config` alongside `thread_id`, and the next work adds focused API/SDK regression coverage.
