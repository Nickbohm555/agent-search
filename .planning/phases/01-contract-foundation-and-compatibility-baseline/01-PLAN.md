---
phase: 01-contract-foundation-and-compatibility-baseline
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/backend/schemas/agent.py
  - src/backend/routers/agent.py
  - src/backend/tests/api/test_agent_run.py
autonomous: true
must_haves:
  truths:
    - "Run endpoints accept additive control fields while still accepting legacy payloads that only include query/thread_id."
    - "HITL remains disabled unless the request explicitly enables it."
    - "Response contract exposes additive sub_answers while preserving existing required fields."
  artifacts:
    - path: "src/backend/schemas/agent.py"
      provides: "Additive request control models and additive response field declarations."
    - path: "src/backend/routers/agent.py"
      provides: "Single mapping function that translates request controls into runtime config dictionary."
    - path: "src/backend/tests/api/test_agent_run.py"
      provides: "Router contract coverage for legacy payloads and additive controls."
  key_links:
    - from: "RuntimeAgentRunRequest.controls"
      to: "router config payload"
      via: "_build_*_config mapping"
      pattern: "config=.*thread_id.*rerank.*query_expansion.*hitl"
    - from: "RuntimeAgentRunResponse.sub_answers"
      to: "existing response shape"
      via: "additive field alongside sub_qa/output/final_citations"
      pattern: "sub_answers"
---

<objective>
Introduce additive API contract fields for per-run controls and additive `sub_answers` response support, while preserving existing request and response compatibility.

Purpose: Establish the Phase 1 compatibility baseline so downstream HITL and control-surface work can be built safely.
Output: Updated schema + router mapping + router-level compatibility tests proving additive behavior.
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
@src/backend/schemas/agent.py
@src/backend/routers/agent.py
@src/backend/tests/api/test_agent_run.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add additive request/response contract fields</name>
  <files>src/backend/schemas/agent.py</files>
  <action>Define optional nested request controls on `RuntimeAgentRunRequest` for rerank/query-expansion/HITL with explicit compatibility-safe defaults (HITL default-off). Add additive `sub_answers` to response models (`RuntimeAgentRunResponse` and async status result shape where needed) without removing or changing existing `sub_qa`, `output`, or other required fields. Keep `thread_id` validation behavior unchanged.</action>
  <verify>Run `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "run or status"` and confirm schema parsing/serialization tests pass.</verify>
  <done>Legacy payloads (`{query}` or `{query,thread_id}`) still validate; new control fields validate when present; response models expose `sub_answers` additively.</done>
</task>

<task type="auto">
  <name>Task 2: Map request controls to runtime config at router boundary</name>
  <files>src/backend/routers/agent.py</files>
  <action>Replace thread-only config builder with a single additive mapper that includes `thread_id` plus nested control sections for rerank/query-expansion/HITL. Reuse this mapper for both `/run` and `/run-async`. Ensure omitted controls produce exactly previous config behavior and explicit HITL values are forwarded deterministically.</action>
  <verify>Run `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "post_run or run_async"` and confirm captured `config` payload assertions pass for legacy and additive cases.</verify>
  <done>Both sync and async endpoints forward the same normalized config shape; omitted controls do not change existing behavior.</done>
</task>

<task type="auto">
  <name>Task 3: Extend router contract tests for additive compatibility</name>
  <files>src/backend/tests/api/test_agent_run.py</files>
  <action>Add/adjust router tests to assert: (1) legacy request remains valid and forwards no extra config, (2) additive control fields are accepted and forwarded, (3) response shape now includes additive `sub_answers` while `sub_qa` remains available. Keep existing assertions for thread_id continuity and error mapping intact.</action>
  <verify>Run `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py`.</verify>
  <done>Router contract tests explicitly enforce CTRL-02/CTRL-04/CTRL-05 and REL-01 baseline behavior at API boundary.</done>
</task>

</tasks>

<verification>
1. `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py`
2. `docker compose exec backend uv run pytest src/backend/tests/contracts/test_public_contracts.py`
</verification>

<success_criteria>
- Legacy clients can POST runs without new fields and still succeed unchanged.
- New control fields are accepted and appear in downstream config forwarding.
- Response includes additive `sub_answers` without removing or altering existing required fields.
</success_criteria>

<output>
After completion, create `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-01-SUMMARY.md`
</output>
