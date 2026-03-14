# Phase 02: Subquestion HITL End-to-End - Research

**Researched:** 2026-03-13  
**Domain:** Subquestion human-in-the-loop checkpointing in existing async runtime  
**Confidence:** HIGH (repo touchpoints), MEDIUM (final payload shape decisions pending confirmation)

## Summary

Phase 2 should add a single, explicit checkpoint immediately after `decompose` and before lane execution (`expand/search/rerank/answer`). The repo already has the async job/SSE lifecycle shell (`run-events`, `run.paused`, `run-resume`) and a place to store pause metadata (`interrupt_payload`, `checkpoint_id`), but it does not yet implement subquestion-specific decision contracts (approve/edit/deny/skip) or a frontend review-and-resume workflow.

The most planning-critical fact: current async first-run flow executes `execute_runtime_graph(...)` when `resume is None`; pause behavior is only wired through `run_checkpointed_agent(...)` in the resume branch. Phase 2 planning must include how initial runs can actually pause at the subquestion checkpoint and resume deterministically from that checkpoint.

**Primary recommendation:** implement a typed subquestion HITL decision envelope and route all HITL-enabled runs through the checkpoint-capable execution path while preserving default non-HITL behavior when omitted/disabled.

## Standard Stack

No new framework is required for Phase 2. Use existing stack/components:

### Core
| Library/Module | Current use | Phase 2 use |
|---|---|---|
| FastAPI router (`src/backend/routers/agent.py`) | Run/start/status/events/resume endpoints | Add additive request/response fields only; keep endpoint topology unchanged |
| Pydantic schemas (`src/backend/schemas/agent.py`) | Runtime request/status/resume contracts | Add typed subquestion HITL config + typed resume decisions + paused payload shape |
| Runtime jobs (`src/backend/agent_search/runtime/jobs.py`) | Async lifecycle/status/SSE event storage | Persist checkpoint payload and apply validated resume decisions |
| Runtime graph routes (`src/backend/agent_search/runtime/graph/routes.py`) | Decompose -> lane routing | Insert HITL checkpoint gate between decompose and lane fan-out |
| Frontend API/App (`src/frontend/src/utils/api.ts`, `src/frontend/src/App.tsx`) | Start run + subscribe SSE + render timeline | Add review UI state and submit resume decisions |

### Supporting
| Component | Why it matters |
|---|---|
| SDK core schemas (`sdk/core/src/schemas/agent.py`) | Must mirror backend schema changes for API/SDK parity (SQH-01) |
| Existing API/SDK tests | Provide regression harness for contract-safe additive changes |

## Architecture Patterns

### Recommended project touchpoints (Phase 2 scope only)
| Area | Likely files/services | Planned change |
|---|---|---|
| API request contract | `src/backend/schemas/agent.py`, `src/backend/routers/agent.py` | Add optional subquestion HITL enablement fields (default-off) |
| Checkpoint gating | `src/backend/agent_search/runtime/graph/routes.py`, `.../graph/builder.py`, `.../graph/execution.py` | Pause after decompose when enabled; continue directly when disabled/skip |
| Pause state + resume | `src/backend/agent_search/runtime/jobs.py`, `.../resume.py`, `.../runner.py` | Store typed interrupt payload; validate/apply approve/edit/deny decisions |
| SSE/status contract | `src/backend/agent_search/runtime/lifecycle_events.py`, `.../jobs.py`, `src/frontend/src/utils/api.ts` | Include checkpoint payload in paused/interrupted lifecycle data |
| Frontend review workflow | `src/frontend/src/App.tsx`, `src/frontend/src/utils/api.ts` | Render pending subquestions, capture edits/denials, call `/run-resume/{job_id}` |
| SDK parity | `sdk/core/src/schemas/agent.py` | Mirror request/resume/status additions |

### Pattern 1: Single checkpoint before lane fan-out
- **What:** Gate at `subquestions_ready` (post-decompose, pre-lane).
- **Why:** Meets SQH-02/03/04 with minimal graph surface area and avoids per-lane HITL complexity in this phase.
- **How:** If HITL disabled or explicitly skipped, route exactly as current behavior.

### Pattern 2: Typed decisions, not raw `Any`
- **What:** Replace implicit `resume: Any` usage in practice with a typed envelope (`checkpoint_id`, `decisions[]`, action type + optional edited value).
- **Why:** Prevents action mismatch and makes frontend/SDK/API behavior deterministic.
- **How:** Keep legacy `resume=True` fallback accepted for compatibility where needed.

### Pattern 3: Additive contract evolution
- **What:** Only additive fields in run request/status/SSE payloads.
- **Why:** Phase 2 depends on compatibility guarantees from Phase 1 and must preserve non-HITL path.

## API/SSE Contract Considerations

1. **Start request (`POST /api/agents/run-async`)**
   - Add optional subquestion HITL config (enable/disable mode).
   - Omitted fields must preserve existing default flow (SQH-05).

2. **Resume request (`POST /api/agents/run-resume/{job_id}`)**
   - Needs typed decision payload for:
     - approve proposed subquestions (SQH-02)
     - edit values before continue (SQH-03)
     - deny selected items, no mandatory feedback text (SQH-04)

3. **Status + SSE**
   - Existing stream already supports named events and `run.paused`.
   - Add structured checkpoint payload to paused/interrupted events so frontend can render and submit decisions without extra polling contract hacks.

4. **Event behavior**
   - Frontend currently listens with `addEventListener(...)` and maps `run.paused` as terminal.
   - Phase 2 needs a "paused-and-actionable" UX state (not just generic error state) when pause is expected.

## Frontend Workflow Considerations

