- [ ] P0 — Replace scaffolded orchestration with a real LangGraph runtime for `/api/agents/run` (spec: `specs/orchestration-langgraph.md`).
  Verification requirements:
  - Add/update backend smoke tests that prove the run path executes through a compiled LangGraph graph instance (not a static projection) from decomposition to synthesis.
  - Validate that one request still returns a single final answer payload and preserves the existing response schema contract in `src/backend/schemas/agent.py`.
  - Validate that graph execution metadata/state in the response reflects the actual run (node progression and completion), not hardcoded placeholders.

- [ ] P0 — Implement true DeepAgent-based per-subquery execution inside the LangGraph flow (spec: `specs/orchestration-langgraph.md`).
  Verification requirements:
  - Add/update backend smoke tests that prove each produced subquery is executed via the deep-agent unit used by the graph (subgraph/agent node), not a plain loop helper.
  - Validate that each subquery follows exactly one tool path (`internal` or `web`) and that retrieval+validation complete before synthesis consumes that subquery result.
  - Validate that the validation loop per subquery terminates deterministically with either `validated` or `stopped_insufficient`.

- [ ] P1 — Align LangGraph state projection for downstream consumers with real deep-agent execution state (spec: `specs/orchestration-langgraph.md`).
  Verification requirements:
  - Add/update backend smoke tests that prove returned `graph_state` can represent per-step progress for decomposition, tool selection, subquery retrieval/validation, and synthesis from real graph execution.
  - Validate that repeated runs produce independent graph-state timelines (no state leakage across runs).
  - Validate that per-subquery deep-agent progress is observable in state/timeline fields needed by future streaming consumers.

- [x] Completed baseline relevant to this scope — Scaffold pipeline behavior exists and is deterministically covered (decomposition, tool assignment, retrieval, validation, synthesis, and graph-shaped response fields), but runtime execution is still scaffolded rather than true LangGraph + DeepAgent execution.
