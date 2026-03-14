# STATE: Agent Search HITL + Prompt Customization Milestone

## Project Reference

- **Core value:** Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.
- **Current milestone roadmap:** `.planning/ROADMAP.md`
- **Current focus:** Phase 6 - SDK Contract Parity and PyPI Release

## Current Position

- **Current phase:** 6
- **Current plan:** 06-01
- **Status:** Phase 5 completed via Plan 05-05 summary; Phase 6 Plan 06-01 is next
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
- Start Phase 6 Plan 06-01 Task 1.
- Lock SDK contract parity for HITL, controls, prompt fields, and additive `sub_answers`.

### Blockers
- None currently.

## Session Continuity

- **Next command:** Implement Section 67 in `IMPLEMENTATION_PLAN.md`
- **Why next:** Phase 5 is complete, so the next dependency-ordered work item is Plan 06-01 Task 1 for SDK/backend contract parity before release.
- **Resume note:** State update: `phase=05`, `plan=05-05`, `task=summary`, `status=implemented`; prompt customization now has contract, docs, runtime wiring, and SDK precedence coverage, and the next target is Phase 6 Plan 06-01 Task 1.
