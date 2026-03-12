# Phase 3: End-to-End LangGraph RAG Cutover - Research

**Researched:** 2026-03-12
**Domain:** Production LangGraph orchestration cutover for full RAG lifecycle
**Confidence:** HIGH

## Summary

Phase 3 should convert the main production query runtime from the current imperative orchestration (`run_parallel_graph_runner`) to a compiled LangGraph `StateGraph` execution path while preserving the existing response contract and quality gates. The current backend already has node-level functions (`decompose`, `expand`, `search`, `rerank`, `answer`, `synthesize`) and typed state models, but no compiled `StateGraph` is used in runtime execution yet.

The standard approach is to keep pure node functions, define reducers in the graph state schema, build a compiled graph with explicit `START`/`END` routing, and run it with stable `thread_id` config through a checkpointer-backed runtime. For fan-out sub-question execution, LangGraph supports dynamic parallelism through `Send`; for deterministic retries, node-level `RetryPolicy` should be used instead of ad-hoc retry loops.

For this phase, planning should prioritize a strict parity path: preserve the existing output schema and citation contract behavior, route all production queries through the LangGraph runtime only, and leave legacy imperative orchestration behind a non-production fallback path (or remove it if no dependencies remain).

**Primary recommendation:** Build and ship a compiled `StateGraph` runtime as the only production query path, with explicit parity tests against the current response contract and node-level retry/checkpoint semantics.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | `1.0.10` (locked) | Graph orchestration runtime (`StateGraph`, edges, compile/invoke/stream) | Official framework for stateful, durable agent workflows |
| `langgraph-checkpoint` | `4.0.1` (locked) | Checkpoint abstraction and in-memory saver for tests | Required for persistent execution semantics and resume/replay |
| `langgraph-checkpoint-postgres` | `3.0.4` (current) | Durable Postgres-backed checkpoint persistence | Official production checkpointer for LangGraph |
| `langchain-core` | transitive via lock | Runnable/config interfaces and LLM plumbing | Standard integration layer used by LangGraph and LangChain ecosystem |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langchain` | `>=1.2.0` (declared) | Existing model/tool abstractions in project | Keep for node internals and model invocation wrappers |
| `pydantic` | `2.10.6` (declared) | Typed request/response/state contracts | Keep for API contract stability and serialization |
| `psycopg[binary]` | `3.2.6` (declared) | Postgres connectivity for app runtime | Needed when wiring Postgres checkpointer connections |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `StateGraph` orchestration | Keep custom `ThreadPoolExecutor` orchestration | Faster short-term, but fails SGF-04 and loses first-class LangGraph persistence/control-flow features |
| `PostgresSaver` | `InMemorySaver` only | Fine for tests/dev, not durable for production resume/replay |
| `Send` fan-out | Manual thread pool fan-out | Less declarative and bypasses LangGraph execution semantics/super-step checkpointing |

**Installation:**
```bash
cd src/backend
uv add langgraph langgraph-checkpoint-postgres
```

## Architecture Patterns

### Recommended Project Structure
```text
src/backend/agent_search/runtime/
├── graph/
│   ├── state.py            # LangGraph state schema + reducers (TypedDict/Annotated)
│   ├── builder.py          # StateGraph construction, node/edge wiring, compile()
│   ├── routes.py           # Conditional routing/fan-out helpers (Send/Command)
│   └── execution.py        # invoke/stream wrappers, config(thread_id), checkpointer wiring
├── nodes/                  # Existing node implementations (decompose/search/rerank/...)
├── runner.py               # Production entrypoint delegates to compiled graph only
└── jobs.py                 # Async job APIs consume same compiled graph runtime path
```

### Pattern 1: Compiled StateGraph as single runtime entrypoint
**What:** Build one compiled graph and use it for sync + async production runs.
**When to use:** Always for v1 query completion after phase cutover.
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/use-graph-api
from langgraph.graph import START, END, StateGraph

builder = StateGraph(RAGState)
builder.add_node("decompose", decompose_node)
builder.add_node("expand", expand_node)
builder.add_node("search", search_node)
builder.add_node("rerank", rerank_node)
builder.add_node("answer", answer_node)
builder.add_node("synthesize", synthesize_node)

builder.add_edge(START, "decompose")
# ... add deterministic routing edges ...
builder.add_edge("synthesize", END)

graph = builder.compile(checkpointer=checkpointer)
result = graph.invoke(inputs, config={"configurable": {"thread_id": thread_id}})
```

