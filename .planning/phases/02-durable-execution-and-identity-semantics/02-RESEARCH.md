# Phase 2: Durable Execution and Identity Semantics - Research

**Researched:** 2026-03-12  
**Domain:** LangGraph durable execution, thread identity contracts, replay-safe side effects, HITL pause/resume  
**Confidence:** HIGH

## Summary

Phase 2 should be implemented by adopting LangGraph-native persistence and interrupt semantics directly, not by extending the current in-memory job registry. The current backend keeps async job state in process memory (`agent_search/runtime/jobs.py`) and can cancel, but cannot durably resume after process failure, and it does not expose a stable `thread_id` contract in API responses.

The standard approach is: compile graphs with a Postgres checkpointer, require a caller-visible stable `thread_id` for every run, resume with the same `thread_id` and `Command(resume=...)` for HITL, and ensure side-effecting/non-deterministic work is wrapped in LangGraph `@task` (or isolated node boundaries) plus application idempotency keys. This directly maps to REL-01..REL-04.

Primary risk is replay behavior: LangGraph resumes from a checkpoint boundary, not from the exact Python line. Code before an interrupt can run again; side effects can duplicate unless idempotency is explicit.

**Primary recommendation:** Implement Phase 2 around `PostgresSaver` + strict `thread_id` ownership + interrupt/Command flows, and enforce idempotent side effects with durable dedupe keys in Postgres.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | `1.0.10` (current repo lock; latest seen `1.1.2`) | Graph runtime, replay, interrupts | Native durability model and thread/checkpoint semantics |
| `langgraph-checkpoint-postgres` | `3.0.4` (latest PyPI) | Durable checkpoint persistence in Postgres | Official production checkpointer for LangGraph |
| `psycopg` | `3.2.6` (repo) | Postgres driver | Required backend DB transport; compatible with saver |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langgraph-checkpoint` | `4.0.1` (transitive in lock) | Base checkpoint interface/serde | Already used via LangGraph internals |
| `SQLAlchemy` | `2.0.40` (repo) | Application-level idempotency ledger and run tables | Persist run/thread mapping and side-effect dedupe |
| Alembic | `1.15.1` (repo) | Schema migrations | Add durable execution metadata tables safely |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `PostgresSaver` | `InMemorySaver` | Simpler local dev but fails REL-01 durability on crash/restart |
| `PostgresSaver` | `AsyncPostgresSaver` | Better fit for fully async invoke path; higher integration complexity if runtime remains mostly sync |
| DB-backed checkpoints | Custom checkpoint tables | Reinvents durable replay semantics already implemented/tested by LangGraph |

**Installation:**
```bash
cd src/backend && uv add langgraph-checkpoint-postgres
```

## Architecture Patterns

### Recommended Project Structure
```
src/backend/
├── agent_search/runtime/
│   ├── persistence.py         # PostgresSaver lifecycle + graph compile helpers
│   ├── execution_identity.py  # thread_id/run_id contract and validation
│   └── resume.py              # resume/replay/HITL command helpers
├── services/
│   └── idempotency_service.py # external side-effect dedupe ledger
└── routers/
    └── agent.py               # expose thread_id + pause/resume endpoints/contracts
```

### Pattern 1: Checkpointed graph invocation with stable `thread_id`
**What:** Every run invocation includes `config={"configurable":{"thread_id": ...}}` and uses a Postgres checkpointer at compile time.  
**When to use:** Always; this is the base for REL-01 and REL-02.  
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/persistence
from langgraph.checkpoint.postgres import PostgresSaver

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()  # first-time bootstrap
    graph = builder.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(inputs, config=config)
```

### Pattern 2: HITL pause/resume via `interrupt()` and `Command(resume=...)`
**What:** Node pauses with interrupt payload; API/UI resumes by reinvoking same thread with resume value.  
**When to use:** Approval gates, review/edit steps, operator intervention (REL-04).  
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/interrupts
from langgraph.types import interrupt, Command

