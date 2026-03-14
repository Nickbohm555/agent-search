# Architecture Research

**Domain:** Brownfield HITL checkpoints for an existing FastAPI + LangGraph-like advanced RAG pipeline with React + SDK mirror surfaces
**Researched:** 2026-03-13
**Confidence:** HIGH (LangChain/LangGraph HITL interrupt mechanics and required persistence), HIGH (current codebase boundaries), MEDIUM (exact payload shape recommendation for this milestone)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Client Experience Layer                                   │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  React app                                                                                  │
│    - starts async run (/api/agents/run-async)                                               │
│    - subscribes to SSE (/api/agents/run-events/{job_id})                                   │
│    - renders pause cards + approve/edit/deny + skip/no-HITL controls                        │
│                                                                                              │
│  SDK mirror (core + generated OpenAPI client)                                               │
│    - same request/response contracts as backend                                              │
│    - exposes typed resume payload helpers                                                    │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                   API / Contract Layer                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  FastAPI router (existing endpoints kept)                                                    │
│    POST /run-async     GET /run-status/{job_id}     GET /run-events/{job_id}               │
│    POST /run-resume/{job_id}                                                               │
│                                                                                              │
│  Contract mapper                                                                              │
│    - maps runtime pause/interrupt data to status + SSE payloads                              │
│    - preserves legacy behavior when HITL disabled                                            │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                               Runtime Orchestration Layer                                    │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  Runtime graph execution (existing)                                                          │
│    decompose -> expand -> search -> rerank -> answer -> synthesize                          │
│                                                                                              │
│  HITL gateway node logic (new, narrow scope)                                                 │
│    - checkpoint: subquestions_ready                                                          │
│    - checkpoint: query_expansion_ready (per lane/subquestion)                                │
│    - emits interrupt payload + pauses job                                                    │
│    - resumes with decision list (approve/edit/reject)                                        │
│                                                                                              │
│  Job controller (existing async jobs + resume path)                                          │
│    - stores interrupt payload + checkpoint id                                                 │
│    - enforces resume transition only from paused                                              │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                   Persistence Layer                                          │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  Postgres runtime tables + checkpoint link + idempotency effects                             │
│  LangGraph PostgresSaver checkpoint data                                                      │
│  pgvector retrieval data                                                                       │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| React workflow UI | Render pending reviews, collect approve/edit/deny/skip decisions, continue showing existing stage timeline | Extend existing `run-events` listener and add a compact review panel keyed by `job_id` + interrupt payload |
| Frontend API client | Keep API usage stable while adding optional HITL payloads | Extend existing `RuntimeAgentRunRequest`, `RuntimeAgentRunAsyncStatusResponse`, `RuntimeLifecycleEvent` guards |
| FastAPI router | Keep endpoint topology stable and delegate only | Reuse existing `/run-async`, `/run-status`, `/run-events`, `/run-resume` with expanded schemas |
| Runtime job manager | Own lifecycle state (`running`, `paused`, `success`, etc.) and checkpoint resume transitions | Existing `AgentRunJobStatus` plus structured `interrupt_payload` + reviewer metadata |
| Runtime graph / nodes | Generate subquestions and query expansions; pause only at configured checkpoints | Existing graph execution plus two explicit HITL checkpoints (no full graph redesign) |
| HITL decision normalizer | Validate decision order and allowed actions per checkpoint; map UI/SDK payload to runtime resume input | New utility module near runtime resume logic |
| SDK core mirror | Mirror backend schema and convenience methods | `sdk/core` schema parity + helper methods for resume decisions |
| Generated Python SDK | Preserve OpenAPI compatibility for external users | regenerate `sdk/python/openapi_client` from updated backend OpenAPI |

## Recommended Project Structure

```
src/
├── backend/
│   ├── routers/agent.py                           # Keep endpoint set unchanged; add optional HITL fields
│   ├── schemas/agent.py                           # Canonical API contract additions (hitl + sub_answers + prompts)
│   └── agent_search/runtime/
│       ├── jobs.py                                # pause/resume state machine and interrupt payload persistence
│       ├── runner.py                              # checkpointed invoke + Command(resume=...)
│       ├── resume.py                              # resume transition and payload validation helpers
│       ├── lifecycle_events.py                    # SSE event typing for stage.interrupted/run.paused + review payloads
│       └── hitl/
│           ├── policy.py                          # where HITL is enabled: subquestions + query expansion
│           ├── payloads.py                        # interrupt request/decision schema objects
│           └── apply_decisions.py                 # approve/edit/reject logic per checkpoint
├── frontend/src/
│   ├── utils/api.ts                               # type guards + request payloads + resume request body
│   └── App.tsx                                    # pause card, decision forms, resume trigger, no-HITL path
└── sdk/
    ├── core/src/schemas/agent.py                 # mirror backend schema changes exactly
    └── python/openapi_client/                    # regenerated models/apis from OpenAPI
```

