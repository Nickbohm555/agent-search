# Phase 4: Operator Controls and Result Visibility - Research

**Researched:** 2026-03-13  
**Domain:** Runtime operator controls (rerank/query expansion) and frontend result visibility  
**Confidence:** HIGH

## Summary

This phase should standardize run-time retrieval controls as explicit run parameters, then expose them through two surfaces: frontend controls (CTRL-01) and SDK parameters (CTRL-03). The backend already has a `RuntimeConfig` model with `rerank` settings, but that config is currently parsed in SDK entrypoints and not propagated into runtime execution. Query expansion is currently env-driven only; it needs a run-level config path.

The frontend already renders sub-answer data (`sub_qa`) in multiple places, including a dedicated Subanswer panel and final synthesis details. The main implementation risk for REL-02 is not rendering itself, but ensuring `sub_qa` remains present and stable in the async event/result contracts when new run-parameter plumbing is introduced.

**Primary recommendation:** Introduce one shared run-options contract (`runtime_config`) on run requests, wire it end-to-end into runtime node execution (expand/rerank), and keep frontend controls as a thin mapping layer to those backend run parameters.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.12 | Request/response models for run APIs | Existing backend framework and contract source of truth |
| Pydantic | 2.10.6 | Runtime config/request validation | Already used for all request/response and runtime models |
| React | 18.3.1 | Operator control inputs + result rendering | Existing frontend app architecture |
| EventSource (browser API) | Baseline across modern browsers | Async run event stream handling | Matches existing `/api/agents/run-events/{job_id}` streaming model |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Vitest + Testing Library | vitest 2.1.9 / @testing-library/react 16.2.0 | Frontend interaction + rendering tests | Verify toggle payloads and sub-answer UI |
| Pytest + FastAPI TestClient | current project standard | API contract and SDK behavior tests | Validate run request schema and event/status contract stability |
| LangGraph runtime integration | `langgraph>=1.0.10` | Runtime orchestration execution | Keep control propagation at runtime context/node boundaries |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Request-level `runtime_config` | UI-only toggles or env flags | Breaks CTRL-03 and prevents per-run SDK control |
| SSE typed events | Poll-only status updates | Loses stage-level granularity and increases backend polling load |
| Shared backend config model | Separate frontend/SDK config models | High drift risk and contract mismatch between surfaces |

**Installation:**
```bash
# No new dependencies required for Phase 4 implementation.
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── backend/
│   ├── schemas/agent.py                 # Request/response contracts (add runtime_config)
│   ├── routers/agent.py                 # API adapters frontend -> SDK
│   ├── agent_search/public_api.py       # SDK surface + config entrypoint
│   ├── agent_search/config.py           # RuntimeConfig sections (add query expansion section)
│   ├── agent_search/runtime/runner.py   # Propagate per-run config into runtime execution
│   └── services/agent_service.py        # Node callsites consume effective config
└── frontend/
    └── src/
        ├── utils/api.ts                 # Typed run payload with runtime_config
        └── App.tsx                      # UI toggles + sub_answer rendering/state
```

### Pattern 1: Single run-options contract across all surfaces
**What:** Define one backend-owned `runtime_config` shape used by both frontend API and SDK.  
**When to use:** Any retrieval behavior that must be configurable per run.  
**Example:**
```python
# Source: project pattern, implemented in schemas + SDK + router
class RuntimeAgentRunRequest(BaseModel):
    query: str = Field(min_length=1)
    thread_id: str | None = None
    runtime_config: dict[str, Any] | None = None
```

### Pattern 2: SDK-first parameterization, UI maps to it
**What:** SDK accepts run parameters as config, frontend toggles are a presentation layer that maps to same config.  
**When to use:** CTRL-03 requirement (no UI coupling in SDK).  
**Example:**
```python
# Source: project pattern in public_api.py
advanced_rag(
    query,
    vector_store=vector_store,
    model=model,
    config={
        "thread_id": thread_id,
        "runtime_config": {
            "rerank": {"enabled": True},
            "query_expansion": {"enabled": False},
        },
    },
)
```

