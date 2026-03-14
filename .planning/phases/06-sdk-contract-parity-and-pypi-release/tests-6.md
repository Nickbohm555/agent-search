---
status: ready
phase: "06-sdk-contract-parity-and-pypi-release"
source:
  - 06-01-SUMMARY.md
  - 06-02-SUMMARY.md
  - 06-03-SUMMARY.md
started: "2026-03-13"
updated: "2026-03-13"
---

## Current Test

Generate UAT coverage for Phase 6 outcomes spanning SDK/backend contract parity, release hardening, and adoption documentation for `agent-search-core==1.0.3`.

## Information Needed from the Summary

- what_changed:
  - Backend request and response contract now accepts additive runtime controls (`runtime_config`, `custom_prompts`, nested HITL controls) while preserving compatibility behavior.
  - Response serialization now includes additive `sub_answers` while keeping legacy `sub_qa`.
  - `openapi.json` and generated Python SDK models were refreshed from backend schema source of truth.
  - Release process hardened around version/tag parity, build-once/publish-once artifact flow, and Trusted Publishing.
  - Documentation updated so root README routes users to `1.0.3` release guidance and migration compatibility expectations.
- files_changed:
  - `src/backend/schemas/agent.py`
  - `src/backend/routers/agent.py`
  - `src/backend/agent_search/config.py`
  - `sdk/core/src/schemas/agent.py`
  - `sdk/core/src/agent_search/config.py`
  - `openapi.json`
  - `sdk/python/openapi_client/models/runtime_agent_run_request.py`
  - `sdk/python/openapi_client/models/runtime_agent_run_response.py`
  - `src/backend/tests/api/test_agent_run.py`
  - `src/backend/tests/sdk/test_runtime_config.py`
  - `sdk/core/pyproject.toml`
  - `.github/workflows/release-sdk.yml`
  - `docs/releases/1.0.3-sdk-contract-parity.md`
  - `sdk/core/README.md`
  - `sdk/python/README.md`
  - `README.md`
- code_areas:
  - Runtime agent request/response schemas and router contract handling.
  - Runtime config defaults and alias compatibility path.
  - OpenAPI generation and generated SDK model parity.
  - SDK release automation and CI publish workflow.
  - End-user migration and release documentation.
- testing_notes:
  - Summary indicates a known docs traceability deviation: migration-guide change existed in workspace but was not captured in a `06-03-task*` commit.
  - Observable validation should prioritize behavior and shipped artifacts rather than commit metadata.
  - OpenAPI drift and release-tag mismatch are release-blocking gates and should be treated as fail-fast checks.

## Tests

### Test 1: Runtime API accepts canonical controls and preserves compatibility response fields
- Type: UAT API behavior
- Preconditions:
  - Services running with Phase 6 backend changes.
- Steps:
  - Submit an agent run request that includes canonical additive controls (`runtime_config`, `custom_prompts`, HITL control fields).
  - Poll until run completion and fetch run result payload.
  - Inspect response payload for both additive and compatibility fields.
- Expected Results:
  - Request is accepted without schema errors.
  - Response includes additive `sub_answers`.
  - Response still provides legacy-compatible `sub_qa` behavior for migration safety.

### Test 2: OpenAPI and generated SDK artifacts stay in backend-contract parity
- Type: UAT contract artifact parity
- Preconditions:
  - Workspace has committed `openapi.json` and generated SDK model files from Phase 6.
- Steps:
  - Run `./scripts/validate_openapi.sh`.
  - Regenerate OpenAPI/SDK artifacts using repository generation flow.
  - Compare regenerated output with committed files.
- Expected Results:
  - Validation script passes.
  - No contract drift is detected between backend schema output and committed `openapi.json`.
  - Generated Python SDK request/response models remain unchanged after regeneration.

### Test 3: Release guard blocks mismatched release tag before publish
- Type: UAT release safety guard
- Preconditions:
  - `sdk/core/pyproject.toml` version is set to the Phase 6 release version.
- Steps:
  - Execute `./scripts/release_sdk.sh` with matching release tag convention.
  - Execute `RELEASE_TAG=agent-search-core-v0.0.0 ./scripts/release_sdk.sh`.
- Expected Results:
  - Matching invocation completes local release preflight checks.
  - Mismatched invocation fails with explicit tag/version mismatch guard.
  - No publish step is reachable when tag and package version do not align.

### Test 4: CI workflow publishes only validated uploaded artifacts
- Type: UAT CI release workflow behavior
- Preconditions:
  - Access to `.github/workflows/release-sdk.yml`.
- Steps:
  - Inspect workflow for a build-and-validate stage that uploads artifacts.
  - Inspect publish stage for artifact download and PyPI publish action usage.
  - Confirm publish stage does not rebuild distributions.
- Expected Results:
  - Workflow contains upload/download artifact handoff.
  - Publish stage uses Trusted Publishing (`id-token: write` + PyPI publish action) against downloaded artifacts.
  - Build-once/publish-once semantics are enforced by workflow structure.

### Test 5: Public release docs provide a complete 1.0.3 adoption path
- Type: UAT documentation usability
- Preconditions:
  - Documentation files from Phase 6 are present in workspace.
- Steps:
  - Start from root `README.md` and follow links to Phase 6 release notes and migration guidance.
  - Verify docs use canonical names (`runtime_config`, `custom_prompts`, `sub_answers`) and explicitly mention compatibility paths (`sub_qa`, aliases).
  - Verify docs call out default-off behavior for controls/HITL unless explicitly enabled.
- Expected Results:
  - A user can navigate from root README to release and migration guidance without dead links.
  - Canonical contract names and compatibility-safe defaults are consistently documented.
  - Documentation supports adoption of `agent-search-core==1.0.3` with clear install and behavior expectations.

## Summary

Phase 6 test coverage now validates five observable outcomes: runtime contract compatibility, OpenAPI/SDK parity, release-tag safety gating, CI artifact publish integrity, and end-user documentation adoption flow for `1.0.3`.

## Gaps

[]
