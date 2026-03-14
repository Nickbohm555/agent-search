# STATE: Agent Search HITL + Prompt Customization Milestone

## Project Reference

- **Core value:** Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.
- **Current milestone roadmap:** `.planning/ROADMAP.md`
- **Current focus:** Phase 6 - SDK Contract Parity and PyPI Release

## Current Position

- **Current phase:** 6
- **Current plan:** 06-02
- **Status:** Phase 6 Plan 06-02 Task 1 implemented; Plan 06-02 Task 2 is next
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
- Start Phase 6 Plan 06-02 Task 2.
- Decide whether Phase 6 can be marked complete after Plans 06-02 and 06-03 finish.

### Blockers
- None currently.

## Session Continuity

- **Next command:** Implement Section 72 in `IMPLEMENTATION_PLAN.md`
- **Why next:** Plan 06-02 Task 1 is complete, so the dependency-ordered follow-up is Phase 6 Plan 06-02 Task 2 for Trusted Publishing build/publish artifact flow hardening.
- **Resume note:** State update: `phase=06`, `plan=06-02`, `task=1`, `status=implemented`; `agent-search-core` is bumped to `1.0.3`, `scripts/release_sdk.sh` now verifies dist filenames and enforces tag alignment before publish, and Phase 6 remains open for workflow hardening and installability proof.
