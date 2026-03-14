---
status: completed
phase: "1 - contract-foundation-and-compatibility-baseline"
source:
  - 01-01-SUMMARY.md
  - 01-02-SUMMARY.md
  - 01-03-SUMMARY.md
started: "2026-03-13"
updated: "2026-03-14"
---

## Current Test
Test 5 - Frontend validation accepts legacy-only and additive payloads.

## Information Needed from the Summary
- what_changed:
  - Backend request contracts now accept additive nested `controls` without breaking legacy payloads.
  - Router normalization forwards one shared runtime config shape for both `/run` and `/run-async`.
  - SDK sync/async entrypoints now map to normalized runtime payloads and preserve omitted-control defaults.
  - Async jobs persist normalized request payloads and resume with full control continuity.
  - Runtime responses include additive `sub_answers` alias while preserving legacy `sub_qa` and required fields.
  - Frontend API validators accept legacy-only responses and additive responses with optional `sub_answers`.
- files_changed:
  - src/backend/schemas/agent.py
  - src/backend/schemas/__init__.py
  - src/backend/routers/agent.py
  - src/backend/agent_search/public_api.py
  - src/backend/agent_search/runtime/jobs.py
  - src/backend/services/agent_service.py
  - src/frontend/src/utils/api.ts
  - src/backend/tests/api/test_agent_run.py
  - src/backend/tests/sdk/test_public_api.py
  - src/backend/tests/sdk/test_public_api_async.py
  - src/backend/tests/sdk/test_runtime_config.py
  - src/backend/tests/services/test_agent_service.py
  - src/backend/tests/contracts/test_public_contracts.py
- code_areas:
  - Backend API contract schemas and run router request mapping.
  - Backend SDK/public API request normalization for sync and async run calls.
  - Async runtime job persistence and resume request reconstruction.
  - Runtime response mapping from graph state to API payload.
  - Frontend runtime response type guards/validators.
  - Contract and regression test suites for compatibility and additive fields.
- testing_notes:
  - Container test path differences were observed (`tests/...` valid in container; some `src/backend/tests/...` paths invalid there).
  - Contract-compatibility tests were green even when broader service-runtime suites had unrelated failures.
  - Verification must focus on observable compatibility outcomes, not broad unrelated runtime failures.

## Tests (at least 3 tests)
1. **Legacy request compatibility remains intact**
   - **Given** a client sends a run request without any new `controls` fields
   - **When** the request is submitted to both sync and async run entrypoints
   - **Then** both requests are accepted, run successfully, and preserve legacy payload behavior (no new-field requirement introduced).
   - result: pass - `docker compose exec backend uv run pytest tests/api/test_agent_run.py::test_runtime_agent_run_request_keeps_legacy_payload_compatible_when_custom_prompts_omitted` passed, and omitted-controls compatibility also passed in `tests/sdk/test_public_api.py::test_advanced_rag_preserves_omitted_controls_and_hitl_default_off` and `tests/sdk/test_public_api_async.py::test_run_async_preserves_omitted_controls_and_hitl_default_off`.
   - reported: 2026-03-14
   - severity: none
   - reason: Legacy payloads without additive controls still validate as query-only requests and both sync and async SDK entrypoints preserve omitted-control defaults instead of requiring new fields.

2. **Additive controls propagate consistently in sync and async flows**
   - **Given** a client sends explicit controls (for example: rerank/query expansion/HITL toggles and thread context)
   - **When** the request is executed via sync run and async run
   - **Then** both paths produce equivalent normalized runtime config behavior, confirming one shared control-shape contract.
   - result: pass - `docker compose exec backend uv run pytest tests/sdk/test_public_api.py::test_advanced_rag_propagates_explicit_controls_without_mutation tests/sdk/test_public_api.py::test_advanced_rag_propagates_runtime_config_without_breaking_legacy_control_shape tests/sdk/test_public_api_async.py::test_run_async_propagates_explicit_controls_to_job_payload tests/sdk/test_public_api_async.py::test_run_async_propagates_runtime_config_to_job_payload_without_breaking_legacy_control_shape` passed.
   - reported: 2026-03-14
   - severity: none
   - reason: Sync `advanced_rag` and async `run_async` both normalized explicit thread and additive control inputs into the same payload shapes, including the nested `runtime_config` compatibility path, confirming one shared contract across both flows.

3. **Async resume preserves full normalized controls**
   - **Given** an async job is created with explicit additive controls
   - **When** the job is resumed from persisted state
   - **Then** resume reconstruction uses the stored normalized request payload and retains the full control envelope (not query/thread-only fallback behavior).
   - result: pass - `docker compose exec backend uv run pytest tests/sdk/test_public_api_async.py::test_resume_run_reconstructs_full_request_payload` passed.
   - reported: 2026-03-14
   - severity: none
   - reason: Resume reconstruction validated the persisted normalized request payload, including `controls.rerank`, `controls.query_expansion`, and `controls.hitl`, before re-entering the checkpointed async runtime path.

4. **Response contract stays backward compatible with additive field**
   - **Given** a runtime response is generated for existing clients
   - **When** the response is returned by backend mapping
   - **Then** required legacy fields (`sub_qa`, `output`, citations and other required contract fields) remain present and unchanged, while additive `sub_answers` is also available.
   - result: pass - `docker compose exec backend uv run pytest tests/contracts/test_public_contracts.py::test_runtime_agent_run_response_contract_keeps_legacy_fields_and_additive_sub_answers tests/services/test_agent_service.py::test_map_graph_state_to_runtime_response_is_backward_compatible tests/api/test_agent_run.py::test_runtime_agent_run_response_serializes_additive_sub_answers_alongside_legacy_sub_qa` passed.
   - reported: 2026-03-14
   - severity: none
   - reason: The contract schema still requires only `output`, validates legacy payloads with `sub_qa`, accepts additive `sub_answers`, the graph-state mapper emits both fields as distinct copies, and API serialization preserves both fields without changing the legacy response shape.

5. **Frontend validation accepts legacy-only and additive payloads**
   - **Given** one response payload that contains only legacy fields and another that also includes `sub_answers`
   - **When** both payloads are validated by frontend API guards
   - **Then** both payloads pass validation, and strict checks apply only when additive `sub_answers` is present.

## Summary
Tests 1-4 passed on 2026-03-14. Legacy payloads without additive controls still validate, explicit additive controls propagate consistently through both sync and async SDK entrypoints, async resume reconstructs the full normalized request payload instead of falling back to query/thread-only state, and runtime responses preserve the legacy `sub_qa` contract while exposing additive `sub_answers`.

## Gaps
[
  "Test 5 pending: frontend runtime validators still need validation against legacy-only and additive `sub_answers` payloads."
]
