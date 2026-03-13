---
status: pending
phase: 03-end-to-end-langgraph-rag-cutover
source:
  - 03-01-SUMMARY.md
  - 03-02-SUMMARY.md
  - 03-03-SUMMARY.md
started: 2026-03-12T00:00:00Z
updated: 2026-03-12T00:00:00Z
---

## Current Test

- number: 1
- name: Sync runtime uses LangGraph path
- expected: A normal sync run returns the production response contract and does not execute legacy orchestration.
- awaiting: user execution

## Information Needed from the Summary

- what_changed: Phase 03 delivered a compiled LangGraph runtime graph, cut over sync and async production execution to that graph, added anti-regression guards against legacy orchestrator usage, and completed containerized validation for API/SDK contract parity.
- files_changed:
  - src/backend/agent_search/runtime/graph/__init__.py
  - src/backend/agent_search/runtime/graph/builder.py
  - src/backend/agent_search/runtime/graph/execution.py
  - src/backend/agent_search/runtime/graph/routes.py
  - src/backend/agent_search/runtime/graph/state.py
  - src/backend/agent_search/runtime/runner.py
  - src/backend/agent_search/runtime/jobs.py
  - src/backend/agent_search/public_api.py
  - src/backend/tests/services/test_agent_service.py
  - src/backend/tests/api/test_agent_run.py
  - src/backend/tests/sdk/test_sdk_run_e2e.py
  - src/backend/tests/sdk/test_sdk_async_e2e.py
  - src/backend/tests/sdk/test_public_api.py
  - src/backend/tests/sdk/test_public_api_async.py
  - src/backend/pyproject.toml
  - src/backend/uv.lock
- code_areas:
  - Runtime graph composition and invocation entrypoint
  - Sync runtime runner delegation path
  - Async jobs execution and lifecycle status behavior
  - Public API contract boundary and fallback removal
  - API and SDK contract regression tests
  - Service anti-regression tests for orchestration path selection
- testing_notes:
  - Test observable outcomes at API and SDK boundaries, not internal node implementation details.
  - Treat any legacy orchestration invocation in normal sync/async production flow as a regression.
  - Validate both contract shape (output, citations, sub_qa, async status) and runtime path selection.
  - Containerized backend verification is the source of cutover-readiness evidence.

## Tests

1. **Sync API contract parity after cutover**
   - expected: Calling the sync run endpoint returns a successful response containing final output text, citations payload, and `sub_qa` contract fields expected by consumers.
   - result: [pending]

2. **Sync production path rejects legacy orchestration fallback**
   - expected: A normal sync run path succeeds without invoking legacy orchestrator code; any fallback attempt is treated as failure/regression.
   - result: [pending]

3. **Async API lifecycle contract remains stable**
   - expected: Creating an async run and polling status shows consistent lifecycle semantics (queued/running/completed or equivalent), and completed payload shape matches expected public contract fields.
   - result: [pending]

4. **Async production path uses compiled graph execution**
   - expected: Async job execution completes through the shared LangGraph runtime path and does not route through legacy imperative orchestration.
   - result: [pending]

5. **SDK sync call contract remains consumer-safe**
   - expected: Sync SDK run returns expected top-level content (answer/final output) plus citations and sub-question artifacts where applicable, with no breaking shape changes.
   - result: [pending]

6. **SDK async call + polling contract remains consumer-safe**
   - expected: Async SDK create/poll flow returns stable status transitions and completion payload compatibility, including fields relied on by downstream clients.
   - result: [pending]

7. **Async cancellation behavior remains intact**
   - expected: Canceling a running async job yields a terminal canceled state with no contract regressions or unexpected runtime errors.
   - result: [pending]

8. **Async resume/checkpoint compatibility remains intact**
   - expected: Resumed/continued async processing preserves thread identity continuity and returns a valid completion payload without requiring legacy default path execution.
   - result: [pending]

9. **Public API no-obsolete-fallback behavior**
   - expected: Public API sync/async entrypoints function normally without the removed obsolete fallback code path, preserving expected outputs and errors.
   - result: [pending]

10. **Containerized backend cutover readiness evidence**
    - expected: Running the targeted backend tests in Docker Compose succeeds for API, SDK, and service regression suites tied to LangGraph cutover parity.
    - result: [pending]

## Summary

- total: 10
- passed: 0
- issues: 0
- pending: 10
- skipped: 0

## Gaps

[]
