# STATE: Agent Search HITL + Prompt Customization Milestone

## Project Reference

- **Core value:** Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.
- **Current milestone roadmap:** `.planning/ROADMAP.md`
- **Current focus:** Phase 4 - Operator Controls and Result Visibility

## Current Position

- **Current phase:** 4
- **Current plan:** 04-03
- **Status:** Phase 4 Plan 04-02 summary implemented; Phase 4 Plan 04-03 Task 1 queued
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
- Continue Phase 4 with Plan 04-03 Task 1.
- Preserve the independent frontend rerank/query-expansion control mapping onto canonical `runtime_config` fields.
- Keep using git-evidenced summaries before advancing plans.

### Blockers
- None currently.

## Session Continuity

- **Next command:** Implement Section 46 in `IMPLEMENTATION_PLAN.md`
- **Why next:** Phase 4 Plan 04-02 is summarized, and the next dependency-ordered work item is the frontend control serialization task in Section 46.
- **Resume note:** State update: `phase=04`, `plan=04-02`, `task=summary`, `status=implemented`; summary-time verification passed for `tests/sdk/test_runtime_config.py` and the scoped `test_agent_service.py -k "expand or rerank or runtime_config"` selectors, while the broader service suite still has unrelated failures.
