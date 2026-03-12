---
phase: 05-major-release-and-migration-documentation
plan: 01
subsystem: release-documentation
tags: [release, semver, migration, docs, sdk]
requires:
  - 04-03-SUMMARY.md
provides:
  - a SemVer-major `1.0.0` package declaration for `agent-search-core`
  - canonical LangGraph migration release notes with breaking-change and checklist guidance
  - a root README entrypoint that links integrators directly to release and migration documentation
affects: [sdk-packaging, release-readiness, docs, repository-entrypoints, phase-05]
tech-stack:
  added: []
  patterns:
    - major-release work is documented as a package contract plus migration communication, not runtime feature churn
    - release notes link directly to migration and deprecation docs so breaking changes have one discoverable entrypoint
    - top-level repository docs surface release-critical migration links for first-contact adopters
key-files:
  created:
    - .planning/phases/05-major-release-and-migration-documentation/05-01-SUMMARY.md
    - docs/releases/1.0.0-langgraph-migration.md
  modified:
    - sdk/core/pyproject.toml
    - README.md
    - .gitignore
key-decisions:
  - "`agent-search-core` `1.0.0` is the explicit SemVer-major marker for the LangGraph-native runtime."
  - "The release notes are the canonical breaking-change and pre-publish checklist artifact for the migration."
  - "The root README must expose release and migration links immediately instead of requiring users to discover them deeper in the docs tree."
duration: 4m 03s
completed: 2026-03-12
---

# Phase 05 Plan 01: Major Release and Migration Documentation Summary

**Phase 5 now has a publish-ready `1.0.0` release contract for `agent-search-core`, canonical LangGraph migration release notes, and top-level repository links that direct adopters to the required migration material.**

## Performance

- **Duration:** 4m 03s
- **Started:** 2026-03-12T19:50:52-04:00
- **Completed:** 2026-03-12T19:54:55-04:00
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Bumped `sdk/core/pyproject.toml` to `version = "1.0.0"` so the core SDK exposes an explicit SemVer-major release target for the LangGraph migration.
- Authored `docs/releases/1.0.0-langgraph-migration.md` with release scope, breaking changes, migration prerequisites, direct links to the migration guide and deprecation map, and a release-candidate checklist.
- Added a dedicated `1.0.0 Release` section to the root `README.md` so repository visitors can immediately find the release notes, migration guide, and deprecation map.

## Task Commits

Each task was committed atomically:

1. **Task 1: Bump core SDK to major migration version** - `79bbf8e`
2. **Task 2: Author 1.0.0 LangGraph migration release notes** - `bff5cdc`
3. **Task 3: Link major release docs from repository entrypoint** - `c4b3d9d`

## Files Created/Modified

- `sdk/core/pyproject.toml` - Declares the `agent-search-core` major release version as `1.0.0`.
- `docs/releases/1.0.0-langgraph-migration.md` - Defines release scope, migration semantics, deprecations, and the pre-publish checklist.
- `README.md` - Adds the top-level release navigation section for `1.0.0` adopters.
- `.gitignore` - Preserves `docs/releases/**/*.md` as tracked release documentation.

## Decisions Made

- Treated the version bump as a release contract change only and kept runtime implementation out of this plan.
- Made the release notes the canonical home for breaking-change framing and publication gates instead of scattering that guidance across multiple docs.
- Required root-level discoverability so migration-critical material is visible from the first repository landing page.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None.

## User Setup Required

None beyond the existing release verification workflow documented in the release notes checklist.

## Phase Readiness

- Plan `05-01` is complete and leaves Phase 5 ready to continue with migration-guide hardening in `05-02`.

---
*Phase: 05-major-release-and-migration-documentation*
*Completed: 2026-03-12*
