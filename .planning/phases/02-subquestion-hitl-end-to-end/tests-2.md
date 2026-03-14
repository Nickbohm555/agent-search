---
status: completed
phase: "2 - subquestion-hitl-end-to-end"
source:
  - 02-01-SUMMARY.md
  - 02-02-SUMMARY.md
  - 02-03-SUMMARY.md
  - 02-04-SUMMARY.md
started: "2026-03-13"
updated: "2026-03-14"
---

## Current Test

Test 3 - Resume with approve/edit/deny/skip decisions completes run deterministically.

## Information Needed from the Summary

- `what_changed`
  - Async run contracts now support additive `hitl.subquestions.enabled` without changing default behavior when HITL is omitted.
  - Resume contracts now accept typed envelopes with `checkpoint_id` and per-subquestion `approve`/`edit`/`deny`/`skip` decisions, while legacy `resume=True` and object payloads remain valid.
  - Runtime now pauses once at `subquestions_ready` for HITL-enabled runs, emits paused lifecycle/SSE metadata (`checkpoint_id`, `interrupt_payload`), and deterministically applies decisions on resume.
  - Frontend now treats `run.paused` as actionable review state and submits typed resume payloads; non-HITL UX path remains unchanged.
  - SDK now exposes typed HITL request/resume schemas and forwards async controls through the same run/status/resume topology.
- `files_changed`
  - `src/backend/agent_search/config.py`
  - `src/backend/agent_search/public_api.py`
  - `src/backend/schemas/__init__.py`
  - `src/backend/schemas/agent.py`
  - `src/backend/agent_search/runtime/graph/builder.py`
  - `src/backend/agent_search/runtime/graph/routes.py`
  - `src/backend/agent_search/runtime/graph/state.py`
  - `src/backend/agent_search/runtime/jobs.py`
  - `src/backend/agent_search/runtime/lifecycle_events.py`
  - `src/backend/agent_search/runtime/resume.py`
  - `src/backend/agent_search/runtime/runner.py`
  - `src/frontend/src/utils/api.ts`
  - `src/frontend/src/App.tsx`
  - `src/frontend/src/App.test.tsx`
  - `src/frontend/src/styles.css`
  - `sdk/core/src/schemas/agent.py`
  - `sdk/core/src/schemas/__init__.py`
  - `src/backend/tests/api/test_agent_run.py`
  - `src/backend/tests/api/test_run_events_stream.py`
  - `src/backend/tests/services/test_agent_service.py`
  - `src/backend/tests/sdk/test_public_api_async.py`
  - `src/backend/tests/sdk/test_sdk_async_e2e.py`
- `code_areas`
  - Backend API schema validation and async/resume request parsing.
  - Runtime checkpoint gate placement and resume decision application.
  - SSE lifecycle payload emission for paused and resumed states.
  - Frontend paused-state rendering, review controls, and typed resume request construction.
  - SDK typed schema surface and async API forwarding.
- `testing_notes`
  - Container test paths in summaries were corrected from `src/backend/tests/...` to `tests/...` during verification.
  - Existing verification indicates backend API/runtime/SDK and frontend test suites already exercised target behaviors; this UAT file focuses on black-box observable outcomes.

## Tests

### Test 1: Async run accepts additive subquestion HITL control and remains backward compatible

**Given** the API is running and a valid async run request payload is available  
**When** I submit an async run with `hitl.subquestions.enabled: true`  
**Then** the request is accepted and returns a `job_id`  
**And** when I submit the same request without `hitl` fields, it is also accepted and follows default non-HITL behavior (no required review step introduced by default)
- result: pass - `docker compose exec backend uv run pytest tests/api/test_agent_run.py::test_post_run_async_accepts_subquestion_hitl_controls tests/sdk/test_public_api_async.py::test_run_async_preserves_omitted_controls_and_hitl_default_off tests/sdk/test_sdk_async_e2e.py::test_sdk_async_run_e2e_preserves_default_off_subquestion_hitl_path` passed.
- reported: 2026-03-14
- severity: none
- reason: The API accepted additive `hitl.subquestions.enabled` on async start, omitted controls still preserved HITL default-off behavior, and the async E2E path completed through the non-checkpoint runtime when subquestion HITL remained disabled.

### Test 2: Paused HITL run exposes reviewable checkpoint metadata to clients

**Given** a HITL-enabled async run that reaches decomposition  
**When** I observe run events via `/api/agents/run-events/{job_id}`  
**Then** I receive a paused event/state at `subquestions_ready`  
**And** the payload includes `checkpoint_id` and `interrupt_payload` with proposed subquestions for operator review
- result: pass - `docker compose exec backend uv run pytest tests/api/test_run_events_stream.py::test_checkpoint_enabled_initial_run_pauses_at_subquestions_ready_with_interrupt_payload_and_checkpoint_id` and `docker compose exec frontend npm run test -- --run src/App.test.tsx -t "shows paused subquestion review and resumes to completion with typed decisions"` passed.
- reported: 2026-03-14
- severity: none
- reason: The backend emitted `run.paused` at `subquestions_ready` with matching `checkpoint_id` and `interrupt_payload` review data, and the frontend consumed that payload into actionable review UI before resuming successfully.

### Test 3: Resume with approve/edit/deny/skip decisions completes run deterministically

**Given** a paused run with a known `checkpoint_id`  
**When** I resume with typed decisions that include a mix of `approve`, `edit`, `deny`, and `skip`  
**Then** the run transitions from paused to completion  
**And** resulting downstream behavior reflects the submitted decisions (edited text used, denied/skipped entries excluded, approved entries preserved)

### Test 4: Malformed typed resume envelope fails at API boundary

**Given** a paused run exists  
**When** I submit a resume request with an invalid typed envelope (missing required fields or invalid decision shape)  
**Then** the API responds with deterministic validation errors  
**And** no silent fallback or ad hoc runtime parsing occurs for malformed typed payloads

### Test 5: Frontend paused review UX is actionable and non-HITL flow is unchanged

**Given** the frontend is connected to backend run APIs  
**When** a run pauses for subquestion HITL  
**Then** the UI displays review controls for approve/edit/deny/skip and can submit a typed resume request  
**And** when a run is started without HITL controls, completion follows the previous non-review path with no resume UI requirement

### Test 6: SDK typed async parity supports new and legacy resume modes

**Given** an SDK client using async run/resume APIs  
**When** I enable subquestion HITL through SDK typed request controls and later resume with typed checkpoint decisions  
**Then** the SDK flow succeeds and mirrors backend runtime behavior  
**And** legacy `resume=True` / object-style resume payloads still function for backward compatibility

## Summary

Tests 1-2 passed on 2026-03-14. Async run requests accept additive subquestion HITL enablement without changing default-off behavior, and HITL-enabled runs now emit `run.paused` at `subquestions_ready` with reviewable checkpoint metadata that the frontend can consume and resume from.

## Gaps

[]
