# Architecture Research

**Domain:** Production RAG orchestration migration from custom workflow engine to LangGraph state graphs (FastAPI + React + Postgres/pgvector)
**Researched:** 2026-03-12
**Confidence:** HIGH (LangGraph primitives, persistence, and state model), MEDIUM (migration sequencing details are architecture recommendations)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                  Experience / API Layer                                    │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  React App (unchanged API client usage)                                                    │
│      │                                                                                     │
│      ▼                                                                                     │
│  SDK + Generated Client (major-version compatibility facade)                               │
│      │                                                                                     │
│      ▼                                                                                     │
│  FastAPI Routers (stable external contracts where required)                                │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                              Orchestration / Domain Layer                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Orchestrator Adapter (feature flag + traffic routing)                                     │
│      ├──────────────► Legacy Orchestrator (read-only during migration tail)               │
│      └──────────────► LangGraph Runtime (StateGraph)                                       │
│                          ├── Ingestion Subgraph                                             │
│                          ├── Retrieval Subgraph                                             │
│                          ├── Answer/Citation Subgraph                                       │
│                          └── Evaluation/Guardrails Subgraph                                 │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                 Data / Integration Layer                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Postgres + pgvector  │  LangGraph Checkpointer (PostgresSaver)  │  Document/Chunk Store  │
│  Embedding/LLM Provider Clients (OpenAI via LangChain integrations)                        │
│  Telemetry: LangSmith traces + app metrics/logs                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| React frontend | Collect user queries, display streaming answers/citations, no orchestration logic | Existing React + TypeScript app calling SDK client |
| SDK + generated client | Keep API surface stable across migration versions | Generated OpenAPI client plus compatibility wrappers |
| FastAPI routers | Validate request/auth, map HTTP contracts to domain service calls | Thin router handlers + Pydantic request/response models |
| Orchestrator adapter | Single boundary that decides legacy vs LangGraph path | Strategy/factory selected by feature flag, tenant, or endpoint version |
| LangGraph entry graph | Canonical workflow for query handling and response generation | `StateGraph` with typed state, reducers, conditional edges |
| LangGraph subgraphs | Isolated capability units (retrieval, synthesis, eval) with clear state contracts | Compiled subgraphs invoked by parent graph or added as nodes |
| Retrieval services | Deterministic retrieval over pgvector + metadata filters | Repository services wrapped as graph nodes/tasks |
| LLM/embedding gateway | Provider abstraction, retries, rate-limit handling, idempotency keys | LangChain model wrappers + internal retry policies |
| Checkpoint store | Durable execution, resumability, thread memory, rollback support | `langgraph-checkpoint-postgres` on existing Postgres cluster |
| Observability pipeline | End-to-end run traces and node-level visibility | LangSmith tracing + structured logs + metrics/alerts |

## Recommended Project Structure

```
src/
├── backend/
│   ├── api/
│   │   ├── routers/                      # Existing FastAPI routes (stable contract boundary)
│   │   └── schemas/                      # HTTP input/output models
│   ├── orchestration/
│   │   ├── adapter.py                    # Legacy vs LangGraph dispatch and migration flags
│   │   ├── legacy/                       # Legacy orchestrator kept for fallback during cutover
│   │   └── langgraph/
│   │       ├── state.py                  # Canonical graph state schemas and reducers
│   │       ├── graph.py                  # Root StateGraph compile/wiring
│   │       ├── subgraphs/
│   │       │   ├── ingestion.py          # Optional ingest path
│   │       │   ├── retrieval.py          # Retrieve + rerank + context assembly
│   │       │   ├── answer.py             # Synthesis + citations + formatting
│   │       │   └── guardrails.py         # Policy and confidence checks
│   │       ├── nodes/                    # Pure node logic and task wrappers
│   │       ├── edges/                    # Routing/branching conditions
│   │       └── io/
│   │           ├── checkpointer.py       # PostgresSaver/AsyncPostgresSaver setup
│   │           └── stream_mapper.py      # Graph stream events -> API response chunks
│   ├── services/
│   │   ├── retrieval_service.py          # pgvector access, filters, ranking
│   │   ├── llm_service.py                # LLM calls and retries
│   │   └── embedding_service.py          # embedding creation / cache
│   └── observability/
│       ├── tracing.py                    # LangSmith instrumentation
│       └── metrics.py                    # latency, token, error metrics
└── frontend/
    └── ...                               # No architectural change required for first cutover
```

### Structure Rationale

- **`orchestration/adapter.py`:** enforces a hard boundary so API contracts remain stable while execution engine changes underneath.
- **`orchestration/langgraph/`:** keeps graph definitions, state schema, and node implementations together so flow is inspectable and testable.
- **`orchestration/legacy/`:** allows controlled fallback and A/B comparison until parity confidence is high.
- **`services/`:** prevents graph nodes from directly owning external I/O concerns; nodes orchestrate, services execute.
- **`observability/`:** keeps tracing/metrics first-class; migration success depends on parity evidence, not just correctness-by-inspection.