### Structure Rationale

- **`runtime/hitl/` as a thin slice:** keeps HITL logic isolated from retrieval/synthesis business logic and avoids platform redesign.
- **Router and endpoint stability:** existing clients continue to function when HITL is off.
- **Schema-first mirror discipline:** backend schema is source of truth; frontend guards and SDK mirrors follow.
- **Pause logic near runtime jobs:** aligns with current `run.paused` lifecycle and `resume_agent_run_job` flow.

## Architectural Patterns

### Pattern 1: Explicit HITL Checkpoint Objects (not ad-hoc dicts)

**What:** Represent each review checkpoint as a typed object with checkpoint type, action requests, allowed decisions, and prompt text.
**When to use:** Always for pause surfaces consumed by API + UI + SDK.
**Trade-offs:** Slightly more schema work; major reduction in contract drift across backend/frontend/SDK.

**Example:**
```python
class HitlActionRequest(BaseModel):
    action_id: str
    checkpoint: Literal["subquestions", "query_expansion"]
    lane_sub_question: str | None = None
    payload: dict[str, Any]  # proposed subquestions or expanded queries
    allowed_decisions: list[Literal["approve", "edit", "reject"]]
    prompt: str

class HitlInterruptPayload(BaseModel):
    checkpoint_id: str
    thread_id: str
    requests: list[HitlActionRequest]
```

### Pattern 2: Resume Decisions Are Ordered and Deterministic

**What:** Require decisions in request order, mirroring LangChain HITL middleware and LangGraph interrupt semantics.
**When to use:** Multiple pending actions in the same pause (especially query expansion fan-out).
**Trade-offs:** More strict validation; avoids non-deterministic replay and wrong action-to-decision mapping.

**Example:**
```python
class HitlDecision(BaseModel):
    type: Literal["approve", "edit", "reject"]
    edited_payload: dict[str, Any] | None = None
    message: str | None = None

class RuntimeAgentRunResumeRequest(BaseModel):
    resume: dict[str, Any] = {
        "checkpoint_id": "...",
        "decisions": [{"type": "approve"}],
    }
```

### Pattern 3: Preserve Legacy Fast Path (HITL Disabled)

**What:** If HITL config is absent/disabled, runtime never emits interrupt payload and finishes exactly as before.
**When to use:** Brownfield rollout and backwards compatibility.
**Trade-offs:** Dual path to test; no behavior regression for existing consumers.

**Example:**
```python
if not hitl_config.enabled_for("subquestions"):
    return continue_without_pause()

interrupt_payload = build_subquestion_review_payload(...)
return pause_with_interrupt(interrupt_payload)
```

### Pattern 4: Side-Effect Discipline Around Interrupts

**What:** Ensure all side effects before interrupt are idempotent or deferred until after approval.
**When to use:** Any checkpoint node that may re-run on resume.
**Trade-offs:** Requires careful node boundaries; prevents duplicate writes and replay divergence.

## Data Flow

### Request Flow (HITL Off: unchanged)

```
React/SDK start run
    ↓
POST /api/agents/run-async
    ↓
jobs._run_agent_job(...)
    ↓
execute_runtime_graph / run_checkpointed_agent
    ↓
decompose -> expand -> search -> rerank -> answer -> synthesize
    ↓
SSE stage.completed ... run.completed
    ↓
UI renders final result + sub_answers
```

### Pause/Resume Flow (HITL On)

```
1) Runtime reaches checkpoint (subquestions or query expansion)
    ↓
2) Build interrupt payload:
      - checkpoint_id
      - requests[] with proposed output + allowed decisions + prompt
    ↓
3) Runtime pauses (LangGraph interrupt/checkpoint persisted by thread_id)
    ↓
4) Job status -> paused, message updated, interrupt_payload stored
    ↓
5) SSE emits stage.interrupted then run.paused
    ↓
6) UI/SDK shows review form and sends POST /api/agents/run-resume/{job_id}
      resume = { checkpoint_id, decisions:[approve|edit|reject ...] }
    ↓
7) Runtime validates transition + decisions, resumes with Command(resume=...)
    ↓
8) Runtime applies edited/approved/rejected result and continues graph
    ↓
9) SSE continues normal stage events and ends with run.completed or run.failed
```

### API Contract Data Flow

1. **Start request (`/run-async`):**
   - Add optional HITL config:
     - enable/disable by checkpoint (`subquestions`, `query_expansion`)
     - decision policy (`approve/edit/reject`)
     - custom prompt text per checkpoint
     - explicit `mode="off"` (skip/no-HITL).
2. **Status response (`/run-status/{job_id}`):**
   - Continue existing fields.
   - Add optional `interrupt_payload` when paused.
   - Keep `sub_qa` and add alias/read-model `sub_answers` for consumers.
