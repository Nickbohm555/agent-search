# Agent-Search Implementation Plan

Tasks are in **recommended implementation order**. Each section has a **single clear goal**. Complete one section at a time; run the listed tests before moving on.

**Tech stack:** No new dependencies. **Tooling:** No change.

**UI vs logs:** The Final Readout UI shows only **subagent response**, **subagent answer**, and **final answer** (no tool-call input on the UI). Keep `tool_call_input` in the API and in **run-end logs** (e.g. docker logs) for debugging; do not render it in the frontend.

**Before marking any section complete or moving it to `agent-search/completed.md`:**
1. **Restart the application** after all code for that section is built.
2. Add or adjust **logging** so behavior can be inspected; **check relevant docker logs** and **run all relevant tests** (unit, integration, or "How to test").
3. If anything fails, such as docker log issues: fix, then **repeat from step 1**. Do **not** mark complete or add to `completed.md` until everything passes.
4. Record outcomes under **Test results** in `agent-search/completed.md`, then mark the section complete / move it to `completed.md`.


---

## Section 5: Update _extract_sub_qa unit test

**Goal:** Unit test asserts all four fields: sub_question, sub_answer, tool_call_input, sub_agent_response.

**Details:**
- In `src/backend/tests/services/test_agent_service.py`: Update the `_extract_sub_qa` test so mock messages include an AIMessage after the ToolMessage. Assert the returned item(s) have `sub_question`, `sub_answer`, `tool_call_input`, and `sub_agent_response` set as expected.

| File | Purpose |
|------|--------|
| `src/backend/tests/services/test_agent_service.py` | Update _extract_sub_qa test for new fields and message shape. |

**How to test:** Run backend pytest; _extract_sub_qa test must pass.

---

## Section 6: Add run-end summary log for sub_qa

**Goal:** At end of each agent run, log a clear summary so docker logs show sub_question, tool input/output, and sub_agent_response for every SubQuestionAnswer.

**Details:**
- In `src/backend/services/agent_service.py`: After extracting `sub_qa` and before returning (e.g. in `run_runtime_agent`), log a structured block: for each item in `sub_qa`, log sub_question (truncate if needed), tool_call_input, sub_answer, sub_agent_response (truncate if needed). Use a clear label (e.g. "SubQuestionAnswer", index). Optionally keep one "Extracted sub_qa count=N" and trim other per-message logs so the summary is easy to find.
- Optional: In `src/backend/utils/agent_callbacks.py`, trim or gate `log_agent_messages_summary` if too noisy.

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Log run-end summary per SubQuestionAnswer. |
| `src/backend/utils/agent_callbacks.py` | Optional: reduce log noise. |

**How to test:** Restart backend; run a query that produces at least one sub_qa; confirm docker logs show sub_question, tool_call_input, sub_answer, and sub_agent_response for every item at run end (tool_call stays in logs only, not on UI).

---

## Section 7: Call _extract_sub_qa and return RuntimeAgentRunResponse with main_question and sub_qa

**Goal:** In `run_runtime_agent`, call `_extract_sub_qa(messages)` and return `RuntimeAgentRunResponse(main_question=payload.query, sub_qa=extracted, output=output)`.

**Details:**
- In `src/backend/services/agent_service.py`: After `agent.invoke()` and existing main-answer extraction, call `_extract_sub_qa(result["messages"])`. Build and return `RuntimeAgentRunResponse(main_question=payload.query, sub_qa=extracted, output=output)`. Ensure existing tests that mock the agent still pass (e.g. empty `sub_qa` when message shape doesn’t match).

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Call `_extract_sub_qa`; return `RuntimeAgentRunResponse` with `main_question`, `sub_qa`, `output`. |

**How to test:** Run full backend pytest. Restart backend; verify sub_qa in logs for a real run.

---

## Section 8: Integration test for run response shape

**Goal:** Integration test asserts `POST /api/agents/run` response includes `main_question`, `sub_qa` (with sub_question, sub_answer, tool_call_input, sub_agent_response), and `output`.

**Details:**
- In `src/backend/tests/api/test_agent_run.py` (or equivalent): Add or update a test that mocks the runtime agent to return messages yielding at least one sub_qa item, POSTs to `/api/agents/run`, and asserts the response has `main_question`, `sub_qa` (list of objects with those four fields), and `output`.