## Architectural Patterns

### Pattern 1: Typed State + Explicit Reducers

**What:** Define graph state as a typed schema, with reducer behavior explicit per key.
**When to use:** Always for production RAG graphs where message history, retrieved docs, and intermediate decisions must be deterministic.
**Trade-offs:** More upfront schema design; significantly better debuggability and replay safety.

**Example:**
```python
from typing import Annotated, TypedDict
from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages

class RAGState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    query: str
    retrieved_chunks: list[dict]
    citations: list[dict]
    answer: str
    error: str | None
```

### Pattern 2: Subgraph-per-Capability with Contracted Interfaces

**What:** Split ingestion, retrieval, synthesis, and guardrails into subgraphs with narrow input/output contracts.
**When to use:** Migration from a monolithic/custom orchestrator where step boundaries are currently implicit.
**Trade-offs:** More compile units and integration tests; enables independent team ownership and safer incremental replacement.

**Example:**
```python
# Parent graph invokes retrieval subgraph and maps back to parent state.
def run_retrieval(state: ParentState):
    out = retrieval_subgraph.invoke(
        {"query": state["query"], "k": state["k"], "filters": state["filters"]}
    )
    return {"retrieved_chunks": out["chunks"], "retrieval_debug": out.get("debug", {})}
```

### Pattern 3: Side Effects in Tasks + Durable Checkpointing

**What:** Isolate side effects (LLM/provider calls, writes) and persist checkpoints each step using a DB-backed checkpointer.
**When to use:** Any production graph requiring resume/retry, interruptibility, and idempotent recovery.
**Trade-offs:** Slight runtime overhead; major gains in reliability and operability.

**Example:**
```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.func import task

@task
def call_llm(payload: dict) -> dict:
    # side-effecting external call encapsulated in task
    return llm_client.invoke(payload)

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
```

## Data Flow

### Request Flow

```
User Query (React)
    ↓
SDK client request
    ↓
FastAPI router
    ↓
Orchestrator Adapter (feature flag / version gate)
    ↓
LangGraph Entry Graph (thread_id attached)
    ↓
[Query Normalize Node]
    ↓
[Retrieval Subgraph] → pgvector / metadata store
    ↓
[Context Assembly Node]
    ↓
[Answer Subgraph] → LLM provider
    ↓
[Citation + Guardrail Node]
    ↓
Graph stream events (token/chunk/status)
    ↓
FastAPI stream mapper
    ↓
SDK
    ↓
React UI render
```

### State Management

```
HTTP request metadata + user payload
    ↓
State initializer (input schema)
    ↓
LangGraph state channels
    ├── messages                (conversation/history channel)
    ├── retrieval inputs/outputs
    ├── synthesis outputs
    ├── citations/confidence
    └── run metadata/errors
    ↓
Checkpointer write (thread_id scoped)
    ↓
Replay/Resume/Debug via checkpoint history
```

### Key Data Flows

1. **Interactive answer flow:** request -> retrieve -> synthesize -> stream response tokens/citations to client.
2. **Thread continuity flow:** follow-up requests with same `thread_id` reuse short-term memory and checkpointed state.
3. **Recovery flow:** failure resumes from latest valid checkpoint rather than re-running full pipeline.
4. **Migration parity flow:** adapter can dual-run legacy and LangGraph paths for shadow comparison before final cutover.

## Build Order and Dependency Chain

1. **State contract first (blocking dependency)**
   - Define canonical `RAGState`, input/output schemas, and reducer rules.
   - Why first: all nodes/subgraphs and tests depend on state keys and merge semantics.

2. **Infrastructure for durability + observability**
   - Add Postgres checkpointer wiring, `thread_id` propagation, LangSmith tracing, and per-node metrics.
   - Why second: required to validate replay behavior and migration parity safely.

3. **Adapter boundary (legacy + LangGraph coexistence)**
   - Introduce orchestrator adapter with feature flags and traffic slicing.
   - Why third: enables incremental rollout without API breakage.

4. **Retrieval subgraph migration**
   - Port retrieval path from legacy orchestration first (most deterministic path).
   - Why fourth: retrieval quality can be benchmarked separately from generation variance.

5. **Answer/citation subgraph migration**
   - Port synthesis and citation formatting with compatibility mapper to existing API response models.
   - Why fifth: user-visible output parity can now be measured end-to-end.

6. **Guardrails/evaluation nodes**
   - Add confidence thresholds, fallback policies, and quality gates.
   - Why sixth: enforce production safety before broad traffic exposure.

