---
phase: 01-contract-foundation-and-compatibility-baseline
plan: 02
type: execute
wave: 2
depends_on:
  - "01-01"
files_modified:
  - src/backend/agent_search/public_api.py
  - src/backend/agent_search/runtime/jobs.py
  - src/backend/tests/sdk/test_public_api.py
  - src/backend/tests/sdk/test_public_api_async.py
autonomous: true
must_haves:
  truths:
    - "Run controls are reflected in runtime config handling, not just accepted at the HTTP edge."
    - "Async start/status/resume paths preserve additive request controls through pause/resume cycles."
    - "When controls are omitted, runtime behavior defaults remain unchanged."
  artifacts:
    - path: "src/backend/agent_search/public_api.py"
      provides: "Config translation from API request payload to RuntimeConfig-compatible dict for sync and async entrypoints."
    - path: "src/backend/agent_search/runtime/jobs.py"
      provides: "Job persistence and resume reconstruction that preserves additive request controls."
    - path: "src/backend/tests/sdk/test_public_api_async.py"
      provides: "Regression tests for async config propagation and resume continuity."
  key_links:
    - from: "routers agent config dict"
      to: "public_api RuntimeConfig.from_dict"
      via: "advanced_rag/run_async config parameter"
      pattern: "RuntimeConfig\\.from_dict\\(config\\)"
    - from: "start_agent_run_job payload"
      to: "resume_agent_run_job payload reconstruction"
      via: "stored normalized request payload"
      pattern: "RuntimeAgentRunRequest\\("
---

<objective>
Thread additive control fields through SDK/public runtime entrypoints and async job lifecycle so sync, async, and resume flows all honor the same request contract.

Purpose: Remove the highest Phase 1 risk where new fields are accepted but silently dropped in async/retry paths.
Output: Runtime config propagation and async payload persistence/resume reconstruction with regression tests.
</objective>

<execution_context>
@~/.cursor/get-shit-done/workflows/execute-plan.md
@~/.cursor/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md
@src/backend/agent_search/public_api.py
@src/backend/agent_search/runtime/jobs.py
@src/backend/tests/sdk/test_public_api.py
@src/backend/tests/sdk/test_public_api_async.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Normalize control-to-runtime config mapping in public API</name>
  <files>src/backend/agent_search/public_api.py</files>
  <action>Introduce explicit config translation that carries rerank/query-expansion/HITL control fields from request-derived config into `RuntimeConfig.from_dict` inputs for `advanced_rag` and `run_async`. Preserve existing behavior for omitted controls by emitting only compatibility-safe defaults (no implicit enablement of HITL).</action>
  <verify>Run `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api.py src/backend/tests/sdk/test_runtime_config.py`.</verify>
  <done>Public API logs and tests show controls are parsed and reflected in runtime config handling; legacy config inputs still resolve to prior defaults.</done>
</task>

<task type="auto">
  <name>Task 2: Persist additive request payload through async job and resume</name>
  <files>src/backend/agent_search/runtime/jobs.py</files>
  <action>Persist normalized request payload (not only query/thread_id) in job status metadata and/or in-memory job state, then rebuild `RuntimeAgentRunRequest` from that persisted payload during `resume_agent_run_job`. Ensure pause/resume does not strip rerank/query-expansion/HITL fields and that resume still rejects invalid state transitions as today.</action>
  <verify>Run `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api_async.py -k "run_async or resume"`.</verify>
  <done>Resumed async runs use the same effective controls as original submission; omitted controls continue to behave identically to baseline.</done>
</task>

<task type="auto">
  <name>Task 3: Add sync/async control propagation regression tests</name>
  <files>src/backend/tests/sdk/test_public_api.py, src/backend/tests/sdk/test_public_api_async.py</files>
  <action>Add tests that assert control fields survive public API sync path and async start->status->resume lineage without mutation/loss. Include assertions that omitted control fields preserve existing defaults and that HITL remains disabled unless explicitly enabled.</action>
  <verify>Run `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api.py src/backend/tests/sdk/test_public_api_async.py`.</verify>
  <done>SDK-level contract tests fail if any new control fields are dropped, implicitly enabled, or default behavior changes when fields are omitted.</done>
</task>

</tasks>

<verification>
1. `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api.py src/backend/tests/sdk/test_public_api_async.py`
2. `docker compose exec backend uv run pytest src/backend/tests/sdk/test_runtime_config.py`
</verification>

<success_criteria>
- Control fields are reflected in runtime config processing for sync and async runs.
- Resume reconstructs full request controls rather than query/thread-only payload.
- Default behavior for legacy requests remains unchanged.
</success_criteria>

<output>
After completion, create `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-02-SUMMARY.md`
</output>