3. **SSE events (`/run-events/{job_id}`):**
   - Keep existing events.
   - Ensure interrupted payload is included in `stage.interrupted` / `run.paused`.
4. **Resume request (`/run-resume/{job_id}`):**
   - Replace untyped `Any` usage with typed decision envelope while still accepting legacy truthy resume for compatibility.

### SDK + UI Workflow Flow

- SDK accepts same optional HITL and prompt config on run start.
- SDK exposes typed helper for decisions:
  - `approve(action_id)`
  - `edit(action_id, payload)`
  - `reject(action_id, message)`
- React UI reads `interrupt_payload` from status/SSE and renders:
  - per-action prompt
  - editable payload text areas/chips
  - deny reason input
  - skip/no-HITL toggle before start.
- Existing timeline stays intact; pause is a new terminal-intermediate state, not a new endpoint model.

## Build Order and Dependency Chain

1. **Contract primitives first (blocking):**
   - Define `HitlInterruptPayload`, `HitlDecision`, optional run config, and `sub_answers` response alias in backend schemas.
   - Mirror same shapes in `sdk/core` and frontend type guards.
2. **Runtime pause points second:**
   - Add checkpoint builders for `subquestions_ready` and `query_expansion_ready`.
   - Integrate pause outcome into existing `jobs.py` status + lifecycle path.
3. **Resume validator third:**
   - Implement deterministic decision validation/order checks and allowed-decision enforcement.
   - Keep fallback compatibility for legacy `resume=True`.
4. **SSE/status projection fourth:**
   - Emit structured interrupted payload in `stage.interrupted` and `run.paused`.
   - Add `interrupt_payload` to status response.
5. **UI workflow fifth:**
   - Add pause cards and decision submission in React.
   - Preserve current flow when no interrupt payload is present.
6. **SDK ergonomics sixth:**
   - Add typed resume helpers and OpenAPI regeneration.
7. **Hardening/tests seventh:**
   - Matrix tests for off/on, approve/edit/reject, invalid order, skipped HITL, and thread-id resume continuity.

## Anti-Patterns

### Anti-Pattern 1: Global "pause everything" switch

**What people do:** pause every stage once HITL is enabled.
**Why it's wrong:** high operator burden, poor latency, and scope creep.
**Do this instead:** restrict to requested checkpoints only (`subquestions`, `query_expansion`) with per-checkpoint policy.

### Anti-Pattern 2: Unstructured resume payloads

**What people do:** pass raw arbitrary objects to `resume`.
**Why it's wrong:** impossible to validate safely, brittle SDK/UI parity.
**Do this instead:** typed decision envelopes with explicit checkpoint ID and ordered decisions.

### Anti-Pattern 3: Breaking default behavior

**What people do:** make HITL mandatory once implemented.
**Why it's wrong:** regresses existing workloads and external SDK consumers.
**Do this instead:** keep HITL opt-in and preserve old behavior when disabled.

### Anti-Pattern 4: Mutating non-idempotent state before interrupt

**What people do:** side effects before pause in a node that re-runs on resume.
**Why it's wrong:** duplicate writes and replay drift.
**Do this instead:** move side effects after review or guard with idempotency ledger.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| LangChain HITL middleware + LangGraph interrupts | Pause on configured actions, resume via `Command(resume=...)` | Align decision ordering and allowed decision types with official HITL behavior |
| LangGraph checkpointer (PostgresSaver) | Persist pause state keyed by `thread_id` | Required for safe pause/resume in async jobs |
| Postgres runtime metadata/idempotency tables | Persist checkpoint links and interrupt metadata | Already present in runtime job persistence flow |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `runtime/graph/*` -> `runtime/jobs.py` | callback events + outcome object | graph computes, jobs own lifecycle state and pause status |
| `runtime/jobs.py` -> `routers/agent.py` | typed status/response schemas | router remains thin, no decision logic |
| `routers/agent.py` -> frontend/sdk | existing endpoints + additive fields | no endpoint proliferation required |
| backend schemas -> sdk core -> generated SDK -> frontend guards | schema mirroring pipeline | single-source contract discipline prevents drift |

## Sources

- [LangChain Human-in-the-Loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) (required primary source, HIGH)
- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) (official, HIGH)
- [LangGraph `interrupt` reference](https://reference.langchain.com/python/langgraph/types/interrupt) (official API behavior, HIGH)
- Existing project architecture and contracts in:
  - `src/backend/routers/agent.py`
  - `src/backend/agent_search/runtime/jobs.py`
  - `src/backend/agent_search/runtime/runner.py`
  - `src/backend/agent_search/runtime/lifecycle_events.py`
  - `src/frontend/src/utils/api.ts`
  - `src/frontend/src/App.tsx`
  - `sdk/core/src/schemas/agent.py`

---
*Architecture research for: HITL checkpoints in brownfield advanced RAG*
*Researched: 2026-03-13*
