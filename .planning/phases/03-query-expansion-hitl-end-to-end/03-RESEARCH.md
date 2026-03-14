# Phase 03: Query Expansion HITL End-to-End - Research

**Researched:** 2026-03-13  
**Domain:** Query-expansion human-in-the-loop checkpointing in existing async runtime  
**Confidence:** HIGH (repo/runtime touchpoints), MEDIUM (final resume payload schema details)

## Summary

Phase 3 should introduce one explicit human checkpoint at query-expansion time, after expansion candidates are generated and before retrieval executes for each subquestion lane. This directly matches QEH-01..QEH-05: users can enable query-expansion HITL, review proposed expansions, approve/edit/deny, or skip and continue normal execution.

The project already has the required infrastructure: async jobs, SSE lifecycle events, pause/resume endpoints, checkpoint persistence, and thread-id continuity. What is missing is query-expansion-specific contract shape and runtime gating logic. The highest-leverage plan is to reuse the same pause/resume architecture used for subquestion HITL and add query-expansion-specific payloads and decision application in the `expand -> search` handoff.

**Primary recommendation:** implement a typed query-expansion checkpoint payload and typed resume decision envelope, then gate `search` on approved/edited expansion lists while preserving default non-HITL behavior when config is omitted/disabled.

## Standard Stack

The established libraries/tools for this phase:

### Core
| Library/Module | Version/Status | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI + Pydantic schemas (`src/backend/routers/agent.py`, `src/backend/schemas/agent.py`) | existing | Public contract for run/start/status/events/resume | Existing API surface; additive schema evolution keeps compatibility |
| LangGraph runtime execution + checkpoints (`src/backend/agent_search/runtime/graph/*`, `.../runner.py`, `.../persistence.py`) | existing | Pause/resume and graph progression | Already central orchestration layer for runtime stages |
| Runtime job manager + lifecycle events (`src/backend/agent_search/runtime/jobs.py`, `.../lifecycle_events.py`) | existing | Run status, SSE events, paused-state metadata | Already persists `interrupt_payload` and emits `run.paused`/`run.completed` |
| Query expansion node/service (`src/backend/agent_search/runtime/nodes/expand.py`, `src/backend/services/query_expansion_service.py`) | existing | Candidate expansion generation | Current source of proposed expansions and normalization |
| React + TypeScript EventSource client (`src/frontend/src/utils/api.ts`, `src/frontend/src/App.tsx`) | existing | Render and react to SSE lifecycle stream | Already listens to named SSE events with `addEventListener(...)` |

### Supporting
| Library/Module | Version/Status | Purpose | When to Use |
|---------|---------|---------|-------------|
| SDK mirror schemas (`sdk/core/src/schemas/agent.py`) | existing | Backend/SDK parity for request/resume/status contracts | Same phase as backend contract change to avoid drift |
| Existing API/SDK/runtime tests | existing | Contract and lifecycle regression harness | Required for QEH acceptance + compatibility safety |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SSE + existing `/run-events` | New websocket channel | Unnecessary transport complexity and contract duplication |
| Existing pause/resume endpoint | New query-expansion-only resume endpoint | Endpoint proliferation and split state machine risk |
| Typed decision schema | Raw `resume: Any` mutation | Faster short-term, but high validation and parity drift risk |

**Installation:**
```bash
# No new dependencies required for Phase 3 baseline
```

## Architecture Patterns

### Recommended Project Structure
```text
src/
├── backend/
│   ├── schemas/agent.py                         # add query-expansion HITL request/resume/status models
│   ├── routers/agent.py                         # keep endpoint set; wire additive contract fields
│   └── agent_search/runtime/
│       ├── graph/builder.py                     # add checkpoint gate between expand and search
│       ├── graph/execution.py                   # preserve lifecycle stream semantics for paused events
│       ├── jobs.py                              # persist query-expansion interrupt payload + paused state
│       └── resume.py                            # validate query-expansion decision envelopes
├── frontend/src/
│   ├── utils/api.ts                             # typed interrupt payload + resume payload guards
│   └── App.tsx                                  # paused review UI for expansion approve/edit/deny/skip
└── sdk/core/src/schemas/agent.py                # mirror backend models exactly
```

