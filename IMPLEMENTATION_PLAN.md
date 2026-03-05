# Agent-Search Implementation Plan

Tasks are in **recommended implementation order**. Each section has a **single clear goal**. Complete one section at a time.


## Section 15: Frontend tests for new response shape

**Goal:** Existing run-flow tests pass. One test asserts that when the response includes `main_question`, `sub_qa` (with sub_question, sub_answer, sub_agent_response, tool_call_input), and `output`, the UI shows Main question, Final answer, and Subquestions list; and that expanding a subquestion reveals sub_answer, sub_agent_response, and tool_call_input where present.

**Details:**
- In `src/frontend/src/App.test.tsx`: Keep the test that mocks `{ output: "..." }` (and any minimal shape) and expects final answer; it must still pass. Add or extend a test that mocks a response with `output`, `main_question`, and `sub_qa` (at least one item with sub_question, sub_answer, sub_agent_response, and optionally tool_call_input), submits a query, and asserts: (1) main question text appears in the document, (2) final answer (output) appears, (3) subquestion list is present, (4) after expanding the first subquestion (or by snapshot), sub_answer, sub_agent_response, and tool_call_input appear as expected where non-empty.

| File | Purpose |
|------|--------|
| `src/frontend/src/App.test.tsx` | Minimal-response test unchanged; add test for main_question, sub_qa accordion, and expanded content. |

**How to test:** Run frontend test suite; all tests must pass.

---