### Pattern 2: Dynamic fan-out/fan-in with `Send`
**What:** Route decomposition outputs into parallel sub-question branches using `Send`.
**When to use:** When number of sub-questions is dynamic per query.
**Example:**
```python
# Source: https://reference.langchain.com/python/langgraph/types/Send
from langgraph.types import Send

def route_subquestions(state: RAGState):
    return [Send("subquestion_lane", {"sub_question": q}) for q in state["decomposition_sub_questions"]]
```

### Pattern 3: Node retries via `RetryPolicy`
**What:** Attach retry policy per fragile node (LLM or retrieval dependent).
**When to use:** Transient model/network/retrieval failures where retry is safe.
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/use-graph-api#add-node-retries
from langgraph.types import RetryPolicy

builder.add_node(
    "search",
    search_node,
    retry_policy=RetryPolicy(max_attempts=3),
)
```

### Pattern 4: Thread-scoped durable execution
**What:** Always execute with `configurable.thread_id` when checkpointer is enabled.
**When to use:** All production runs requiring resume/replay/interrupt compatibility.
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/persistence
config = {"configurable": {"thread_id": run_metadata.thread_id}}
graph.invoke(graph_input, config=config)
```

### Anti-Patterns to Avoid
- **Dual orchestration in production:** Running both imperative and LangGraph runtime paths causes parity drift and undermines SGF-04.
- **Manual parallelism outside graph runtime:** Thread-pool fan-out in orchestration layer bypasses LangGraph super-step semantics and checkpoint behavior.
- **No explicit reducers for append/merge channels:** State keys updated by parallel nodes can become nondeterministic if reducer behavior is implicit.
- **Missing `thread_id` on checkpointed runs:** Breaks persistence contract and safe resume semantics.
- **Non-idempotent side effects before interruption points:** Resume/replay can re-run node prefix code and duplicate side effects.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph runtime wiring | Custom orchestration loop with manual edge control | `StateGraph` + `add_edge`/`add_conditional_edges` | Official model with validated execution semantics and toolchain support |
| Dynamic branch fan-out | Custom thread pool branch scheduler | `Send` with conditional edges | Native map-reduce style fan-out integrates with graph state semantics |
| Node retries | Custom retry wrappers scattered in services | Node `RetryPolicy` in graph definition | Centralized retry policy, less drift and clearer behavior |
| Checkpoint persistence | Custom checkpoint tables/serialization | `PostgresSaver` | Battle-tested saver interface with thread/checkpoint model |
| Pause/resume protocol | Bespoke pause tokens | `interrupt()` + `Command(resume=...)` | Native resume semantics with persisted graph state |

**Key insight:** Most "orchestration glue" should move from custom service code into graph definition + checkpointer configuration so runtime behavior stays consistent, testable, and observable.

## Common Pitfalls

### Pitfall 1: Cutover keeps legacy path as hidden default
**What goes wrong:** Production still executes old orchestration in some codepaths (sync or async).
**Why it happens:** Partial migration updates only one entrypoint (`advanced_rag` or async jobs).
**How to avoid:** Enforce one runtime gateway in `runner` and make both sync + async route through compiled graph.
**Warning signs:** Tests mock/target `run_parallel_graph_runner` instead of a compiled graph executor.

### Pitfall 2: State merge bugs under parallel sub-question processing
**What goes wrong:** Missing/duplicated sub-answers, unstable ordering, citation map collisions.
**Why it happens:** Reducers not explicitly defined for list/dict merge channels.
**How to avoid:** Define reducer semantics for append/merge keys in graph state and verify deterministic ordering in synthesis input.
**Warning signs:** Non-deterministic test snapshots between repeated runs.

### Pitfall 3: Retry policy breaks quality guardrails
**What goes wrong:** Retries produce fallback text too early or retry non-retryable failures.
**Why it happens:** Retry behavior split across node code and orchestration wrappers.
**How to avoid:** Define retry boundaries per node and classify retryable exceptions explicitly.
**Warning signs:** Increased "fallback" answers despite healthy upstream systems.

### Pitfall 4: Checkpoint/thread config mismatch
**What goes wrong:** Resume/replay does not load expected state thread.
**Why it happens:** `thread_id` not consistently propagated from run metadata into `graph.invoke`.
**How to avoid:** Standardize a single config builder that injects thread/checkpoint namespace fields.
**Warning signs:** Checkpoint history exists but run resumes as fresh execution.

### Pitfall 5: Non-idempotent effects before resume boundaries
**What goes wrong:** Duplicate writes or duplicate external actions after resume/replay.
**Why it happens:** Node code before `interrupt` (or replay boundary) performs writes.
**How to avoid:** Move side effects after approval/resume points or isolate in idempotent nodes.
**Warning signs:** Duplicate outbound events for interrupted/replayed runs.