| File | Purpose |
|------|--------|
| `src/backend/tests/api/test_agent_run.py` | Integration test for run endpoint response shape. |

**How to test:** Run backend pytest including this test; restart backend and confirm no regressions.

---

## Section 9: Frontend types for run response

**Goal:** Define `SubQuestionAnswer` and extend `RuntimeAgentRunResponse` with `main_question` and `sub_qa` in the frontend.

**Details:**
- In `src/frontend/src/utils/api.ts`: Add interface `SubQuestionAnswer` with `sub_question: string`, `sub_answer: string`, optional `tool_call_input?: string`, `sub_agent_response?: string` (treat absent as `""`). Extend `RuntimeAgentRunResponse` with `main_question?: string` (absent → `""`) and `sub_qa?: SubQuestionAnswer[]` (absent → `[]`). Keep `output: string` required.

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Add `SubQuestionAnswer`; extend `RuntimeAgentRunResponse` with `main_question`, `sub_qa`. |

**How to test:** Frontend tests; no runtime change yet.

---

## Section 10: Update runAgent response validator

**Goal:** `runAgent` validator accepts and validates `main_question` and `sub_qa`; older responses (only `output`) still pass.

**Details:**
- In `src/frontend/src/utils/api.ts`: Update the `validate` function in `runAgent` to accept and validate `main_question` (string) and `sub_qa` (array of objects with `sub_question`, `sub_answer`, and optionally `tool_call_input`, `sub_agent_response`). Treat missing fields as empty string or empty array.

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Update `runAgent` validator for new fields. |

**How to test:** Frontend tests. Call `POST /api/agents/run` from the app; confirm no "malformed response" when backend returns `main_question` and `sub_qa`.

---

## Section 11: Display main_question in Final Readout

**Goal:** Show main question from API response in "Final Readout"; fallback to submitted query when absent.

**Details:**
- In `src/frontend/src/App.tsx`: For the main question line, use `result.data.main_question` when non-empty, else `submittedQuery`. Store full run result if needed (e.g. `lastRunResponse`) so `main_question` and later `sub_qa` can be shown. Optionally update label (e.g. "Main question:" or "Requested query:").

| File | Purpose |
|------|--------|
| `src/frontend/src/App.tsx` | Use main_question from run response in Final Readout with fallback to submitted query. |

**How to test:** Frontend tests. Manually run a query; confirm main question line shows API `main_question` when present, else submitted query.

---

## Section 12: Display sub_qa list in UI

**Goal:** Render `sub_qa` in Final Readout so the UI shows only **subagent answer** (`sub_answer`), **subagent response** (`sub_agent_response`), and **final answer** (existing output). Do **not** display `tool_call_input` in the UI (it remains in logs only).

**Details:**
- In `src/frontend/src/App.tsx`: From last run result, read `result.data.sub_qa`. If non-empty, render a list: for each item show (1) sub_question as context if desired, (2) subagent answer (`sub_answer`), (3) subagent response (`sub_agent_response`). Use clear labels (e.g. "Subagent answer:", "Subagent response:"); hide blocks when value is empty. Do **not** render `tool_call_input`. Do not change "Final Answer" display.

| File | Purpose |
|------|--------|
| `src/frontend/src/App.tsx` | Render `sub_qa` in Final Readout (sub_answer, sub_agent_response only; no tool_call_input). |

**How to test:** Frontend tests. Manually run a query that returns sub_qa and confirm list shows subagent answer and subagent response only (no tool call); run one with empty sub_qa and confirm no errors.

---

## Section 13: Frontend tests for new response shape

**Goal:** Existing run-flow tests pass; one test asserts main_question, subagent answer, subagent response, and final answer are accepted and rendered (no assertion for tool_call_input in the UI).

**Details:**
- In `src/frontend/src/App.test.tsx`: Keep the test that mocks `{ output: "..." }` and expects final answer; it must still pass. Add or extend a test that mocks a response with `output`, `main_question`, and `sub_qa` (at least one item with sub_question, sub_answer, sub_agent_response), submits a query, and asserts main question, subagent answer (`sub_answer`), subagent response (`sub_agent_response`), and final answer appear in the document. Do not assert that tool_call_input is displayed (it is not shown in the UI).

| File | Purpose |
|------|--------|
| `src/frontend/src/App.test.tsx` | Keep minimal-response test; add test for main_question and sub_qa display. |

**How to test:** Run frontend test suite; all tests must pass.

---
