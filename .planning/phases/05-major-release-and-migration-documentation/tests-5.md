---
status: pending
phase: 05-major-release-and-migration-documentation
source:
  - 05-01-SUMMARY.md
  - 05-02-SUMMARY.md
  - 05-03-SUMMARY.md
started: 2026-03-12T00:00:00Z
updated: 2026-03-12T00:00:00Z
---

## Current Test

- number: 1
- name: Core SDK exposes SemVer-major release contract
- expected: `sdk/core/pyproject.toml` declares `version = "1.0.0"` for `agent-search-core`.
- awaiting: user execution

## Information Needed from the Summary

- what_changed:
  - Core SDK package contract was bumped to `1.0.0` for the LangGraph-native major release.
  - Release notes were added and linked from the root README for migration-first discoverability.
  - Deprecation policy was documented as an explicit status/removal matrix in committed docs.
  - SDK docs index gained migration/deprecation callouts for adopters.
  - Canonical OpenAPI and generated SDK references were regenerated to match runtime contracts.
  - Application docs were reframed as migration-complete and LangGraph-first.
  - Health-check example now supports explicit target URL selection and clearer failure output.
- files_changed:
  - `sdk/core/pyproject.toml`
  - `docs/releases/1.0.0-langgraph-migration.md`
  - `README.md`
  - `.gitignore`
  - `docs/deprecation-map.md`
  - `sdk/README.md`
  - `openapi.json`
  - `sdk/python/README.md`
  - `docs/application-documentation.html`
  - `sdk/examples/run_health.py`
- code_areas:
  - Release/versioning contract for published SDK package metadata.
  - Top-level and SDK-level documentation navigation for migration-critical guidance.
  - Deprecation/removal semantics for legacy orchestration surfaces.
  - OpenAPI-driven SDK documentation generation and endpoint/model inventory.
  - LangGraph runtime architecture documentation (state contracts, resume/checkpoint behavior).
  - SDK example execution path and health endpoint connectivity behavior.
- testing_notes:
  - One planned artifact (`docs/migration-guide.md`) is intentionally treated as a traceability gap unless committed; test should confirm that this is documented, not silently assumed shipped.
  - Tests should focus on observable documentation and contract outcomes, not internal implementation details.
  - Health example tests should validate behavior against both default and explicit base URL selection paths.
  - OpenAPI/SDK docs parity should be validated by presence of expected runtime endpoints and run contract fields.

## Tests

1. **Major release contract is visible in package metadata**
   - expected: `sdk/core/pyproject.toml` shows `agent-search-core` at `1.0.0`.
   - result: [pending]

2. **Release notes exist and describe LangGraph migration scope**
   - expected: `docs/releases/1.0.0-langgraph-migration.md` exists and includes breaking changes, migration prerequisites, and release checklist guidance.
   - result: [pending]

3. **Repository entrypoint surfaces release and migration links**
   - expected: `README.md` contains a dedicated `1.0.0 Release` section with links to release notes and migration/deprecation docs.
   - result: [pending]

4. **Deprecation map defines status and removal semantics**
   - expected: `docs/deprecation-map.md` includes explicit support statuses, replacement paths, and earliest removal horizon guidance.
   - result: [pending]

5. **SDK index warns adopters and points to migration/deprecation docs**
   - expected: `sdk/README.md` contains top-level migration/deprecation callouts and advises preferred modern entrypoints.
   - result: [pending]

6. **OpenAPI artifact reflects current runtime contract**
   - expected: `openapi.json` includes runtime endpoints and schema elements for run events/resume flows and `thread_id`-carrying run contracts.
   - result: [pending]

7. **Generated Python SDK reference aligns with OpenAPI inventory**
   - expected: `sdk/python/README.md` lists shipped interfaces/endpoints consistent with current OpenAPI output, including run/events/resume and health-relevant surfaces.
   - result: [pending]

8. **Application docs present migration-complete LangGraph architecture**
   - expected: `docs/application-documentation.html` describes LangGraph-first runtime behavior, canonical state roles, stable `thread_id` handling, and checkpoint-backed resume narrative.
   - result: [pending]

9. **Health-check example supports explicit target and actionable failures**
   - expected: `sdk/examples/run_health.py` accepts explicit base URL override (`--base-url` and/or `AGENT_SEARCH_BASE_URL`) and emits useful failure diagnostics while preserving `/api/health` semantics.
   - result: [pending]

10. **Traceability gap is documented instead of misreported as delivered**
    - expected: summary evidence clearly records that `docs/migration-guide.md` is not treated as shipped/committed plan evidence until traceability is fixed.
    - result: [pending]

## Summary

- total: 10
- passed: 0
- issues: 0
- pending: 10
- skipped: 0

## Gaps

[]
