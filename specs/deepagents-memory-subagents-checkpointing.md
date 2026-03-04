# DeepAgents: Memory (with Routing), Subagents, Checkpointing & Config — Spec

**JTBD:** When I run the agent, I want conversation and user-scoped memory across threads, specialized subagents with tools for retrieval/research, and durable execution with proper thread/checkpoint config so I can resume and trace runs.

**Scope:** Add to the DeepAgent orchestration: (1) LangGraph memory store with routing, (2) subagents with tools per Deep Agents API, (3) checkpointer and configurable (`thread_id`, optional `checkpoint_id`, `user_id`/context) for all runs.

**Status:** Discussion / Draft

**References:**
- [LangGraph Persistence (Memory Store)](https://docs.langchain.com/oss/python/langgraph/persistence#memory-store)
- [Deep Agents Overview](https://docs.langchain.com/oss/python/deepagents/overview)
- [Deep Agents Subagents](https://docs.langchain.com/oss/python/deepagents/subagents)

---

<scope>
## Topic Boundary

This spec covers only the **integration** of memory store, subagents, checkpointing, and config into the existing DeepAgent-based pipeline (see `orchestration-langgraph.md`). It does not redefine decomposition, tool selection, retrieval, or synthesis behavior—those stay in their respective specs. It defines:

- How memory is stored and retrieved (Store + namespace + optional semantic search) and **when** it is read/written (routing).
- How subagents are defined (tools, descriptions, system prompts) and how the main agent delegates to them.
- How checkpointing and config are passed (thread_id, checkpoint_id, context) and where they come from (API, env).
</scope>

---

<requirements>
## Requirements

### 1. Memory with routing

- **Store (cross-thread):** Use LangGraph’s **Store** interface (e.g. `InMemoryStore` for dev, `PostgresStore` or `RedisStore` for production) in addition to the checkpointer. The checkpointer is per-thread; the store is for data that must be shared **across threads** (e.g. user preferences, summaries).
- **Namespace:** Memories are namespaced by a tuple, e.g. `(user_id, "memories")`. `user_id` (or equivalent) must come from runtime context or request.
- **Routing (when to read/write):**
  - **Read:** At start of a run (or in a dedicated “memory lookup” step), call `store.search(namespace)` or semantic `store.search(namespace, query=..., limit=N)` and inject relevant memories into the agent context (e.g. system message or state).
  - **Write:** After synthesis (or in a dedicated “memory update” node), optionally write a memory (e.g. query + summary, or user preference) via `store.put(namespace, memory_id, value)`. Routing logic (e.g. “only write when user asks to remember” or “always write final summary”) is implementation-defined but must be explicit.
- **Semantic search (optional):** If the store is configured with an embedding index (`embed`, `dims`, `fields`), support semantic search in the read path; otherwise use simple namespace search.
- **Context:** Use a **context schema** (e.g. dataclass with `user_id`) and pass it when invoking the graph so nodes can access `runtime.context.user_id` and thus the store namespace. Deep agents built on LangGraph support this when the graph is compiled with `context_schema` and invoked with `context=...`.

### 2. Subagents with tools

- **Subagent definitions:** Define subagents per [Deep Agents Subagents](https://docs.langchain.com/oss/python/deepagents/subagents): each subagent is a dict with required `name`, `description`, `system_prompt`, `tools` (list of callables). Optionally `model`, `middleware`, `interrupt_on`, `skills`.
- **Tools per subagent:** Assign only the tools each subagent needs (e.g. research subagent: web search + open_url; retrieval subagent: internal RAG tool). Main agent keeps high-level tools (e.g. `task()` for delegation) and possibly shared tools if desired.
- **Delegation:** Main agent uses the built-in **task** tool to delegate to a subagent by name. Subagents return a single result (concise summary preferred) to avoid context bloat.
- **At least one specialized subagent:** E.g. “research-agent” or “subquery-executor” with description and system prompt that match the pipeline (research / retrieval + validation). The existing `SubQueryExecutionAgent` in code can be reflected as a Deep Agents subagent with tools that call the current retrieval/validation services.
- **Context propagation:** Parent’s `config` (including `context` and `configurable`) is passed to subagent invocations so that `thread_id`, `user_id`, and store/checkpointer behave correctly in subagent runs.

### 3. Checkpointing and config

- **Checkpointer:** Compile the DeepAgent graph with a **checkpointer** (e.g. `AsyncPostgresSaver` from `DATABASE_URL` for production; `InMemorySaver` for dev). This enables per-thread state, resume, and time-travel.
- **Configurable:** Every `ainvoke` / `astream` must receive a **config** that includes at least:
  - `configurable.thread_id` (required when using a checkpointer): identifies the conversation/run thread.
  - `configurable.checkpoint_id` (optional): for replay/fork from a specific checkpoint.
- **Context:** Pass runtime context (e.g. `user_id`) for store namespace and for subagents; e.g. `context=Context(user_id=...)` or equivalent in the run config.
- **API:** Extend the run request to accept:
  - `thread_id` (optional but recommended): if provided, use it; otherwise generate one per run and return it in the response so the client can reuse it.
  - `user_id` (optional): for memory namespace and context.
  - `checkpoint_id` (optional): for replay.
  Response should include `thread_id` (and optionally `checkpoint_id`) so the client can resume or replay.
- **Env config:** Continue using `AGENT_MODEL_NAME`, `AGENT_MODEL_PROVIDER`, `DATABASE_URL` for model and persistence. No new required env vars for minimal implementation; optional e.g. for store backend or embedding model for semantic memory.

</requirements>

---

<acceptance_criteria>
## Acceptance Criteria

- **Memory:** The agent has access to a LangGraph Store. Memories are namespaced by `user_id` (or equivalent). There is a defined “read” point (e.g. start of run or memory node) and an optional “write” point (e.g. after synthesis). Semantic search is optional.
- **Subagents:** At least one subagent is defined with `name`, `description`, `system_prompt`, and `tools`. The main agent can delegate to it via the task tool. Subagent tools are wired to the existing retrieval/validation behavior or equivalent.
- **Checkpointing:** The graph is compiled with a checkpointer. Each run that should be persistent is invoked with `configurable.thread_id`. State can be inspected with `graph.get_state(config)` when applicable.
- **Config:** Run endpoint accepts optional `thread_id`, `user_id`, `checkpoint_id` and passes them into the agent config/context; response includes `thread_id` (and optionally `checkpoint_id`) when relevant.
</acceptance_criteria>

---

<implementation>
## Implementation notes

- **Store vs checkpointer:** Checkpointer = per-thread graph state (messages, current node). Store = cross-thread key/value (memories). Use both: `graph.compile(checkpointer=..., store=store)`. Deep agents built on LangGraph will expose this when the underlying graph is compiled with both.
- **Context schema:** If using raw LangGraph under the hood, use `StateGraph(..., context_schema=Context)` and pass `context=Context(user_id=request.user_id)` on invoke. If using `create_deep_agent` only, follow the library’s pattern for context (e.g. `context_schema` and invocation config).
- **Subagent tools:** Wrap existing services (e.g. `execute_subquery_retrieval`, `validate_retrieval_result`) in callables with clear docstrings so the subagent can use them; main agent gets `task()` and any high-level tools.
- **Request schema:** Add optional fields to `RuntimeAgentRunRequest`: `thread_id: Optional[str]`, `user_id: Optional[str]`, `checkpoint_id: Optional[str]`. Add to `RuntimeAgentRunResponse` (or `graph_state.graph`): `thread_id`, and optionally `checkpoint_id` after run.
- **Backward compatibility:** If `thread_id` is not provided, generate one (e.g. uuid) for the run and return it; behavior remains stateless from the client’s perspective unless the client sends `thread_id` for continuity.
</implementation>

---

<boundaries>
## Out of Scope

- Changing decomposition, tool selection, retrieval, or synthesis logic (other specs).
- Streaming/MCP/UI (streaming-agent-heartbeat.md, mcp-exposure.md).
- Human-in-the-loop / interrupts (can be added later via `interrupt_on` on subagents).
</boundaries>

---
*Topic: deepagents-memory-subagents-checkpointing*
*Spec created: 2025-03-04*
*Relates to: orchestration-langgraph*
