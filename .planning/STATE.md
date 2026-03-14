# STATE: Agent Search HITL + Prompt Customization Milestone

## Project Reference

- **Core value:** Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.
- **Current milestone roadmap:** `.planning/ROADMAP.md`
- **Current focus:** Phase 4 - Operator Controls and Result Visibility

## Current Position

- **Current phase:** 4
- **Current plan:** 04-02
- **Status:** Phase 4 Plan 04-02 Task 2 implemented; Phase 4 Plan 04-02 Task 3 queued
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
- Implement Phase 4 Plan 04-02 Task 3.
- Continue Phase 4 in dependency order after service-level control toggle regressions.
- Keep using git-evidenced summaries before advancing plans.

### Blockers
- None currently.

## Session Continuity

- **Next command:** Implement Section 44 in `IMPLEMENTATION_PLAN.md`
- **Why next:** Phase 4 Plan 04-02 Task 2 is complete, and the next dependency-ordered work item is adding service-level regressions for per-run query expansion and rerank toggles.
- **Resume note:** State update: `phase=04`, `plan=04-02`, `task=2`, `status=implemented`; service runners now honor request-scoped expand/rerank toggles and preserve baseline behavior when `runtime_config` is absent.