### Pattern 3: Typed SSE event handling for runtime updates
**What:** Use `addEventListener(eventType, ...)` for named SSE events, not only `onmessage`.  
**When to use:** Any frontend stream for lifecycle events (`stage.completed`, `run.completed`, etc.).  
**Example:**
```typescript
// Source: MDN EventSource + existing frontend api.ts pattern
const source = new EventSource(`/api/agents/run-events/${jobId}`);
source.addEventListener("stage.completed", onEvent);
source.addEventListener("run.completed", onEvent);
source.onmessage = onEvent; // still useful for unnamed fallback messages
```

### Anti-Patterns to Avoid
- **UI-owned semantics:** Do not encode retrieval behavior flags only in frontend state names; backend/SDK contract must remain canonical.
- **Env-only control path:** Do not keep query expansion/rerank as process-wide env-only switches for this phase.
- **Split contracts by surface:** Do not implement one shape for frontend and another for SDK.
- **Polling fallback as primary:** Keep SSE as primary run update source; polling is secondary/debug.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request validation for nested run options | Custom dict parsing and manual type checks | Pydantic request models and nested config dataclasses | Prevents drift, gives automatic API validation/errors |
| SSE event protocol parsing | Custom text stream parser in frontend | Native `EventSource` with typed listeners | Browser-native reconnect/event model with simpler code |
| Per-surface config translation layers | Separate business logic in UI and SDK | Shared backend `runtime_config` contract | Enforces CTRL-03 and avoids divergence |

**Key insight:** Most complexity here is contract consistency and plumbing, not novel algorithms. Reuse existing model/stream infrastructure.

## Common Pitfalls

### Pitfall 1: Config parsed but ignored at runtime
**What goes wrong:** SDK/router accept config but runtime continues using env defaults.  
**Why it happens:** Current `RuntimeConfig.from_dict(config)` call is logged but not injected into runtime execution path.  
**How to avoid:** Add explicit `runtime_config` argument through `public_api` -> runtime runner -> node invocations (`expand`, `rerank`, search knobs if needed).  
**Warning signs:** Tests pass for schema acceptance but rerank/query-expansion behavior never changes between runs.

### Pitfall 2: Query expansion toggle coupled to rerank toggle
**What goes wrong:** One checkbox accidentally controls both features.  
**Why it happens:** Shared local UI state or merged payload serializer.  
**How to avoid:** Keep independent booleans and independent backend config paths (`query_expansion.enabled`, `rerank.enabled`).  
**Warning signs:** Payload snapshots show one field missing or mirrored values.

### Pitfall 3: Sub-answer regressions during contract evolution
**What goes wrong:** `sub_qa` disappears from async events or final result mapping.  
**Why it happens:** Request/response refactors touch model defaults or serialization logic.  
**How to avoid:** Add explicit regression tests for `sub_qa` presence in status + stream + final result.  
**Warning signs:** UI shows "No subanswers yet" on successful runs where backend generated answers.

### Pitfall 4: SSE handling only via `onmessage`
**What goes wrong:** Named lifecycle events are missed in real browser behavior.  
**Why it happens:** Assuming all events are unnamed message events.  
**How to avoid:** Register `addEventListener(...)` for named lifecycle events (already partially implemented; keep it).  
**Warning signs:** Network stream contains `event:` fields but state updates are incomplete.

## Code Examples

Verified/adapted patterns for this phase:

### Add run options to frontend start request
```typescript
// Source: current src/frontend/src/utils/api.ts startAgentRun pattern (adapted)
export async function startAgentRun(
  query: string,
  runtimeConfig?: {
    rerank?: { enabled?: boolean };
    query_expansion?: { enabled?: boolean };
  },
) {
  return requestJson("/api/agents/run-async", {
    method: "POST",
    payload: { query, runtime_config: runtimeConfig },
    validate: isRuntimeAgentRunAsyncStartResponse,
  });
}
```

