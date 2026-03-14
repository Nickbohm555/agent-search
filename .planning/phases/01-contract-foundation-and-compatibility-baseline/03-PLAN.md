---
phase: 01-contract-foundation-and-compatibility-baseline
plan: 03
type: execute
wave: 2
depends_on:
  - "01-01"
files_modified:
  - src/backend/services/agent_service.py
  - src/frontend/src/utils/api.ts
  - src/backend/tests/services/test_agent_service.py
  - src/backend/tests/contracts/test_public_contracts.py
autonomous: true
must_haves:
  truths:
    - "Runtime responses expose additive sub_answers while preserving sub_qa and existing required response fields."
    - "Frontend/runtime response validation accepts additive fields without breaking legacy behavior."
    - "Public contract tests lock compatibility for additive response evolution."
  artifacts:
    - path: "src/backend/services/agent_service.py"
      provides: "Response mapper emitting both sub_qa and additive sub_answers."
    - path: "src/frontend/src/utils/api.ts"
      provides: "Client validators/types tolerant of additive sub_answers field."
    - path: "src/backend/tests/contracts/test_public_contracts.py"
      provides: "Contract assertions for additive response compatibility."
  key_links:
    - from: "map_graph_state_to_runtime_response"
      to: "RuntimeAgentRunResponse"
      via: "sub_qa copied + sub_answers additive alias"
      pattern: "RuntimeAgentRunResponse\\("
    - from: "frontend validateRuntimeAgentRunResponse"
      to: "API response payload"
      via: "non-breaking validator acceptance"
      pattern: "validateRuntimeAgentRunResponse"
---

<objective>
Finalize additive response compatibility by emitting and validating `sub_answers` across backend response mapping and frontend contract guards without breaking legacy fields.

Purpose: Complete REL-01 safely so consumers can adopt new field(s) incrementally.
Output: Backend response alias wiring + client compatibility updates + contract-focused tests.
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
@src/backend/services/agent_service.py
@src/frontend/src/utils/api.ts
@src/backend/tests/services/test_agent_service.py
@src/backend/tests/contracts/test_public_contracts.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Emit additive sub_answers from runtime response mapper</name>
  <files>src/backend/services/agent_service.py</files>
  <action>Update response mapping to include additive `sub_answers` as compatibility alias of current `sub_qa` data while preserving all existing required fields and semantics (`output`, `final_citations`, `main_question`). Do not rename or remove `sub_qa` in this phase.</action>
  <verify>Run `docker compose exec backend uv run pytest src/backend/tests/services/test_agent_service.py -k "runtime response or map_graph_state"`.</verify>
  <done>Mapped runtime responses include both `sub_qa` and `sub_answers` with equivalent content and no regression to existing fields.</done>
</task>

<task type="auto">
  <name>Task 2: Keep frontend runtime validators compatibility-safe</name>
  <files>src/frontend/src/utils/api.ts</files>
  <action>Extend frontend API types/validators to accept additive `sub_answers` while preserving current `sub_qa`-based behavior. Ensure validation remains permissive for old responses that do not include `sub_answers` and does not require immediate UI usage change in this phase.</action>
  <verify>Run `docker compose exec frontend npm run typecheck` and `docker compose exec frontend npm run build`.</verify>
  <done>Frontend compile/type checks pass and runtime response guards accept both old and additive response shapes.</done>
</task>

<task type="auto">
  <name>Task 3: Add compatibility contract tests for additive response fields</name>
  <files>src/backend/tests/services/test_agent_service.py, src/backend/tests/contracts/test_public_contracts.py</files>
  <action>Add assertions that `sub_answers` is additive and does not break existing contract guarantees. Include checks that required fields remain unchanged and that old-client assumptions (`sub_qa` presence) still hold.</action>
  <verify>Run `docker compose exec backend uv run pytest src/backend/tests/services/test_agent_service.py src/backend/tests/contracts/test_public_contracts.py`.</verify>
  <done>Contract tests enforce REL-01 and fail on any breaking removal/rename of pre-existing fields.</done>
</task>

</tasks>

<verification>
1. `docker compose exec backend uv run pytest src/backend/tests/services/test_agent_service.py src/backend/tests/contracts/test_public_contracts.py`
2. `docker compose exec frontend npm run typecheck`
3. `docker compose exec frontend npm run build`
</verification>

<success_criteria>
- Runtime responses include additive `sub_answers` with no breaking schema changes.
- Frontend validators tolerate additive response evolution and legacy payloads.
- Contract tests lock compatibility to prevent future regressions.
</success_criteria>

<output>
After completion, create `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-03-SUMMARY.md`
</output>
