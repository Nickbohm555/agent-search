**Orchestration stack: DeepAgent library only.** No LangGraph or StateGraph — all graph/orchestration is provided by DeepAgent.

- [ ] P0 — Replace scaffolded orchestration with a real DeepAgent runtime for `/api/agents/run` (spec: `specs/orchestration-langgraph.md`).
  Verification requirements:
  - Add/update backend smoke tests that prove the run path executes through the DeepAgent library (not a static projection) from decomposition to synthesis.
  - Validate that one request still returns a single final answer payload and preserves the existing response schema contract in `src/backend/schemas/agent.py`.
  - Validate that execution metadata/state in the response reflects the actual run (step progression and completion), not hardcoded placeholders.

- [ ] P0 — Implement true DeepAgent-based per-subquery execution inside the flow (spec: `specs/orchestration-langgraph.md`).
  Verification requirements:
  - Add/update backend smoke tests that prove each produced subquery is executed via the DeepAgent library (subgraph/agent unit), not a plain loop helper.
  - Validate that each subquery follows exactly one tool path (`internal` or `web`) and that retrieval+validation complete before synthesis consumes that subquery result.
  - Validate that the validation loop per subquery terminates deterministically with either `validated` or `stopped_insufficient`.

- [ ] P1 — Align state projection for downstream consumers with real DeepAgent execution state (spec: `specs/orchestration-langgraph.md`).
  Verification requirements:
  - Add/update backend smoke tests that prove returned `graph_state` can represent per-step progress for decomposition, tool selection, subquery retrieval/validation, and synthesis from real execution.
  - Validate that repeated runs produce independent state timelines (no state leakage across runs).
  - Validate that per-subquery deep-agent progress is observable in state/timeline fields needed by future streaming consumers.

- [x] Completed baseline relevant to this scope — Scaffold pipeline behavior exists and is deterministically covered (decomposition, tool assignment, retrieval, validation, synthesis, and graph-shaped response fields), but runtime execution is still scaffolded rather than true DeepAgent execution.