## Code Examples

Verified patterns from official sources:

### Build and compile graph
```python
# Source: https://docs.langchain.com/oss/python/langgraph/use-graph-api
from langgraph.graph import START, END, StateGraph

builder = StateGraph(State)
builder.add_node("node_a", node_a)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", END)
graph = builder.compile()
```

### Conditional routing and dynamic parallel fan-out
```python
# Source: https://docs.langchain.com/oss/python/langgraph/graph-api#conditional-edges
from langgraph.types import Send

def route(state):
    return [Send("worker_node", {"item": item}) for item in state["items"]]

builder.add_conditional_edges("planner_node", route)
```

### Thread-scoped persistence invocation
```python
# Source: https://docs.langchain.com/oss/python/langgraph/persistence
config = {"configurable": {"thread_id": "run-123"}}
graph.invoke(inputs, config=config)
```

### Resume after interrupt
```python
# Source: https://docs.langchain.com/oss/python/langgraph/interrupts
from langgraph.types import Command

graph.invoke(Command(resume=True), config={"configurable": {"thread_id": "run-123"}})
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Imperative orchestration wrappers + thread pools | Compiled LangGraph with declarative nodes/edges/reducers | LangGraph 1.x maturity (2025-2026 ecosystem baseline) | Better durability, replayability, and control-flow clarity |
| Ad-hoc retry loops in service code | Node-scoped `RetryPolicy` in graph definition | RetryPolicy available since LangGraph `0.2.24` | Centralized retry semantics and cleaner node contracts |
| Local-only in-memory state for runtime flows | Checkpointer-backed thread persistence (`thread_id`) | Persistence model standardized in LangGraph docs | Enables reliable resume/HITL/time-travel and production fault tolerance |

**Deprecated/outdated:**
- Service-layer-only orchestration as main runtime path for v1 query completion.
- Maintaining parallel production codepaths (legacy + graph) beyond temporary migration toggles.

## Open Questions

1. **Should fan-out remain fixed-order merge or reducer-driven merge by metadata?**
   - What we know: Current runner preserves lane completion order post-collection before synthesis.
   - What's unclear: Whether phase requires strict stable ordering contract for `sub_qa` serialization.
   - Recommendation: Lock an ordering policy in tests before cutover (e.g., decomposition order index).

2. **How much of current fallback behavior is contractual vs implementation detail?**
   - What we know: Existing nodes include several fallback strings and timeout fallbacks.
   - What's unclear: Which exact fallback text is externally relied upon.
   - Recommendation: Define response-quality contract tests at API level to avoid accidental behavior drift.

3. **Will async job status stream from graph events or remain snapshot-based polling?**
   - What we know: Current async jobs update in-memory status from snapshot callbacks.
   - What's unclear: Whether phase requires native stream-based lifecycle events (likely Phase 4).
   - Recommendation: Keep current status API but drive updates from graph stream/checkpoint events internally.

## Sources

### Primary (HIGH confidence)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) - state graph model, reducers, edges, compile contract.
- [Use the Graph API](https://docs.langchain.com/oss/python/langgraph/use-graph-api) - canonical implementation patterns for `StateGraph`, `Send`, `Command`, and `RetryPolicy`.
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) - thread/checkpoint model, `thread_id` contract, checkpointer behavior.
- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) - resume semantics, idempotency constraints.
- [LangGraph Streaming](https://docs.langchain.com/oss/python/langgraph/streaming) - runtime event streaming modes for state/tasks/checkpoints.
- [LangGraph PyPI](https://pypi.org/project/langgraph/) - current release metadata and package status.
- [langgraph-checkpoint-postgres PyPI](https://pypi.org/project/langgraph-checkpoint-postgres/) - official Postgres saver usage and production caveats.
- Repository evidence:
  - `src/backend/agent_search/runtime/runner.py`
  - `src/backend/services/agent_service.py`
  - `src/backend/agent_search/runtime/nodes/`
  - `src/backend/schemas/agent.py`
  - `src/backend/uv.lock`

### Secondary (MEDIUM confidence)
- None required; primary official docs and repo code were sufficient.

### Tertiary (LOW confidence)
- Web search index pages used only to locate official docs, not as authoritative technical source.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified with lockfile + official docs/PyPI package metadata.
- Architecture: HIGH - aligned with official LangGraph Graph API and current repository runtime layout.
- Pitfalls: HIGH - derived from official LangGraph persistence/interrupt semantics plus current codepath analysis.

**Research date:** 2026-03-12
**Valid until:** 2026-04-11 (30 days; ecosystem is active and versions move quickly)