- Keep existing run timeline UI and add a compact "Subquestion Review" panel when paused payload is present.
- Allow per-item action:
  - Approve unchanged
  - Edit text
  - Deny (no required reason text)
- Submit decisions via `/run-resume/{job_id}` and resume SSE stream continuity.
- Preserve current no-HITL UX when no checkpoint payload exists.
- Prevent stale decision submission by binding decisions to `job_id` + `checkpoint_id`.

## Don't Hand-Roll

| Problem | Don't build | Use instead |
|---|---|---|
| Separate pause queue service | New side channel queue/state machine | Existing `AgentRunJobStatus` + `interrupt_payload` + checkpoint link path |
| New transport for runtime updates | Parallel websocket/status channel | Existing SSE `/api/agents/run-events/{job_id}` typed events |
| Ad hoc resume parser | Free-form dict mutation in handlers | Typed Pydantic resume decision models with validation |

## Common Pitfalls

### Pitfall 1: Initial runs never pause
- **Cause:** first-run path uses `execute_runtime_graph(...)`, while checkpointed pause/resume path is only in resume branch.
- **Mitigation:** explicitly plan execution-path alignment for HITL-enabled runs.

### Pitfall 2: Decision/order mismatch
- **Cause:** multiple subquestions edited/denied without deterministic identity mapping.
- **Mitigation:** include stable item IDs or index-locked mapping in checkpoint payload.

### Pitfall 3: Breaking default behavior
- **Cause:** making checkpoint mandatory or changing default request semantics.
- **Mitigation:** enforce default-off and additive-only schema changes (SQH-05).

### Pitfall 4: Paused state treated as failure in UI
- **Cause:** current `run.paused` handling maps to error-like terminal behavior.
- **Mitigation:** add explicit paused-review state and continue/resume action.

## Testing Strategy (Phase 2)

### Backend
- **Contract tests**
  - `run-async` accepts HITL params + omitted params still work (SQH-01, SQH-05).
  - `run-resume` validates approve/edit/deny shapes and transition status codes.
- **Runtime tests**
  - Pauses at subquestion checkpoint when enabled.
  - Approve resumes with unchanged list (SQH-02).
  - Edit resumes with edited list (SQH-03).
  - Deny omits denied entries without required feedback field (SQH-04).
  - Disabled/skip path bypasses pause and completes normally (SQH-05).
- **SSE tests**
  - Paused/interrupted events carry checkpoint payload and terminal `run.paused`.

### Frontend
- **Component/integration tests (`App.test.tsx`)**
  - Renders review UI on paused payload.
  - Approve/edit/deny interactions build correct resume payload.
  - Resume transitions back to running and ultimately completed states.
  - Non-HITL run path remains unchanged.

### Suggested acceptance mapping
| Requirement | Verification |
|---|---|
| SQH-01 | API + SDK request accepts/propagates subquestion HITL enablement |
| SQH-02 | Approve path resumes with proposed subquestions |
| SQH-03 | Edit path resumes with edited subquestions |
| SQH-04 | Deny path omits denied items, no mandatory feedback |
| SQH-05 | Skip/disabled path behaves like current default run |

## Key Risks and Dependencies

- **Dependency on Phase 1:** additive request contract/default-off behavior must already exist and remain stable.
- **Execution-path risk:** pause/resume capability must be available on initial HITL-enabled runs, not only on explicit resume branch.
- **Cross-surface drift risk:** backend schema, frontend type guards, and SDK schema must be updated together.
- **Event-state risk:** paused lifecycle semantics must not be conflated with failure.

## Assumptions to Confirm Before Execution

1. Phase 1 delivered the additive control field baseline used to enable subquestion HITL per run.
2. Subquestion checkpoint scope is exactly one gate after decompose (not per-lane/per-stage HITL).
3. Deny semantics mean omission only; no feedback/reason is required for acceptance.
4. `run-resume` remains the single resume endpoint (no new endpoint needed).
5. SDK mirror update for these fields is in scope for Phase 2 planning (at least schema parity).

## Code Examples

### Typed subquestion resume envelope (recommended shape)
```python
class SubquestionDecision(BaseModel):
    subquestion_id: str
    action: Literal["approve", "edit", "deny"]
    edited_value: str | None = None

class RuntimeAgentRunResumeRequest(BaseModel):
    resume: dict[str, Any]  # e.g. {"checkpoint_id": "...", "decisions": [...]}
```

### Pause-aware frontend state transition
```ts
if (event.event_type === "run.paused" && event.status === "paused") {
  setReviewPayload(event.interrupt_payload ?? null);
  setRunState("loading"); // paused-awaiting-user-action, not failed
}
```

## Sources

### Primary (HIGH confidence)
- Repo contracts and runtime flow:
  - `src/backend/schemas/agent.py`
  - `src/backend/routers/agent.py`
  - `src/backend/agent_search/runtime/jobs.py`
  - `src/backend/agent_search/runtime/graph/routes.py`
  - `src/backend/agent_search/runtime/graph/execution.py`
  - `src/backend/agent_search/runtime/lifecycle_events.py`
  - `src/frontend/src/utils/api.ts`
  - `src/frontend/src/App.tsx`
  - `sdk/core/src/schemas/agent.py`

### Supporting tests reviewed
- `src/backend/tests/api/test_agent_run.py`
- `src/backend/tests/api/test_run_events_stream.py`
- `src/backend/tests/sdk/test_public_api_async.py`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (existing stack/components already present)
- Architecture touchpoints: HIGH (directly traced in code)
- Final payload shape details: MEDIUM (requires phase execution decision)

**Research date:** 2026-03-13  
**Valid until:** 2026-04-12 (or until runtime contract changes)
