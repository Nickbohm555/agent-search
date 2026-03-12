# Phase 4: Observability and Remote Runtime Validation - Research

**Researched:** 2026-03-12
**Domain:** LangGraph runtime observability, trace correlation, and remote validation for FastAPI + Docker Compose + pip-installed SDK
**Confidence:** HIGH

## Summary

Phase 4 should formalize three things that are partially present today: (1) runtime lifecycle events as a real stream (not only polling status snapshots), (2) trace correlation that is explicit across run/thread/node/outcome, and (3) deployment-realistic validation in two remote environments (Compose and fresh pip SDK install). The current codebase already has strong primitives: `GraphStageSnapshot`, `run_metadata` (`run_id`, `thread_id`, `trace_id`, `correlation_id`), async job stage tracking, and Langfuse span/trace hooks.

The standard implementation path is to keep LangGraph as the source of execution events, expose those events to operators through SSE on FastAPI, and keep trace correlation deterministic by propagating one canonical identity tuple (`run_id`, `thread_id`, `trace_id`) through graph config, stage events, and tracing metadata. LangGraph streaming and persistence docs confirm the right event modes and the importance of `thread_id`. Langfuse and LangSmith docs both support trace correlation; this repo already uses Langfuse and should continue on that path for v1.

For REL-05, planning should require a test matrix that proves the same migrated runtime works in remote Compose and clean pip environments. "Works locally" is not enough; acceptance should include startup health, one successful end-to-end run, lifecycle event visibility, and trace correlation artifacts in each environment.

**Primary recommendation:** Implement lifecycle SSE over current stage snapshots first, then extend to native LangGraph stream parts (`updates`/`tasks`/`checkpoints`) with checkpointer-backed thread correlation and deterministic trace IDs.

## Standard Stack

The established libraries/tools for this phase:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | `1.0.10` (locked) | Graph orchestration and runtime event streaming (`updates`, `messages`, `tasks`, `checkpoints`, `debug`) | Official streaming model for node/state lifecycle visibility |
| `langgraph-checkpoint` | `4.0.1` (locked) | Checkpoint persistence interface and thread-aware state snapshots | `thread_id`-centric durability and replay model required for reliable trace/thread correlation |
| `fastapi` | `0.115.12` (current), `>=0.135.0` (optional upgrade) | API surface for operator event streams | Current version supports `StreamingResponse`; newer versions add first-party SSE helpers |
| `langfuse` | `3.14.5` (locked) | Trace/span capture and correlation metadata | Already integrated in runtime; supports trace IDs, sessions, and LangChain callbacks |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langsmith` | `0.7.12` (transitive lock) | Optional deep LangGraph trace visualization | Use when LangSmith project/workspace is available and you want parallel observability |
| Docker Compose CLI | Current install | Remote runtime validation in containerized environment | Required for REL-05 Compose proof and operator-facing smoke checks |
| `venv` + `pip` | Python packaging standard | Fresh environment SDK-install validation | Required for REL-05 pip-installed SDK proof |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `StreamingResponse` SSE framing on FastAPI `0.115` | `fastapi.sse.EventSourceResponse` on FastAPI `>=0.135.0` | Newer API reduces SSE boilerplate and supports `ServerSentEvent`, but requires dependency upgrade |
| Langfuse-only tracing | LangSmith tracing (`LANGSMITH_TRACING=true`) | LangSmith offers excellent LangGraph-native views; Langfuse is already integrated and lower migration cost for this repo |

**Installation:**
```bash
# keep existing stack
cd src/backend && uv sync

# optional future upgrade path (if team chooses first-party SSE API)
cd src/backend && uv add "fastapi>=0.135.0"
```

## Architecture Patterns

### Recommended Project Structure
```
src/backend/
├── agent_search/runtime/      # graph runner + snapshot/event producers
├── routers/                   # SSE and polling endpoints for operators
└── utils/                     # tracing adapters (Langfuse callbacks, trace ID helpers)
```

### Pattern 1: Lifecycle Event Contract (Run-scoped event envelope)
**What:** Define one canonical event schema for stream output: `event_type`, `run_id`, `thread_id`, `trace_id`, `stage`, `status`, `lane_index`, `lane_total`, `emitted_at`, optional `error`.
**When to use:** Every emitted lifecycle event from run start to completion/failure/cancel.
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/streaming
for chunk in graph.stream(inputs, stream_mode=["updates", "tasks", "checkpoints"], version="v2"):
    emit({
        "event_type": chunk["type"],
        "run_id": run_id,
        "thread_id": thread_id,
        "trace_id": trace_id,
        "payload": chunk["data"],
    })
```

