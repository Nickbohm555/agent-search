# STATE: Agent Search HITL + Prompt Customization Milestone

## Project Reference

- **Core value:** Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.
- **Current milestone roadmap:** `.planning/ROADMAP.md`
- **Current focus:** Phase 6 - SDK Contract Parity and PyPI Release

## Current Position

- **Current phase:** 6
- **Current plan:** 06-02
- **Status:** Phase 6 Plan 06-02 Task 2 implemented; Plan 06-02 Task 3 is next
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
- Start Phase 6 Plan 06-02 Task 3.
- Decide whether Phase 6 can be marked complete after Plans 06-02 and 06-03 finish.

### Blockers
- None currently.

## Session Continuity

- **Next command:** Implement Section 73 in `IMPLEMENTATION_PLAN.md`
- **Why next:** Plan 06-02 Task 2 is complete, so the dependency-ordered follow-up is Phase 6 Plan 06-02 Task 3 for post-publish installability proof.
- **Resume note:** State update: `phase=06`, `plan=06-02`, `task=2`, `status=implemented`; `.github/workflows/release-sdk.yml` now accepts an explicit manual `release_tag`, keeps branch-based dry runs ungated, uploads validated build artifacts once, and only allows CI publish from downloaded artifacts when a tag or manual release tag is present.
