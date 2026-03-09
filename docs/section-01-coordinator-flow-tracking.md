# Section 1 Architecture: Coordinator Flow Tracking via `write_todos` and Virtual File System

## Purpose
Keep long multi-stage agent runs coherent by forcing the coordinator to persist plan state in two places:
- `write_todos` (structured stage checklist)
- deep-agents virtual filesystem file `/runtime/coordinator_flow.md` (narrative flow state)

This prevents stage loss across decomposition, sub-question delegation, and refinement paths.

## Components
- API entrypoint: `POST /api/agents/run` in [`src/backend/routers/agent.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/routers/agent.py)
- Runtime orchestrator: `run_runtime_agent(...)` in [`src/backend/services/agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/agent_service.py)
- Coordinator factory: `create_coordinator_agent(...)` in [`src/backend/agents/coordinator.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/agents/coordinator.py)
- Deep-agents backend: `StateBackend` (virtual filesystem state)
- Deep-agents checkpointer: in-memory saver attached at coordinator construction
- Subagent retrieval tool: `search_database(...)` from [`src/backend/tools/retriever_tool.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tools/retriever_tool.py)
- Observability callbacks: [`src/backend/utils/agent_callbacks.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/utils/agent_callbacks.py)

## Flow Diagram
```text
+---------------------------------------------------------------+
| Client                                                        |
|  - POST /api/agents/run { query }                             |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
| FastAPI Router (`runtime_agent_run`)                          |
|  +---------------------------------------------------------+  |
|  | Service call: run_runtime_agent(payload, db)            |  |
|  +---------------------------------------------------------+  |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
| Agent Service (`run_runtime_agent`)                           |
|  +---------------------------------------------------------+  |
|  | create_coordinator_agent(vector_store, model)           |  |
|  | generate per-run thread_id (UUID)                       |  |
|  +---------------------------+-----------------------------+  |
|                              |                                |
+------------------------------|--------------------------------+
                               v
+---------------------------------------------------------------+
| Coordinator (`create_coordinator_agent`)                      |
|  +---------------------------------------------------------+  |
|  | System prompt contract:                                  |  |
|  |  - call `write_todos` at start and transitions          |  |
|  |  - create `/runtime/coordinator_flow.md` with write_file|  |
|  |  - update using read_file + edit_file                   |  |
|  +---------------------------------------------------------+  |
|  +---------------------------------------------------------+  |
|  | deep-agents backend = `StateBackend` (virtual FS state) |  |
|  | checkpointer = in-memory saver                          |  |
|  +---------------------------------------------------------+  |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
| Deep Agent Runtime                                             |
|  +--------------------------+  +----------------------------+ |
|  | Planner tools            |  | Subagent (`rag_retriever`) | |
|  | - write_todos            |  | - task() delegated         | |
|  | - read_file/write_file   |  | - calls `search_database`  | |
|  | - edit_file              |  | - returns sub-answer       | |
|  +--------------------------+  +----------------------------+ |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
| Agent Service post-invoke                                      |
|  - callback logs tool calls/results                            |
|  - extract `sub_qa` from task + tool outputs                   |
|  - continue into later sections                                |
+---------------------------------------------------------------+
```

## Data Flow
Inputs:
- HTTP payload: `RuntimeAgentRunRequest.query`
- Decomposition sub-questions (generated before coordinator invocation)

Transformations and movement:
1. `run_runtime_agent(...)` serializes the provided sub-question list into one coordinator `HumanMessage`.
2. `create_coordinator_agent(...)` builds deep-agent runtime with:
- main coordinator prompt that enforces `write_todos` + virtual-file updates
- `StateBackend` for persisted in-run filesystem state
- in-memory checkpointer for run state snapshots
- one retrieval subagent with `search_database`
3. `run_runtime_agent(...)` creates a fresh UUID `thread_id` per run and invokes with
`config={"callbacks":[...], "configurable":{"thread_id": "<uuid>"}}`.
4. During `agent.invoke(...)`, deep-agents emits tool calls:
- planner flow state: `write_todos`, `write_file`/`read_file`/`edit_file` on `/runtime/coordinator_flow.md`
- delegated retrieval: subagent `search_database(query, expanded_query, ...)`
5. `AgentLoggingCallbackHandler` logs tool inputs/outputs; `SearchDatabaseCaptureCallback` captures retrieval input-output pairs for deterministic extraction; optional Langfuse callback emits external traces.
6. Service converts message/tool traces into `sub_qa` records (sub-question, raw retrieval output, expanded query, subagent response), then hands off to later pipeline sections.

Outputs:
- Intermediate: in-memory deep-agent state containing todo status and virtual file content
- Intermediate: per-run checkpoint snapshots keyed by `thread_id` (no cross-run chat continuity because each run uses a new thread)
- Intermediate: extracted `sub_qa` list for downstream pipeline stages
- External response eventually includes final `RuntimeAgentRunResponse`

## Key Interfaces / APIs
- `POST /api/agents/run` -> `RuntimeAgentRunResponse`
- `create_coordinator_agent(vector_store, model, create_deep_agent_fn=None, backend_factory=None, checkpointer=None)`
- deep-agents `create_deep_agent(...)` called with `backend=StateBackend`
- deep-agents invoke config includes `configurable.thread_id` (unique per run)
- retriever tool API:
`search_database(query: str, expanded_query: str | None = None, limit: int = 10, wiki_source_filter: str | None = None) -> str`

## How It Fits Adjacent Sections
- Upstream dependency from Section 2/3 work: coordinator receives only the normalized sub-question list in its first input message.
- Downstream dependency for Sections 4-14: coordinator delegation and captured subagent retrieval traces seed `sub_qa`, which is the input contract for validation, reranking, answering, verification, initial synthesis, and refinement loops.
- If Section 1 flow tracking fails, later sections still may run but lose reliable stage visibility and traceability.

## Tradeoffs
1. Dual tracking (`write_todos` + `/runtime/coordinator_flow.md`)
- Chosen: better human-readable + structured progress states.
- Alternative: `write_todos` only.
- Pros: redundancy improves recoverability and debugging.
- Cons: extra token/tool overhead and risk of divergence between two state representations.

2. Virtual filesystem via `StateBackend`
- Chosen: state is managed inside deep-agents runtime, avoiding ad-hoc external file writes.
- Alternative: persist flow state in Postgres.
- Pros: simple integration, no schema/migration work, aligned with agent tooling.
- Cons: state is run-scoped; cross-run analytics/auditing are weaker than DB persistence.

3. Prompt-level enforcement for tool behavior
- Chosen: encode guardrails in system prompt (create once with `write_file`, then `read_file + edit_file`).
- Alternative: hard runtime validator that rejects invalid tool sequences.
- Pros: fast to implement and adaptable.
- Cons: relies on model compliance; not a strict guarantee under all prompts.

4. Single retrieval subagent under coordinator
- Chosen: coordinator delegates retrieval via `task()` to one RAG subagent.
- Alternative: coordinator uses retriever directly.
- Pros: separation of planning vs retrieval execution.
- Cons: added message hops and extraction complexity when reconstructing `sub_qa`.