### Pattern 1: Stage-scoped checkpoint at expand->search boundary
**What:** Pause after `expand` output exists, before `search` consumes `expanded_queries`.  
**When to use:** Query-expansion HITL enabled for run/lane.  
**Example:**
```python
# Source: project runtime flow + LangGraph interrupt guidance
expanded = run_expand_node(...)
if query_expansion_hitl_enabled:
    decision_payload = interrupt(build_query_expansion_review_payload(expanded))
    expanded = apply_query_expansion_decisions(expanded, decision_payload)
search = run_search_node(expanded_queries=expanded.expanded_queries, ...)
```

### Pattern 2: Ordered typed decisions bound to checkpoint identity
**What:** Resume request includes `checkpoint_id` and ordered decisions tied to expansion items.  
**When to use:** Any pause that may involve edit/deny of multiple query expansions.  
**Example:**
```python
class QueryExpansionDecision(BaseModel):
    expansion_id: str
    action: Literal["approve", "edit", "deny"]
    edited_query: str | None = None

class RuntimeAgentRunResumeRequest(BaseModel):
    resume: dict[str, Any]  # {"checkpoint_id": "...", "decisions": [...]}
```

### Pattern 3: Additive, default-off contract evolution
**What:** Optional HITL fields only; omitted fields preserve current behavior.  
**When to use:** All API and SDK contract changes in this phase.  
**Example:**
```python
class RuntimeAgentRunRequest(BaseModel):
    query: str
    thread_id: str | None = None
    # optional, additive
    query_expansion_hitl: QueryExpansionHitlConfig | None = None
```

### Anti-Patterns to Avoid
- **Checkpoint after retrieval:** too late for QEH goal; retrieval would already have executed.
- **Unstructured `resume: Any` branching:** causes malformed edit/deny handling and weak API guarantees.
- **Treating `run.paused` as failure in UI:** blocks expected review-control flow.
- **Breaking lane determinism:** decision application must preserve lane/subquestion mapping.

## Architecture Touchpoints Likely to Change

1. `src/backend/schemas/agent.py`  
   - Add query-expansion HITL run config, checkpoint payload model, decision/resume model.
2. `src/backend/agent_search/runtime/graph/builder.py` and `src/backend/agent_search/runtime/graph/execution.py`  
   - Insert query-expansion checkpoint gate and preserve stage event emission around pause/resume.
3. `src/backend/agent_search/runtime/jobs.py` and `src/backend/agent_search/runtime/lifecycle_events.py`  
   - Persist/emit query-expansion interrupt payloads and paused status consistently.
4. `src/backend/routers/agent.py` and `src/backend/agent_search/public_api.py`  
   - Accept additive request fields and typed resume payloads end-to-end.
5. `src/frontend/src/utils/api.ts` and `src/frontend/src/App.tsx`  
   - Parse/render query-expansion review payload; submit approve/edit/deny/skip resume actions.
6. `sdk/core/src/schemas/agent.py`  
   - Mirror backend schema additions for SDK contract parity.

## API/Data Contract Implications

### Start Request (`POST /api/agents/run-async`)
- Add optional query-expansion HITL enablement config.
- Omitted config must keep default non-HITL path (QEH-05 + compatibility guarantees).

### Status + SSE (`GET /api/agents/run-status/{job_id}`, `GET /api/agents/run-events/{job_id}`)
- Include structured query-expansion review payload when paused.
- Keep current lifecycle event topology (`stage.*`, `run.paused`, `run.completed`) and additive fields only.

### Resume Request (`POST /api/agents/run-resume/{job_id}`)
- Validate typed decision envelope for:
  - approve expansions (QEH-02)
  - edit expansions before retrieval (QEH-03)
  - deny selected expansions without mandatory feedback (QEH-04)
  - skip checkpoint (QEH-05)
- Enforce paused-only transitions and checkpoint identity match.

### Data Shape Constraints
- Stable lane identity (`sub_question` and/or deterministic expansion IDs).
- Decisions must be order-safe and deterministic.
- Edited expansions must be normalized with existing query normalization rules (`max_query_length`, dedupe).

## Runtime/Event-Stream/Checkpoint Implications

### Runtime Execution
- Current graph executes `expand -> search` directly; Phase 3 adds interrupt-capable gate in that seam.
- `search` must consume post-decision expansion list, not raw model-generated list.

