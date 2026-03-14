---
phase: "06"
plan: "06-02"
subsystem: "sdk-release-hardening-and-pypi-publication"
tags:
  - sdk
  - release
  - pypi
  - github-actions
  - packaging
requires:
  - REL-04
provides:
  - REL-04
affects:
  - sdk/core/pyproject.toml
  - scripts/release_sdk.sh
  - .github/workflows/release-sdk.yml
tech-stack:
  added: []
  patterns:
    - "The release version is declared once in `sdk/core/pyproject.toml`, and `scripts/release_sdk.sh` rejects any `RELEASE_TAG` that does not match the package metadata before publish work can proceed."
    - "The GitHub Actions release workflow builds and validates artifacts once, uploads them, and publishes only the downloaded validated distributions through Trusted Publishing."
    - "Installability proof is captured outside the publish workflow through a clean virtualenv install/import check against the released PyPI artifact."
key-files:
  created:
    - .planning/phases/06-sdk-contract-parity-and-pypi-release/06-02-SUMMARY.md
  modified:
    - sdk/core/pyproject.toml
    - .github/workflows/release-sdk.yml
key-decisions:
  - "Cut `agent-search-core` release `1.0.3` as the parity-aligned package version for public distribution."
  - "Keep GitHub OIDC Trusted Publishing as the only CI publish path instead of adding alternate upload flows."
  - "Require artifact validation before upload and publish the exact uploaded artifacts to avoid rebuild drift."
duration: "00:08:41"
completed: "2026-03-13"
---
# Phase 6 Plan 02: SDK Contract Parity and PyPI Release Summary

`agent-search-core` version `1.0.3` was cut, the release pipeline was hardened around build-once/publish-once semantics, and the published package was verified from a clean virtualenv install/import flow.

## Outcome

Plan `06-02` completed the REL-04 release-hardening work for `agent-search-core`. The package metadata now declares version `1.0.3`, and the local release script remains the canonical guard for release execution by deriving the expected `agent-search-core-v<version>` tag from `sdk/core/pyproject.toml` and rejecting mismatches before any upload path is available. The GitHub Actions release workflow was then aligned so build and validation happen in a dedicated job, the validated distributions are uploaded as artifacts, and PyPI publication downloads and publishes those exact artifacts through Trusted Publishing rather than rebuilding during publish.

The plan also produced consumer-facing release evidence: `agent-search-core==1.0.3` was installed from PyPI into a fresh Python 3.11 virtual environment and imported successfully, confirming the released artifact is installable outside the repository environment.

## Commit Traceability

- `06-02-task1` (`731a7d8`): bumped `agent-search-core` to `1.0.3` in [sdk/core/pyproject.toml](/Users/nickbohm/Desktop/Tinkering/agent-search/sdk/core/pyproject.toml) and kept release-tag validation centered on the declared package version.
- `06-02-task2` (`ceec7dd`): updated [.github/workflows/release-sdk.yml](/Users/nickbohm/Desktop/Tinkering/agent-search/.github/workflows/release-sdk.yml) so CI builds and validates once, uploads the resulting distributions, and publishes only the downloaded validated artifacts with OIDC Trusted Publishing.
- `06-02-task3` (`782455f`): captured clean-environment install/import proof for the newly published `1.0.3` package and recorded completion state for the release verification step.

## Verification

- `./scripts/release_sdk.sh` -> passed for local build/check preflight.
- `RELEASE_TAG=agent-search-core-v0.0.0 ./scripts/release_sdk.sh` -> failed with the expected tag/version mismatch guard.
- `rg -n "id-token: write|upload-artifact|download-artifact|gh-action-pypi-publish|Build and validate SDK artifacts" .github/workflows/release-sdk.yml` -> confirmed build-before-publish and artifact handoff semantics.
- `python3 -m venv /tmp/agent-search-core-release-check && source /tmp/agent-search-core-release-check/bin/activate && pip install --upgrade pip && pip install --index-url https://pypi.org/simple agent-search-core==1.0.3 && python -c "import agent_search; print(agent_search.__file__)"` -> passed.

## Success Criteria Check

- The release candidate version is explicitly declared and tied to strict release-tag validation before publish.
- CI uses Trusted Publishing to publish validated artifacts only, preserving build-once/publish-once behavior.
- The published `agent-search-core==1.0.3` artifact installs and imports successfully in a clean consumer environment.

## Deviations

- The plan executed as written.
- Summary duration was inferred from the `06-02-task1` to `06-02-task3` commit window because `$DURATION` and `$PLAN_END_TIME` were not populated in the shell environment.