### Pattern 2: Thread-Centric Durability and Correlation
**What:** Always invoke graph/checkpointer with `configurable.thread_id`; treat `thread_id` as the stable correlation key for checkpoints and replay.
**When to use:** All production runs, retries, replay, and operator debugging.
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/persistence
config = {"configurable": {"thread_id": "thread-123"}}
result = graph.invoke(inputs, config=config)
snapshot = graph.get_state(config)
```

### Pattern 3: API Streaming for Operators (SSE)
**What:** Expose lifecycle events over `text/event-stream` so UI/operators can observe progress live.
**When to use:** Operator-facing run monitoring and troubleshooting UX.
**Example:**
```python
# Source: https://fastapi.tiangolo.com/tutorial/server-sent-events/
@app.get("/runs/{run_id}/events", response_class=EventSourceResponse)
async def stream_run_events(run_id: str):
    async for event in event_bus.subscribe(run_id):
        yield ServerSentEvent(data=event, event=event["event_type"], id=event["sequence"])
```

### Pattern 4: Deterministic Trace Correlation
**What:** Generate or map deterministic trace IDs from external run/request IDs and propagate them into callback/span metadata.
**When to use:** Cross-service troubleshooting, auditability, and external system correlation.
**Example:**
```python
# Source: https://langfuse.com/docs/observability/features/trace-ids-and-distributed-tracing
trace_id = langfuse.create_trace_id(seed=external_request_id)
with langfuse.start_as_current_observation(
    as_type="span",
    name="runtime.agent_run",
    trace_context={"trace_id": trace_id},
):
    run_graph()
```

### Anti-Patterns to Avoid
- **Stage polling only as "streaming":** polling `/run-status` is not equivalent to lifecycle event streaming; it misses ordering and event granularity.
- **Missing `thread_id` on persisted runs:** breaks checkpoint retrieval/replay semantics and weakens correlation guarantees.
- **Ad-hoc trace IDs per node:** prevents single-trace reconstruction for a run.
- **One giant debug blob event:** hard to consume in UI and impossible to reason about step-by-step failures.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph lifecycle event taxonomy | Custom event protocol disconnected from runtime | LangGraph stream modes (`updates`, `tasks`, `checkpoints`, `debug`) | Preserves semantics and avoids drift from actual graph execution |
| Durable run continuity | Homegrown checkpoint files/tables | LangGraph checkpointer interface with `thread_id` | Correct replay/super-step behavior is already solved |
| Trace correlation IDs | Random per-component IDs | Langfuse deterministic `create_trace_id(seed=...)` or run-root trace ID propagation | Enables consistent cross-system debugging |
| SSE wire protocol details | Manual fragile string formatting everywhere | FastAPI SSE support (`EventSourceResponse` / `ServerSentEvent`) or one centralized formatter | Reduces protocol bugs (`id`, `event`, reconnect behavior) |

**Key insight:** Phase 4 succeeds by tightening contracts and propagation, not by inventing new runtime primitives.

## Common Pitfalls

### Pitfall 1: Event stream has no stable sequence/resume contract
**What goes wrong:** Clients reconnect and duplicate or skip progress updates.
**Why it happens:** No event `id` and no `Last-Event-ID` handling.
**How to avoid:** Emit monotonic event IDs per run and support resume from `Last-Event-ID`.
**Warning signs:** UI timelines jump backward/forward after network blips.

### Pitfall 2: `thread_id` not explicitly set on every run
**What goes wrong:** Checkpoint history cannot be reliably queried or replayed per run/thread.
**Why it happens:** Runtime relies on implicit defaults instead of explicit configurable context.
**How to avoid:** Require `thread_id` in run config and include it in every lifecycle/tracing event.
**Warning signs:** Missing state history or mismatched checkpoints in troubleshooting.

### Pitfall 3: Tracing callback exists but correlation metadata is partial
**What goes wrong:** Spans exist but cannot be mapped to node stage, thread, or final outcome.
**Why it happens:** Metadata keys are inconsistent or not propagated to child spans.
**How to avoid:** Enforce one metadata contract (`run_id`, `thread_id`, `trace_id`, `stage`, `status`).
**Warning signs:** Traces visible in dashboard but not joinable to operator logs/API events.

### Pitfall 4: Remote validation only checks startup
**What goes wrong:** Environment is "up" but runtime execution fails under real run load.
**Why it happens:** Validation stops at health checks.
**How to avoid:** For each remote target, require one successful run, one trace correlation check, and one lifecycle stream check.
**Warning signs:** `200` health endpoint but failed run assertions or missing events.

### Pitfall 5: FastAPI SSE API mismatch by version
**What goes wrong:** Planning assumes `fastapi.sse` on a version that does not provide it.
**Why it happens:** Current backend is pinned to `0.115.12`.
**How to avoid:** Decide early: keep `StreamingResponse` now, or explicitly schedule FastAPI upgrade first.
**Warning signs:** Import errors for `fastapi.sse` in CI/runtime.

## Code Examples

Verified patterns from official sources:

### LangGraph state updates streaming
```python
# Source: https://docs.langchain.com/oss/python/langgraph/streaming
for chunk in graph.stream(inputs, stream_mode="updates", version="v2"):
    if chunk["type"] == "updates":
        handle_updates(chunk["data"])