### Checkpointing and Resume
- Current runtime already supports `Command(resume=...)` and checkpointer-backed recovery.
- Phase 3 requires first-run HITL-enabled path to reach pause state (not only resume path mechanics).
- Node re-entry behavior must avoid duplicate side effects on resume.

### Event Stream
- Continue SSE named events; frontend already listens via `addEventListener(...)`.
- Ensure paused events include actionable review payload and terminal `run.paused`.
- Keep `Last-Event-ID` replay behavior intact for stream reconnection safety.

### Lifecycle Semantics
- `run.paused` is expected intermediate-terminal for reviewer action, not an error.
- After resume, new events should continue with same `run_id`/`thread_id` continuity.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pause orchestration queue | New custom pause broker/service | Existing LangGraph checkpointer + runtime jobs pause state | Existing stack already persists checkpoint and supports resume |
| Streaming transport | New websocket protocol | Existing SSE endpoint + named events | Already implemented/tested and browser-compatible |
| Resume decision parser | Ad-hoc dict parsing | Pydantic typed decision models | Strong validation, safer SDK/frontend parity |
| Query normalization variant | New normalization logic for edits | Existing query expansion normalization constraints | Prevents drift between generated and edited expansions |

**Key insight:** custom workflow plumbing here increases drift risk more than it adds value; reusing current runtime + SSE + checkpoint primitives is the safest path.

## Common Pitfalls

### Pitfall 1: Retrieval runs before human review
**What goes wrong:** expansion review arrives after `search` already used unreviewed queries.  
**Why it happens:** checkpoint inserted too late or not wired into `expand -> search` boundary.  
**How to avoid:** pause immediately after expand output, before search invocation.  
**Warning signs:** `search` stage snapshots/events appear before any `run.paused` for HITL-enabled runs.

### Pitfall 2: Invalid decision mapping across lanes
**What goes wrong:** edits/denials applied to wrong subquestion or wrong expansion item.  
**Why it happens:** decisions keyed by list index only without stable IDs/context.  
**How to avoid:** bind decisions to `checkpoint_id` + deterministic expansion IDs + lane identity.  
**Warning signs:** resumed runs show mismatched expansion text in artifacts.

### Pitfall 3: Pause treated as frontend failure
**What goes wrong:** UI shows disconnected/error state instead of review controls.  
**Why it happens:** `run.paused` handled like `run.failed`.  
**How to avoid:** explicit paused-review mode and resume submission path in UI state machine.  
**Warning signs:** `run.paused` events followed by no decision UI.

### Pitfall 4: Resume replay duplicates work
**What goes wrong:** duplicated side effects or inconsistent artifacts after resume.  
**Why it happens:** node code before interrupt re-runs and mutates non-idempotent state.  
**How to avoid:** keep pre-interrupt logic pure/idempotent, apply side effects post-decision.  
**Warning signs:** duplicate lifecycle stage records or conflicting artifact snapshots.

## Code Examples

Verified patterns from official/project sources:

### SSE named-event subscription (frontend)
```typescript
// Source: src/frontend/src/utils/api.ts
const eventSource = new EventSource(`${API_BASE_URL}/api/agents/run-events/${jobId}`);
eventSource.addEventListener("stage.completed", handleMessage as EventListener);
eventSource.addEventListener("run.paused", handleMessage as EventListener);
eventSource.addEventListener("run.completed", handleMessage as EventListener);
```

### Resume via `Command(resume=...)` (runtime pattern)
```python
# Source: LangGraph HITL docs + src/backend/agent_search/runtime/runner.py
if resume is not None:
    graph_input = build_resume_command(resume)  # wraps Command(resume=...)
result = graph.invoke(graph_input, config={"configurable": {"thread_id": run_metadata.thread_id}})
```

