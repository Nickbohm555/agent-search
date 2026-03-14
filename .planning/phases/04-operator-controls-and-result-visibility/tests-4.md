---
status: completed
phase: "04 - operator-controls-and-result-visibility"
source:
  - 04-01-SUMMARY.md
  - 04-02-SUMMARY.md
  - 04-03-SUMMARY.md
started: "2026-03-13"
updated: "2026-03-14"
---

## Current Test

Phase 4 UAT coverage for operator controls and result visibility, derived from delivered outcomes in the phase summaries. Tests 1 through 3 are now recorded as passing.

## Information Needed from the Summary

- what_changed:
  - Added optional top-level `runtime_config` on run requests, including nested rerank and query-expansion controls.
  - Wired router and SDK sync/async paths so runtime config is forwarded without breaking legacy request behavior.
  - Applied per-run runtime behavior changes so query expansion and rerank can be disabled per run without mutating defaults.
  - Added frontend toggles for rerank and query expansion that serialize to canonical `runtime_config` payload fields.
  - Preserved sub-answer visibility by accepting both legacy `sub_qa` and additive `sub_answers` in streamed and terminal responses.
- files_changed:
  - src/backend/schemas/agent.py
  - src/backend/routers/agent.py
  - src/backend/agent_search/public_api.py
  - src/backend/services/agent_service.py
  - src/backend/tests/api/test_agent_run.py
  - src/backend/tests/sdk/test_public_api.py
  - src/backend/tests/sdk/test_public_api_async.py
  - src/backend/tests/sdk/test_runtime_config.py
  - src/backend/tests/services/test_agent_service.py
  - src/frontend/src/App.tsx
  - src/frontend/src/App.test.tsx
  - src/frontend/src/utils/api.ts
- code_areas:
  - API request/response schema for run start.
  - Router-to-SDK config forwarding and normalization.
  - Runtime expand/rerank execution path and effective config resolution.
  - Frontend run-start control state and request payload mapping.
  - Frontend SSE/final result sub-answer normalization and rendering.
- testing_notes:
  - Backend targeted tests for this phase passed in plan-scoped selectors.
  - Full backend service suite has unrelated failures outside changed operator-control paths.
  - Frontend phase-focused tests passed for control payload and sub-answer rendering continuity.

## Tests

1. **UAT-4.1 Optional runtime config is additive and backward compatible**
   - Given a user starts a run without providing `runtime_config`
   - When the run request is submitted through the API
   - Then the run is accepted and behaves like legacy/default runs (no required new fields, no contract break).
   - result: Pass on 2026-03-14. `docker compose exec backend uv run pytest tests/api/test_agent_run.py::test_post_run_accepts_additive_runtime_config_payload_without_breaking_legacy_forwarding tests/api/test_agent_run.py::test_post_run_async_accepts_additive_runtime_config_payload_without_breaking_legacy_forwarding tests/sdk/test_public_api.py::test_advanced_rag_preserves_omitted_controls_and_hitl_default_off tests/sdk/test_public_api_async.py::test_run_async_preserves_omitted_controls_and_hitl_default_off` passed, confirming `runtime_config` remains additive on sync and async API paths while omitted config still preserves legacy/default payload behavior in sync and async SDK flows.

2. **UAT-4.2 Per-run query expansion control affects only that run**
   - Given two consecutive runs with the same query
   - When run A sets `runtime_config.query_expansion.enabled=false` and run B omits `runtime_config`
   - Then run A uses disabled expansion behavior, and run B returns to default behavior (no cross-run mutation).
   - result: Pass on 2026-03-14. `docker compose exec backend uv run pytest tests/services/test_agent_service.py::test_run_sequential_graph_runner_disables_query_expansion_per_run_without_mutating_defaults` passed, confirming a run with `query_expansion.enabled=false` skips expand-node execution and searches only the original sub-question, while the immediately following default run restores expand-node behavior and expanded query fanout without cross-run mutation.

3. **UAT-4.3 Per-run rerank control affects only that run**
   - Given two consecutive runs with the same query
   - When run A sets `runtime_config.rerank.enabled=false` and run B omits `runtime_config`
   - Then run A skips rerank behavior, and run B uses default rerank behavior (global defaults unchanged).
   - result: Pass on 2026-03-14. `docker compose exec backend uv run pytest tests/services/test_agent_service.py::test_run_parallel_graph_runner_disables_rerank_per_run_without_mutating_defaults` passed, confirming a run with `rerank.enabled=false` bypasses rerank and carries search results directly into the answer path, while the immediately following default run re-enables rerank behavior without mutating the global reranker defaults.

4. **UAT-4.4 Frontend controls map to canonical backend runtime config**
   - Given the operator opens the frontend run form
   - When rerank and query expansion toggles are changed before submitting
   - Then the `/api/agents/run-async` request payload includes only canonical backend fields under `runtime_config` (`rerank.enabled`, `query_expansion.enabled`) rather than UI-specific names.

5. **UAT-4.5 Sub-answer visibility remains stable across response shapes**
   - Given a run emits streamed lifecycle updates and final output with sub-answer data
   - When backend payloads provide either legacy `sub_qa` or additive `sub_answers`
   - Then the frontend continues to render sub-answers in the run experience without regression.

## Summary

Phase 4 delivered run-scoped retrieval controls (query expansion and rerank) that are configurable through API, SDK, and frontend surfaces, while maintaining backward compatibility and preserving sub-answer visibility in streamed and final outputs. UAT-4.1 through UAT-4.3 passed on 2026-03-14. The tests above validate observable user-facing outcomes rather than internal implementation details.

## Gaps

[
  "UAT-4.1 through UAT-4.3 recorded as passing on 2026-03-14; UAT-4.4 and UAT-4.5 remain to be executed."
]
