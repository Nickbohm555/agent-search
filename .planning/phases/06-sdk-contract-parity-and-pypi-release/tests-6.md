---
status: completed
phase: "06-sdk-contract-parity-and-pypi-release"
source:
  - 06-01-SUMMARY.md
  - 06-02-SUMMARY.md
  - 06-03-SUMMARY.md
started: "2026-03-13"
updated: "2026-03-14"
---

## Current Test

All phase 6 validation tests are now recorded. Tests 1-5 cover runtime contract compatibility, OpenAPI and generated SDK parity checks, release-tag safety gating, CI artifact publish integrity, and the public 1.0.3 documentation adoption path.

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
- result: pass - `docker compose exec backend uv run pytest tests/api/test_agent_run.py::test_runtime_agent_run_request_normalizes_release_blocking_controls_to_canonical_shape tests/api/test_agent_run.py::test_post_run_returns_response_shape_from_runtime_agent tests/api/test_agent_run.py::test_runtime_agent_run_response_serializes_additive_sub_answers_alongside_legacy_sub_qa` passed on 2026-03-14.
- reported: canonical additive controls were accepted and normalized, and the runtime response exposed additive `sub_answers` alongside legacy-compatible `sub_qa` with matching payload contents.
- severity: none
- reason: observed behavior matches the Phase 6 compatibility contract for request acceptance and response serialization.
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
- result: fail - `docker compose up -d backend && ./scripts/validate_openapi.sh` failed on 2026-03-14 because the parity gate detected generated SDK drift in `sdk/python/README.md` even though OpenAPI validation and runtime export parity passed; regenerated `runtime_agent_run_request.py` and `runtime_agent_run_response.py` still matched the committed files.
- reported: backend-contract parity is not clean because the committed generated Python SDK bundle diverges from the repository generation flow in `sdk/python/README.md`, while the schema artifact and key generated request/response models remain aligned.
- severity: high
- reason: OpenAPI/SDK parity is a release-blocking gate in Phase 6, and the repository's own validation script currently fails on committed generated artifact drift.
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
- result: pass - `RELEASE_TAG=agent-search-core-v1.0.3 ./scripts/release_sdk.sh` passed on 2026-03-14, building `agent_search_core-1.0.3.tar.gz` and `agent_search_core-1.0.3-py3-none-any.whl`, passing filename checks, wheel-content validation, and `twine check`, then exiting before upload; `RELEASE_TAG=agent-search-core-v0.0.0 ./scripts/release_sdk.sh` failed immediately with `release tag mismatch expected=agent-search-core-v1.0.3 actual=agent-search-core-v0.0.0`.
- reported: the release script enforces exact tag-to-package version parity and blocks the publish path before any upload logic is reachable when the tag does not match `sdk/core/pyproject.toml`.
- severity: none
- reason: observed dry-run and mismatch behavior match the Phase 6 release safety requirement for fail-fast tag validation ahead of publish.
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
- result: pass - inspected `.github/workflows/release-sdk.yml` and `scripts/release_sdk.sh` on 2026-03-14; `build_and_check` runs `./scripts/release_sdk.sh`, uploads `sdk/core/dist/*` as `agent-search-core-dist`, and `publish` only downloads that artifact to `dist` before `pypa/gh-action-pypi-publish@release/v1` publishes `packages-dir: dist`.
- reported: the release workflow enforces build-once/publish-once semantics by validating artifacts before upload, then publishing only the downloaded artifact bundle under Trusted Publishing without any rebuild step in the publish job.
- severity: none
- reason: observed workflow structure matches the Phase 6 requirement that CI publish only validated uploaded artifacts.
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
- result: pass - manual documentation UAT passed on 2026-03-14 after tracing `README.md` to `docs/releases/1.0.3-sdk-contract-parity.md`, `docs/migration-guide.md`, `sdk/core/README.md`, and `sdk/python/README.md`; all links resolved in-repo and the docs consistently documented canonical `controls`, `runtime_config`, `custom_prompts`, additive `sub_answers`, `sub_qa` fallback handling, and default-off controls/HITL behavior.
- reported: the published docs provide a complete adoption path for `agent-search-core==1.0.3`, from the root README through release and migration guidance into both SDK READMEs, without dead links or naming inconsistencies in the documented compatibility surface.
- severity: none
- reason: observed documentation matches the Phase 6 release guidance requirement for navigable, compatibility-safe adoption instructions.
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

Phase 6 test coverage now validates five observable outcomes: runtime contract compatibility, OpenAPI/SDK parity, release-tag safety gating, CI artifact publish integrity, and end-user documentation adoption flow for `1.0.3`. Test 1 passed on 2026-03-14 using the targeted backend API contract tests for canonical control normalization plus additive and legacy response field serialization. Test 2 failed on 2026-03-14 because `./scripts/validate_openapi.sh` detected committed generated SDK drift in `sdk/python/README.md` even though `openapi.json` matched the runtime export and regenerated request/response models remained unchanged. Test 3 passed on 2026-03-14 because the matching `agent-search-core-v1.0.3` dry run completed local build and artifact checks without uploading, while a mismatched `agent-search-core-v0.0.0` tag was rejected before publish logic. Test 4 passed on 2026-03-14 because `.github/workflows/release-sdk.yml` uploads the validated `sdk/core/dist/*` bundle from `build_and_check`, and `publish` only downloads `agent-search-core-dist` to `dist` before invoking `pypa/gh-action-pypi-publish@release/v1` with `packages-dir: dist`, so the publish job never rebuilds artifacts. Test 5 passed on 2026-03-14 after a documentation UAT from `README.md` through the Phase 6 release notes, migration guide, and both SDK READMEs confirmed the 1.0.3 adoption path is navigable, names the canonical contract fields consistently, documents `sub_qa` compatibility fallback for additive `sub_answers`, and states that new controls and HITL remain default-off unless explicitly enabled.

## Gaps

[
  "Phase 6 Test 2 is currently blocked by generated SDK drift in `sdk/python/README.md`, so OpenAPI/SDK artifact parity is not yet clean."
]