### Resolve effective node config from runtime config (backend)
```python
# Source: current runtime node/service pattern (adapted)
effective_expand_config = runtime_config.query_expansion.to_query_expansion_config(default=_QUERY_EXPANSION_CONFIG)
expand_output = run_expand_node(
    node_input=...,
    model=model,
    config=effective_expand_config,
    callbacks=callbacks,
)

effective_rerank_config = runtime_config.rerank.to_reranker_config(default=_RERANKER_CONFIG)
rerank_output = run_rerank_node(
    node_input=...,
    config=effective_rerank_config,
    callbacks=callbacks,
)
```

### Preserve sub-answer rendering from streamed and terminal events
```typescript
// Source: current App.tsx applyRunEventData pattern
if (lifecycleEvent.sub_qa) setRunSubQa(lifecycleEvent.sub_qa);
if (lifecycleEvent.result && mapBackendStageToCanonical(lifecycleEvent.stage) === "final") {
  setLastSuccessfulSynthesis(lifecycleEvent.result);
  setRunSubQa(lifecycleEvent.result.sub_qa);
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Process-wide env toggles for retrieval behavior | Per-run runtime config contract | Ongoing migration (current code has partial RuntimeConfig support) | Enables operator controls and SDK parity |
| Polling-heavy run updates | SSE typed lifecycle events | Already implemented in current app | Better progressive UX and lower polling churn |
| Final-answer-only UX | Full staged runtime + sub-answer visibility | Already implemented in current app | Better retrieval/debug transparency |

**Deprecated/outdated:**
- Treating retrieval controls as environment-only operational flags for interactive runs.
- Assuming `onmessage` alone is sufficient for all SSE lifecycle events.

## Open Questions

1. **Exact request shape for runtime options in public API**
   - What we know: `config` exists in SDK, and router currently only forwards `thread_id`.
   - What's unclear: Whether to add top-level `runtime_config` in API payload or nest under existing `config`.
   - Recommendation: Use top-level `runtime_config` in API request model for explicit REST contract; map it into SDK `config` internally.

2. **Default behavior for query expansion when toggle is off**
   - What we know: Expansion currently normalizes and often includes original query.
   - What's unclear: Whether "off" should skip LLM expansion entirely but keep original query, or skip expand stage output changes.
   - Recommendation: Define "off" as deterministic pass-through `[sub_question]` only, with explicit provenance marker.

3. **SDK async parity beyond `run_async`**
   - What we know: `run_async` and `advanced_rag` both accept `config`.
   - What's unclear: Whether all async lifecycle APIs need to echo applied runtime config metadata.
   - Recommendation: For this phase, require behavior parity (controls affect run) but not config echo-back unless needed for debugging.

## Sources

### Primary (HIGH confidence)
- Project codebase:
  - `src/backend/agent_search/config.py` - existing runtime config structure and parsing
  - `src/backend/agent_search/public_api.py` - SDK config entrypoints
  - `src/backend/agent_search/runtime/runner.py` - runtime execution handoff path
  - `src/backend/services/agent_service.py` - expand/rerank node integration points
  - `src/backend/services/query_expansion_service.py` - expansion behavior and fallbacks
  - `src/backend/services/reranker_service.py` - rerank behavior and failure mode
  - `src/backend/schemas/agent.py` - run request/response schema
  - `src/frontend/src/utils/api.ts` - frontend run API contract + SSE subscription
  - `src/frontend/src/App.tsx` - sub-answer rendering and run-state wiring
  - `src/backend/tests/sdk/test_runtime_config.py` - config default/override expectations

### Secondary (MEDIUM confidence)
- [FastAPI Body - Nested Models](https://fastapi.tiangolo.com/tutorial/body-nested-models/) - nested request model guidance for run options.
- [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) - named event handling and API behavior.
- [MDN Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) - event stream format and custom event listeners.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - directly from project manifests and current implementation.
- Architecture: HIGH - derived from existing code paths plus official FastAPI/SSE docs.
- Pitfalls: HIGH - observed directly from current code/test gaps and contract boundaries.

**Research date:** 2026-03-13  
**Valid until:** 2026-04-12