### FastAPI SSE stream response
```python
# Source: src/backend/routers/agent.py
return StreamingResponse(
    event_stream(),
    media_type="text/event-stream",
    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Poll-only status checks | SSE lifecycle stream + status endpoint | already in repo | Enables real-time review UX and better interruption handling |
| Linear no-review expansion flow | Stage-scoped HITL checkpoint at expand stage | this phase | Gives user control before retrieval executes |
| Untyped resume payload usage | Typed checkpoint decision envelopes | this phase | Deterministic behavior and safer API/SDK parity |

**Deprecated/outdated:**
- Treating `run.paused` as generic failure in UI: should be replaced with paused-review action flow for HITL-enabled runs.

## Test Strategy and Risks

### Backend
- Contract tests:
  - run request accepts optional query-expansion HITL config (QEH-01).
  - resume validates approve/edit/deny/skip payloads and transition rules.
- Runtime tests:
  - pause occurs before search when HITL enabled.
  - approve/edit/deny/skip semantics alter expansion list correctly (QEH-02..QEH-05).
  - default/off path bypasses pause and preserves existing behavior.
- SSE tests:
  - paused event includes actionable payload and terminal `run.paused`.
  - `Last-Event-ID` recovery still works with paused/resumed runs.

### Frontend
- API/type-guard tests:
  - parse new paused payload shape.
  - validate resume payload assembly for approve/edit/deny/skip.
- App integration tests:
  - render review panel on pause.
  - submit decisions and return to running/completed timeline.
  - non-HITL runs unchanged.

### Risks to plan for
- Execution-path gap: ensure HITL-enabled first run can actually pause.
- Cross-surface drift: backend schema, frontend guards, and SDK mirror must land together.
- Determinism risk: decision IDs/order mismatch in multi-item expansion sets.

## Concrete Planning Inputs (Implementation Sections)

Use these as atomic implementation sections for planning:

1. **Section A - Query Expansion HITL Contract Additions**  
   Single deliverable: additive backend+SDK schema updates for run config, paused payload, and resume decisions.
2. **Section B - Runtime Expand Checkpoint Gate**  
   Single deliverable: insert and wire pause/resume gate at `expand -> search` boundary with deterministic decision application.
3. **Section C - Lifecycle Event + Status Projection**  
   Single deliverable: emit and persist query-expansion actionable paused payloads in status and SSE.
4. **Section D - Frontend Review/Resume UX**  
   Single deliverable: render expansion review controls and submit typed resume actions.
5. **Section E - End-to-End Validation Matrix**  
   Single deliverable: automated tests for QEH-01..QEH-05 plus compatibility regression checks.

## Open Questions

1. **Checkpoint granularity for Phase 3**
   - What we know: requirement says review expansions before retrieval executes.
   - What's unclear: single batch pause for all lanes vs lane-by-lane pause UX.
   - Recommendation: choose one-batch pause first for v1 simplicity unless UX explicitly requires per-lane staging.

2. **Edit validation strictness**
   - What we know: edits are allowed and should affect retrieval.
   - What's unclear: minimum/maximum edit constraints beyond existing normalization.
   - Recommendation: enforce existing normalization + non-empty checks in v1, defer richer validation rules.

3. **Pause timeout policy**
   - What we know: current system supports paused state and resume.
   - What's unclear: operational timeout/escalation behavior for long-unanswered checkpoints.
   - Recommendation: document explicit v1 behavior (indefinite pause or fixed timeout) before implementation.

## Sources

### Primary (HIGH confidence)
- Repository runtime and contract files:
  - `src/backend/schemas/agent.py`
  - `src/backend/routers/agent.py`
  - `src/backend/agent_search/runtime/graph/builder.py`
  - `src/backend/agent_search/runtime/graph/execution.py`
  - `src/backend/agent_search/runtime/jobs.py`
  - `src/backend/agent_search/runtime/runner.py`
  - `src/backend/agent_search/runtime/lifecycle_events.py`
  - `src/backend/services/query_expansion_service.py`
  - `src/frontend/src/utils/api.ts`
  - `src/frontend/src/App.tsx`
  - `sdk/core/src/schemas/agent.py`
- Official docs:
  - [LangGraph human-in-the-loop interrupts](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/wait-user-input/)
  - [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
  - [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)

### Secondary (MEDIUM confidence)
- Existing phase and project planning docs:
  - `.planning/ROADMAP.md`
  - `.planning/REQUIREMENTS.md`
  - `.planning/STATE.md`
  - `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all core mechanisms already exist in repo and official docs
- Architecture: HIGH - concrete file-level touchpoints and execution seam identified
- Pitfalls/risks: MEDIUM - final payload granularity/timeout policy still to be decided in planning

**Research date:** 2026-03-13  
**Valid until:** 2026-04-12 (or until runtime lifecycle/schema changes)