def approval_node(state):
    decision = interrupt({"question": "Approve run?"})
    return {"approved": bool(decision)}

# initial invoke pauses
graph.invoke(input_payload, config={"configurable": {"thread_id": thread_id}})
# resume later
graph.invoke(Command(resume=True), config={"configurable": {"thread_id": thread_id}})
```

### Pattern 3: Replay-safe side effects in tasks + app idempotency key
**What:** Any side effect (HTTP call, write, email, billing) is isolated and idempotent.  
**When to use:** All external effects and non-deterministic operations (REL-03).  
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/durable-execution
from langgraph.func import task

@task
def emit_side_effect(idempotency_key: str, payload: dict) -> dict:
    # 1) check ledger for key
    # 2) if absent, execute effect and persist outcome
    # 3) return recorded outcome
    return {"status": "ok"}
```

### Anti-Patterns to Avoid
- **In-memory run registry as source of truth:** process restart loses status/checkpoints.
- **Generating new `thread_id` on retries/resume:** breaks continuity and starts a new thread.
- **Placing side effects before/around `interrupt()` in same node without task/idempotency:** can duplicate on replay.
- **Using `Command(update=...)` as API resume input:** docs specify `Command(resume=...)` is the intended input for resume.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Durable checkpoints | Custom checkpoint state machine tables | `PostgresSaver` | LangGraph already handles checkpoint lineage, pending writes, and replay semantics |
| Pause/resume protocol | Custom "paused" booleans with ad-hoc transitions | `interrupt()` + `Command(resume=...)` | Canonical model ties suspension to persisted graph state |
| Replay dedupe for effects | Best-effort retries without persistent dedupe | Task-wrapped effects + idempotency ledger table (`thread_id`,`node`,`effect_key`) unique | Prevents duplicate external effects under retries/replay |
| Thread continuity | Recompute `thread_id` from job/process context | Persist explicit client-visible `thread_id` mapping to run/job records | Guarantees REL-02 contract across API/SDK/runtime |

**Key insight:** LangGraph durability is checkpoint-centric and thread-centric; replacing pieces with app-local shortcuts creates semantic gaps exactly in failure/replay paths.

## Common Pitfalls

### Pitfall 1: Confusing `run_id` and `thread_id`
**What goes wrong:** APIs return only `run_id`; retries create new threads implicitly.  
**Why it happens:** Current code seeds run metadata from job UUID and does not expose/persist thread identity contract.  
**How to avoid:** Introduce explicit immutable `thread_id` for logical conversation/run lineage and persist `run_id -> thread_id` mapping.  
**Warning signs:** Resume attempts require original process memory or start from scratch after restart.

### Pitfall 2: Assuming resume continues from exact line
**What goes wrong:** Code before interrupt or failed boundary executes again and duplicates side effects.  
**Why it happens:** LangGraph resumes from checkpoint boundaries (node/entrypoint/task semantics), not arbitrary instruction pointer.  
**How to avoid:** Wrap side effects/non-determinism in tasks or isolated nodes and enforce idempotency keys.  
**Warning signs:** Duplicate emails/webhooks/writes after pause/resume or crash recovery.

### Pitfall 3: Missing first-time checkpointer setup
**What goes wrong:** Checkpoint tables are unavailable or not committed; runtime fails at first write/read.  
**Why it happens:** `PostgresSaver` requires `setup()` on initial use.  
**How to avoid:** Add bootstrapping path (startup migration/health bootstrap) that runs `setup()` once.  
**Warning signs:** Runtime errors on first checkpoint operations; missing checkpointer tables.

### Pitfall 4: Non-deterministic branching around interrupts
**What goes wrong:** On resume, different branch order causes interrupt/resume value mismatch.  
**Why it happens:** Interrupt matching is order/index sensitive in multi-interrupt patterns.  
**How to avoid:** Keep deterministic control flow inputs in state; do not branch on wall clock/random outside task capture.  
**Warning signs:** Resume value applied to wrong interrupt prompt or inconsistent state transitions.

## Code Examples

