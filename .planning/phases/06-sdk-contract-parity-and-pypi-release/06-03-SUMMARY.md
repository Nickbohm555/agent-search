---
phase: "06"
plan: "06-03"
subsystem: "sdk-release-migration-and-adoption-docs"
tags:
  - docs
  - sdk
  - release
  - migration
  - compatibility
requires:
  - REL-05
provides:
  - REL-05
affects:
  - docs/migration-guide.md
  - docs/releases/1.0.3-sdk-contract-parity.md
  - sdk/core/README.md
  - sdk/python/README.md
  - README.md
tech-stack:
  added: []
  patterns:
    - "Canonical contract-adoption guidance is split across a migration guide, release notes, and SDK READMEs so root docs can link consumers into one compatibility-safe path."
    - "Examples document canonical request names (`controls`, `runtime_config`, `custom_prompts`) while explicitly preserving compatibility aliases and legacy `sub_qa` fallback handling."
    - "Top-level release guidance keeps new controls default-off unless explicitly enabled and routes generated-SDK consumers toward typed HITL resume flows."
key-files:
  created:
    - .planning/phases/06-sdk-contract-parity-and-pypi-release/06-03-SUMMARY.md
  modified:
    - docs/releases/1.0.3-sdk-contract-parity.md
    - sdk/core/README.md
    - sdk/python/README.md
    - README.md
key-decisions:
  - "Make the `1.0.3` release notes the top-level entrypoint for Phase 6 adoption and link them directly from the root README."
  - "Document `custom_prompts` and `sub_answers` as canonical while keeping `custom-prompts` and `sub_qa` called out as compatibility-only paths."
  - "Keep migration guidance explicit about default-off controls so documentation cannot be read as implicit feature enablement."
duration: "00:06:16"
completed: "2026-03-13"
---
# Phase 6 Plan 03: SDK Contract Parity and PyPI Release Summary

Phase 6 adoption guidance now points consumers to a single `1.0.3` compatibility story covering runtime controls, HITL, prompt overrides, and additive `sub_answers` handling across root docs and SDK surfaces.

## Outcome

Plan `06-03` completed the REL-05 documentation gate for the Phase 6 release. The repository now includes dedicated `1.0.3` release notes with canonical contract names, install commands, and compatibility guidance for `agent-search-core` and the generated HTTP SDK. Both SDK READMEs were updated with concrete examples for runtime controls, prompt overrides, and additive sub-answer handling, and the root `README.md` now routes users directly to the `1.0.3` release notes and migration guidance while surfacing a concise compatibility checklist that matches the release contract.

## Commit Traceability

- `06-03-task1` (`3f5bc4c`): recorded plan progress for the migration-guide step, but did not capture a tracked documentation diff in git history.
- `06-03-task2` (`40ecc93`): added [docs/releases/1.0.3-sdk-contract-parity.md](/Users/nickbohm/Desktop/Tinkering/agent-search/docs/releases/1.0.3-sdk-contract-parity.md) and updated [sdk/core/README.md](/Users/nickbohm/Desktop/Tinkering/agent-search/sdk/core/README.md) plus [sdk/python/README.md](/Users/nickbohm/Desktop/Tinkering/agent-search/sdk/python/README.md) with release-aligned adoption examples.
- `06-03-task3` (`8d61131`): updated [README.md](/Users/nickbohm/Desktop/Tinkering/agent-search/README.md) to make the migration/release entrypoints and compatibility checklist discoverable from the repository root.

## Verification

- `rg -n "runtime_config|custom_prompts|sub_answers|sub_qa|pip install agent-search-core|release" docs/releases/1.0.3-sdk-contract-parity.md sdk/core/README.md sdk/python/README.md` -> passed during `06-03-task2`.
- `rg -n "migration guide|release notes|agent-search-core|compatibility|default-off" README.md` -> passed during `06-03-task3`.
- Markdown links from `README.md` resolve to existing tracked release artifacts and to the current workspace migration guide at `docs/migration-guide.md`.

## Success Criteria Check

- Root, SDK, and release-note documentation surfaces now use the same canonical contract names for runtime controls, prompt overrides, and additive sub-answer reads.
- Compatibility-safe defaults are stated consistently: controls and HITL stay default-off when omitted, prompt overrides are optional, and `sub_qa` remains a valid fallback during migration.
- Consumers have direct entrypoints from the repository root into release and migration guidance for adopting the `1.0.3` contract surface.

## Deviations

- The plan mostly executed as written, but `06-03-task1` does not contain a tracked git diff for `docs/migration-guide.md`; the migration guide exists in the current workspace and is linked from the shipped docs, but its addition was not captured under a `06-03-task*` commit.
- Summary duration was inferred from the `06-03-task1` to `06-03-task3` commit window because `$DURATION` and `$PLAN_END_TIME` were not populated in the shell environment.