7. **Streaming + UX parity**
   - Ensure stream event mapping matches existing frontend/SDK expectations.
   - Why seventh: prevents client-side regressions during cutover.

8. **Legacy deprecation**
   - Remove old orchestrator only after sustained parity/error SLO pass.
   - Why last: preserves rollback path until operational confidence is proven.

## Migration Cutover Strategy

### Phase A: Shadow Mode (0% user-visible LangGraph)

- Keep legacy path as source of truth.
- Run LangGraph in parallel for sampled traffic using same inputs.
- Compare: citations overlap, answer structure, latency, token/cost profile, failure classes.
- Exit criteria: parity thresholds met for a predefined rolling window.

### Phase B: Canary Routing (1-10% LangGraph by tenant/flag)

- Route a controlled subset to LangGraph as user-visible responses.
- Keep instant rollback in adapter (`legacy` flip) with no client change.
- Monitor SLOs: p95 latency, error rate, timeout/retry behavior, user feedback.

### Phase C: Progressive Ramp (25% -> 50% -> 100%)

- Increase traffic in fixed steps only if each step stabilizes.
- Enforce automatic abort conditions for regressions.
- Continue shadow comparisons for a small mirrored slice to detect drift.

### Phase D: Legacy Retirement

- Freeze legacy orchestration for read-only diagnostics window.
- Remove legacy execution path after soak period and postmortem review.
- Keep checkpoint/trace history for auditability.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Single FastAPI deployment with Postgres checkpointer and pgvector is sufficient; prioritize correctness and tracing. |
| 1k-100k users | Separate worker pool for graph execution, tune connection pools, cache embeddings/query rewrites, optimize retrieval indexes. |
| 100k+ users | Partition workloads (tenant/domain), isolate retrieval-heavy vs synthesis-heavy workers, consider async backpressure and queue-based execution control. |

### Scaling Priorities

1. **First bottleneck: retrieval latency + DB contention** - optimize pgvector indexes/filters and pool settings before introducing new infrastructure.
2. **Second bottleneck: LLM provider throughput/cost** - implement adaptive model routing, request shaping, and strict timeout/circuit-breaker policies.

## Anti-Patterns

### Anti-Pattern 1: Rewriting API contracts during engine migration

**What people do:** change SDK/frontend payload and response structures while replacing orchestration.
**Why it's wrong:** multiplies migration risk and obscures root causes of regressions.
**Do this instead:** keep contracts stable; isolate changes behind adapter and internal state schemas.

### Anti-Pattern 2: Monolithic single-node "mega graph"

**What people do:** map the old orchestrator into one giant node with hidden branching.
**Why it's wrong:** eliminates observability and checkpoint value; hard to test and replay.
**Do this instead:** model explicit nodes/subgraphs with typed transitions and measurable outputs.

### Anti-Pattern 3: Side effects outside task/checkpoint discipline

**What people do:** perform provider calls and DB writes in uncontrolled utility code.
**Why it's wrong:** retries/replays can duplicate writes or diverge behavior.
**Do this instead:** wrap side effects in task boundaries, enforce idempotency keys, and checkpoint by thread.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| OpenAI (via LangChain integrations) | Node/task-level model invocation through a service gateway | Centralize retries, timeout policy, and model routing; avoid direct provider calls in graph wiring code |
| Postgres/pgvector | Retrieval repository + checkpointer backend | Use same DB platform with separate logical schemas/tables for checkpoints vs business data |
| LangSmith | Automatic tracing via env config + instrumentation wrappers | Required for parity analysis and node-level regression isolation |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| FastAPI router <-> Orchestrator adapter | Direct Python service call | Router remains thin; no graph-specific logic in handlers |
| Adapter <-> Legacy orchestrator | Strategy interface | Enables rollback and shadow mode with identical request envelope |
| Adapter <-> LangGraph runtime | Strategy interface + typed input/output mapper | Decouple API contract from graph-internal state evolution |
| LangGraph nodes <-> Domain services | Function call via service layer | Keeps business I/O reusable and testable outside graph harness |
| LangGraph runtime <-> Checkpointer | Compiled graph runtime config | `thread_id` is mandatory for continuity, replay, and interrupts |

## Sources

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) (official)
- [LangGraph Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api) (official)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) (official)
- [LangGraph Durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution) (official)
- [LangGraph Add memory](https://docs.langchain.com/oss/python/langgraph/add-memory) (official)
- [LangGraph Subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) (official)
- [LangGraph Streaming](https://docs.langchain.com/oss/python/langgraph/streaming) (official)
- [LangSmith trace with LangGraph](https://docs.langchain.com/langsmith/trace-with-langgraph) (official)

---
*Architecture research for: LangGraph-native RAG migration*
*Researched: 2026-03-12*