Verified patterns from official sources:

### Resume failed/paused run using same thread
```python
# Source: https://docs.langchain.com/oss/python/langgraph/durable-execution
config = {"configurable": {"thread_id": thread_id}}
graph.invoke(initial_input, config=config)
# ... interruption/failure ...
graph.invoke(None, config=config)  # resume from checkpointed thread
```

### HITL approval gate
```python
# Source: https://docs.langchain.com/oss/python/langgraph/interrupts
from langgraph.types import interrupt, Command

def approval_node(state):
    approved = interrupt({"question": "Approve action?"})
    return {"approved": approved}

graph.invoke(payload, config={"configurable": {"thread_id": tid}})
graph.invoke(Command(resume=True), config={"configurable": {"thread_id": tid}})
```

### Checkpoint history for debugging/replay controls
```python
# Source: https://docs.langchain.com/oss/python/langgraph/persistence
config = {"configurable": {"thread_id": tid}}
latest = graph.get_state(config)
history = list(graph.get_state_history(config))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ephemeral in-process job status | Persistent checkpointer-backed threads | LangGraph durability docs + 1.x ecosystem | Recovery survives process/container restarts |
| Ad-hoc pause flags | `interrupt()` + `Command(resume=...)` | LangGraph interrupt model in current docs | Standardized HITL pause/resume semantics |
| Unscoped retries | Task-level replay + idempotency keys | Durable execution guidance | Prevent duplicate side effects under replay |

**Deprecated/outdated:**
- Relying on `InMemorySaver` for production durability: acceptable for local/dev only.

## Open Questions

1. **Sync vs async saver integration in this backend**
   - What we know: API surface is mostly sync; async status polling already exists; both saver variants exist.
   - What's unclear: whether phase should switch execution path to fully async graph methods now or keep sync invoke.
   - Recommendation: keep sync path for Phase 2 unless required by throughput; design persistence wrapper so async migration is later.

2. **Thread ownership policy**
   - What we know: `thread_id` must remain stable across API/SDK/execution for resume semantics.
   - What's unclear: whether client supplies thread IDs, server always creates, or hybrid with validation.
   - Recommendation: adopt hybrid: accept optional client `thread_id`, otherwise mint server UUIDv7; always return it and persist.

3. **Idempotency scope for external effects**
   - What we know: replay can re-run side-effecting work if it did not complete/record.
   - What's unclear: which operations in this codebase are externally visible in Phase 2 scope.
   - Recommendation: enumerate all side effects during planning and require effect-key strategy per operation before implementation.

## Sources

### Primary (HIGH confidence)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) - thread/checkpoint model, checkpointer libraries, replay/history APIs
- [LangGraph Durable Execution](https://docs.langchain.com/oss/python/langgraph/durable-execution) - determinism, idempotency, durability modes, resume semantics
- [LangGraph Interrupts / HITL](https://docs.langchain.com/oss/python/langgraph/interrupts) - interrupt lifecycle, `Command(resume=...)`, multi-interrupt behavior
- [LangGraph Functional API](https://docs.langchain.com/oss/python/langgraph/functional-api) - task semantics, determinism/idempotency pitfalls
- [LangGraph Add Memory](https://docs.langchain.com/oss/python/langgraph/add-memory) - PostgresSaver setup examples and production guidance
- [LangGraph PyPI](https://pypi.org/project/langgraph/) - current release/version metadata
- [langgraph-checkpoint-postgres PyPI](https://pypi.org/project/langgraph-checkpoint-postgres/) - package usage details (`setup`, psycopg connection requirements)

### Secondary (MEDIUM confidence)
- None required; primary sources were sufficient.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - official docs + PyPI package metadata + repo lockfile alignment
- Architecture: HIGH - directly derived from official LangGraph persistence/interrupt/task semantics
- Pitfalls: HIGH - explicitly documented replay/interrupt behavior and verified against current code structure

**Research date:** 2026-03-12  
**Valid until:** 2026-04-11 (30 days; monitor LangGraph minor releases)
