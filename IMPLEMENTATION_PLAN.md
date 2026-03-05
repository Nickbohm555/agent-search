# Agent-Search Implementation Plan

Tasks are in **recommended implementation order**. Each section has a **single clear goal**. Complete one section at a time.


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