```

### LangGraph checkpoint/thread configuration
```python
# Source: https://docs.langchain.com/oss/python/langgraph/persistence
config = {"configurable": {"thread_id": "1"}}
graph.invoke(inputs, config=config)
history = list(graph.get_state_history(config))
```

### FastAPI SSE endpoint
```python
# Source: https://fastapi.tiangolo.com/tutorial/server-sent-events/
from fastapi.sse import EventSourceResponse, ServerSentEvent

@app.get("/runs/{run_id}/events", response_class=EventSourceResponse)
async def run_events(run_id: str):
    yield ServerSentEvent(comment="stream start")
    yield ServerSentEvent(data={"run_id": run_id, "stage": "decompose"}, event="stage", id="1")
```

### Langfuse deterministic trace ID
```python
# Source: https://langfuse.com/docs/observability/features/trace-ids-and-distributed-tracing
langfuse = get_client()
trace_id = langfuse.create_trace_id(seed=external_request_id)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling job status only | Live SSE event stream + optional polling fallback | Current best practice (2025-2026 docs) | Better operator UX and faster incident triage |
| Ad-hoc tracing context | Deterministic trace IDs + explicit run/thread/stage metadata | Langfuse v3 + modern observability guidance | Reliable cross-system correlation |
| Generic stream chunks | Typed runtime stream modes (`updates`, `tasks`, `checkpoints`, `debug`) | LangGraph v1 docs | Stronger semantics and easier tooling |
| Manual SSE framing in all routes | FastAPI first-party SSE helpers (`EventSourceResponse`) | Added in FastAPI 0.135.0 | Less boilerplate, fewer protocol bugs |

**Deprecated/outdated:**
- Implicit thread identity in durable runs: current LangGraph persistence requires explicit `configurable.thread_id` for checkpoint correctness.
- Treating callback presence as full observability: without consistent correlation metadata, traces are incomplete for audit/troubleshooting.

## Open Questions

1. **Should Phase 4 upgrade FastAPI for first-party SSE APIs now?**
   - What we know: Current backend is pinned at `fastapi==0.115.12`; first-party SSE docs state addition in `0.135.0`.
   - What's unclear: Whether dependency upgrade risk is acceptable in this phase scope.
   - Recommendation: Decide in planning kickoff; if "no upgrade", define a single `StreamingResponse` SSE formatter task explicitly.

2. **Will LangGraph checkpointer integration from Phase 2 be exposed directly in Phase 4 streams?**
   - What we know: `tasks` and `checkpoints` stream modes require a checkpointer.
   - What's unclear: Whether current runtime path is already invoking graph with production checkpointer in all execution modes.
   - Recommendation: Add an early verification task that asserts checkpointer-backed stream modes in both sync and async runs.

3. **Single tracing backend for v1 or dual backend support?**
   - What we know: Repo already integrates Langfuse; LangGraph docs emphasize LangSmith compatibility.
   - What's unclear: Product requirement for one or both observability backends in operator workflows.
   - Recommendation: Keep Langfuse as mandatory baseline; treat LangSmith as optional adapter unless explicitly required.

## Sources

### Primary (HIGH confidence)
- https://docs.langchain.com/oss/python/langgraph/streaming - stream modes, event formats, multi-mode streaming guidance
- https://docs.langchain.com/oss/python/langgraph/persistence - thread/checkpoint semantics and checkpointer behavior
- https://docs.langchain.com/langsmith/trace-with-langgraph - official tracing flow for LangGraph applications
- https://fastapi.tiangolo.com/tutorial/server-sent-events/ - first-party SSE API patterns and FastAPI version note
- https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse - streaming fallback patterns
- https://langfuse.com/docs/observability/features/trace-ids-and-distributed-tracing - deterministic trace IDs and distributed correlation
- https://langfuse.com/docs/integrations/langchain/tracing - Langfuse callback integration details
- https://docs.docker.com/reference/cli/docker/compose/up/ - Compose startup semantics and wait/detach behavior
- https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/ - clean pip env validation workflow

### Secondary (MEDIUM confidence)
- https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events - SSE protocol details and browser behavior constraints

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified from lockfile and official docs
- Architecture: HIGH - aligned with official LangGraph/FastAPI/Langfuse patterns plus current codebase primitives
- Pitfalls: HIGH - grounded in explicit doc constraints and observed repo implementation gaps

**Research date:** 2026-03-12
**Valid until:** 2026-04-11
