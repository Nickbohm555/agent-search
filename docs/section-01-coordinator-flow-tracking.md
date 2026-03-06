# Section 1 Architecture: Coordinator flow tracking via `write_todos` and virtual file system

## Purpose
This section ensures the coordinator agent does not lose pipeline state while running a multi-stage question-answering workflow. It does this by forcing explicit plan/state tracking through deep-agents tools (`write_todos`, `read_file`, `write_file`, `edit_file`) backed by a virtual file system state backend.

## Components
- Coordinator factory: `create_coordinator_agent(...)` in `src/backend/agents/coordinator.py`.
- Coordinator system prompt: `_COORDINATOR_PROMPT` defines mandatory planning + flow-tracking behavior.
- Runtime state backend: `StateBackend` from `deepagents.backends` (default backend for agent state + virtual files).
- Flow tracking file path: `/runtime/coordinator_flow.md` (constant `_FLOW_TRACKING_FILE`).
- Subagent wiring: single `rag_retriever` subagent with retriever tool; coordinator delegates via `task()`.
- Runtime orchestrator that invokes coordinator: `run_runtime_agent(...)` in `src/backend/services/agent_service.py`.
- API entrypoint: `POST /api/agents/run` in `src/backend/routers/agent.py`.
- Behavioral tests: `src/backend/tests/agents/test_coordinator_agent.py`.

## Data Flow
### Inputs
- External input: API request body `RuntimeAgentRunRequest` with `query` (`src/backend/schemas/agent.py`).
- Internal contextual input: `run_runtime_agent(...)` builds decomposition context and embeds it in the coordinator input message as JSON (`_build_coordinator_input_message`).

### Transformations and movement
1. API layer receives `POST /api/agents/run` and passes payload to `run_runtime_agent(...)`.
2. Service layer creates coordinator by calling `create_coordinator_agent(vector_store, model)`.
3. `create_coordinator_agent(...)` builds a deep-agents runnable with:
- `system_prompt=_COORDINATOR_PROMPT` (includes explicit requirements to call `write_todos` and maintain `/runtime/coordinator_flow.md`).
- `backend=StateBackend` (unless explicitly overridden).
- Subagent list containing `rag_retriever`.
4. `run_runtime_agent(...)` invokes the coordinator runnable with a `HumanMessage` that includes:
- User question.
- “Initial retrieval context for decomposition” JSON block.
- Subquestion formatting constraints.
5. During execution, the coordinator uses deep-agents tools (per prompt contract):
- `write_todos` to represent stage status.
- `write_file` once to create `/runtime/coordinator_flow.md`.
- `read_file` + `edit_file` to update flow state over time.
6. State is persisted in the deep-agents virtual file system attached to `StateBackend`, so plan/file state survives across tool calls/turn transitions within the run.
7. Coordinator delegates sub-questions via `task()` to `rag_retriever`; results eventually return to `run_runtime_agent(...)` as message history + final output.

### Outputs
- Coordinator side effects: structured todo state + flow markdown file content inside virtual FS state.
- Service response: `RuntimeAgentRunResponse` containing `main_question`, `sub_qa`, and `output`.
- Operational observability: coordinator construction/invoke logs include backend name and flow file path.

## Key Interfaces and APIs
- `create_coordinator_agent(vector_store, model, *, create_deep_agent_fn=None, backend_factory=None) -> Any`
- Deep-agents backend contract: accepts `StateBackend` class as `backend` argument during runnable creation.
- Runtime API route: `POST /api/agents/run` (`runtime_agent_run(...)`).
- Request/response schemas:
- `RuntimeAgentRunRequest { query: str }`
- `RuntimeAgentRunResponse { main_question, sub_qa[], output }`

## Fit With Adjacent Sections
- Upstream dependency: the initial context search path in `run_runtime_agent(...)` provides decomposition context embedded into coordinator input.
- Downstream dependency: coordinator-produced sub-question work feeds later per-subquestion stages (expand/search/validate/rerank/answer/check), initial answer generation, and refinement stages.
- This section is the control-plane layer: it does not perform ranking/verification itself, but it enforces consistent stage tracking so downstream data-plane steps remain coordinated.

## Tradeoffs
### Chosen design
- Prompt-enforced workflow tracking (`write_todos` + virtual file updates) with `StateBackend` default.

### Benefits
- Durable, inspectable run-state: flow file + todos provide explicit execution trace.
- Better long-horizon reliability: reduces coordinator drift across many pipeline stages.
- Tool-level observability: logs and callback traces can confirm state-tracking behavior.

### Costs
- Prompt coupling: correctness depends on agent following prompt/tool instructions.
- Additional token/tool overhead: frequent todo/file operations add latency and cost.
- Backend dependence: design assumes deep-agents `StateBackend` semantics and available file tools.

### Alternatives considered/rejected
- In-memory only tracking inside model context:
- Pro: lower tool overhead.
- Con: higher risk of state loss in long workflows; poor inspectability.
- Server-side explicit state machine (outside agent tools):
- Pro: deterministic control and stronger guarantees.
- Con: less agent flexibility; more implementation complexity and tighter orchestration code.
- Persistent database-backed run logs as the primary control state:
- Pro: durable across process restarts and easier historical analytics.
- Con: heavier write path and more schema/transaction complexity for iterative agent planning.
