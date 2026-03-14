---
status: ready
phase: "03-query-expansion-hitl-end-to-end"
source:
  - 03-01-SUMMARY.md
  - 03-02-SUMMARY.md
  - 03-03-SUMMARY.md
started: "2026-03-13"
updated: "2026-03-13"
---

## Current Test

Phase 03 end-to-end query-expansion HITL behavior across backend contracts, runtime checkpointing/resume, SSE lifecycle, and frontend review/resume UX.

## Information Needed from the Summary

what_changed:
- Added optional query-expansion HITL fields to async run/start and typed resume envelopes without breaking legacy callers.
- Inserted a single runtime pause checkpoint after query expansion and before retrieval, with persisted `checkpoint_id` and interrupt payload.
- Implemented deterministic resume handling for approve/edit/deny/skip decisions tied to the paused checkpoint.
- Exposed paused lifecycle data over SSE and made the frontend treat query-expansion pause as an actionable state.
- Added frontend review controls for approve/edit/deny/skip and resumed streaming to completion for the same run.

files_changed:
- `src/backend/agent_search/public_api.py`
- `src/backend/schemas/__init__.py`
- `src/backend/schemas/agent.py`
- `sdk/core/src/schemas/__init__.py`
- `sdk/core/src/schemas/agent.py`
- `src/backend/agent_search/runtime/graph/builder.py`
- `src/backend/agent_search/runtime/graph/routes.py`
- `src/backend/agent_search/runtime/graph/state.py`
- `src/backend/agent_search/runtime/jobs.py`
- `src/backend/agent_search/runtime/lifecycle_events.py`
- `src/backend/agent_search/runtime/resume.py`
- `src/backend/agent_search/runtime/runner.py`
- `src/backend/tests/api/test_agent_run.py`
- `src/backend/tests/api/test_run_events_stream.py`
- `src/frontend/src/utils/api.ts`
- `src/frontend/src/App.tsx`
- `src/frontend/src/App.test.tsx`

code_areas:
- Backend API request/response schema boundaries for async run and resume.
- Runtime graph transition between query expansion and retrieval.
- Paused job metadata persistence and resume decision application.
- SSE lifecycle event payload generation and client stream consumption.
- Frontend API typing/guards and React review/resume interaction flow.

testing_notes:
- Primary observable outcomes are pause timing, pause payload shape, checkpoint-bound resume semantics, and non-HITL backward compatibility.
- Verify both API-level behavior and UI behavior because this phase spans contracts, runtime, and frontend interaction.
- Existing summary verification indicates backend and frontend regression suites already include coverage; these UAT tests confirm operator-visible outcomes.

## Tests

### Test 1 - Non-HITL backward compatibility remains unchanged
**Goal:** Confirm runs without query-expansion HITL config behave exactly like the legacy async flow.

**Setup:**
- Start backend and frontend services.
- Submit a normal async run request without any query-expansion HITL fields.

**Steps:**
1. Trigger an async run with a representative query and no HITL config.
2. Observe lifecycle events and final run state.
3. Confirm no pause action is requested and no checkpoint resume call is needed.
4. Validate frontend does not render query-expansion review controls.

**Expected observable outcome:**
- Run goes from async start to completion without `run.paused`.
- No query-expansion review panel appears in UI.
- No resume request is sent for this run.

### Test 2 - HITL-enabled run pauses after expansion and before retrieval
**Goal:** Confirm query-expansion HITL creates one actionable pause at the correct stage.

**Setup:**
- Submit an async run with query-expansion HITL enabled.

**Steps:**
1. Start HITL-enabled run.
2. Watch SSE lifecycle stream.
3. Capture the pause event payload.
4. Verify payload includes stage context and checkpoint metadata for review/resume.

**Expected observable outcome:**
- Run emits `run.paused` once at query-expansion review stage.
- Pause arrives after expansion candidates are available and before retrieval work proceeds.
- Payload includes a stable `checkpoint_id` and reviewable expansion data.

### Test 3 - Approve decision resumes same run to completion
**Goal:** Confirm approve action continues the paused run deterministically.

**Setup:**
- Use a paused HITL run with known `job_id` and `checkpoint_id`.

**Steps:**
1. Submit an approve resume decision bound to the paused checkpoint.
2. Continue consuming SSE events for the same `job_id`.
3. Observe transition from paused state to terminal completion.

**Expected observable outcome:**
- Resume request is accepted when `checkpoint_id` matches paused metadata.
- Same run continues and completes without creating a new job.
- Completion reflects continued execution past retrieval.

### Test 4 - Edit decision uses operator-modified expansions
**Goal:** Confirm edit decision replaces the expansion set used for resumed execution.

**Setup:**
- Pause a HITL-enabled run and prepare a distinct edited expansion list.

**Steps:**
1. Submit resume decision type `edit` with edited expansions and the paused `checkpoint_id`.
2. Resume run and observe downstream behavior and returned context.
3. Compare resulting behavior with baseline approve path for the same input.

**Expected observable outcome:**
- Resume accepts edited payload and continues same job.
- Resumed execution reflects operator-edited expansion terms (not original generated set).
- Run still reaches terminal completion.

### Test 5 - Deny and skip paths are supported and deterministic
**Goal:** Confirm both deny and skip resume decisions are handled as first-class outcomes.

**Setup:**
- Create separate paused runs (or repeatable fixtures) for deny and skip decisions.

**Steps:**
1. Resume one paused run with decision `deny`.
2. Resume another paused run with decision `skip`.
3. Observe lifecycle transitions and final state in each path.

**Expected observable outcome:**
- Both resume requests are accepted when checkpoint-bound.
- Each path follows deterministic behavior for decision semantics.
- Neither path breaks stream handling or causes malformed terminal state.

### Test 6 - Frontend review UX renders actionable controls and resumes stream
**Goal:** Confirm UI presents review state and sends correct checkpoint-bound decision payloads.

**Setup:**
- Open frontend app and start HITL-enabled run.

**Steps:**
1. Wait for query-expansion pause in UI.
2. Verify review panel appears with approve/edit/deny/skip options and expansion data.
3. Trigger one action (e.g., skip) and inspect outbound resume payload shape.
4. Confirm UI transitions from paused review back to active/completed state.

**Expected observable outcome:**
- Query-expansion pause is displayed as an actionable state, not as failure.
- Resume request includes `job_id` + `checkpoint_id` and typed decision envelope.
- Stream resumes and UI ends in completion view.

## Summary

This test set validates phase 03 as an operator-visible contract-to-UI workflow: additive backward-compatible API inputs, runtime checkpoint pause placement, deterministic checkpoint-bound resume semantics (approve/edit/deny/skip), SSE paused payload integrity, and a frontend review/resume experience that preserves legacy non-HITL behavior when disabled.

## Gaps

[]
