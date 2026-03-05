# Agent-Search Implementation Plan

Tasks are in **recommended implementation order**. Each section has a **single clear goal**. Complete one section at a time.


## Section 13: Subquestions list with nested dropdown (accordion)

**Goal:** For each item in `sub_qa`, render one collapsible row (dropdown/accordion). The row header shows the **sub-question** (optionally truncated). When expanded, show labeled blocks: **Subagent answer** (`sub_answer`), **Subagent response** (`sub_agent_response`), and **Tool call input** (`tool_call_input`). Hide any block when its value is empty. Keep the UI clean and scannable.

**Details:**
- In `src/frontend/src/App.tsx`: Inside the Subquestions section, map over `lastRunResponse?.sub_qa ?? []`. Each item is one collapsible: summary/button = sub_question text; expanded content = optional blocks for "Subagent answer:", "Subagent response:", "Tool call input:" with the corresponding values. Omit a block if the value is empty or undefined. Use native `<details>/<summary>` or a small state-based accordion; style so multiple items can be expanded at once and the list is easy to scan.

| File | Purpose |
|------|--------|
| `src/frontend/src/App.tsx` | Render sub_qa as accordion list with sub_answer, sub_agent_response, tool_call_input in expanded area. |

**How to test:** Run a query that returns `sub_qa` with at least one item; confirm each sub-question appears as a row, expanding shows subagent answer, subagent response, and tool call input (when present); empty values do not show blocks; empty sub_qa still shows Section 12 empty state.

---

## Section 14: Final Readout polish and accessibility

**Goal:** Improve readability and accessibility of the Final Readout: spacing, typography, and optional ARIA/labels for the Subquestions accordion. No new data or behavior.

**Details:**
- In `src/frontend/src/App.tsx` (and any related CSS): Add or adjust spacing between Main question, Final answer, and Subquestions sections; ensure accordion buttons/summaries have clear focus and, if using custom accordion, `aria-expanded` and `aria-controls`. Keep visual hierarchy (e.g. section labels vs. body text). Optionally add a small cue (e.g. chevron) for expand/collapse.

| File | Purpose |
|------|--------|
| `src/frontend/src/App.tsx` (+ styles) | Spacing, typography, ARIA and focus for Final Readout and accordion. |

**How to test:** Visual pass and keyboard tab-through; screen reader if available; confirm no regressions in existing behavior.

---

## Section 15: Frontend tests for new response shape

**Goal:** Existing run-flow tests pass. One test asserts that when the response includes `main_question`, `sub_qa` (with sub_question, sub_answer, sub_agent_response, tool_call_input), and `output`, the UI shows Main question, Final answer, and Subquestions list; and that expanding a subquestion reveals sub_answer, sub_agent_response, and tool_call_input where present.

**Details:**
- In `src/frontend/src/App.test.tsx`: Keep the test that mocks `{ output: "..." }` (and any minimal shape) and expects final answer; it must still pass. Add or extend a test that mocks a response with `output`, `main_question`, and `sub_qa` (at least one item with sub_question, sub_answer, sub_agent_response, and optionally tool_call_input), submits a query, and asserts: (1) main question text appears in the document, (2) final answer (output) appears, (3) subquestion list is present, (4) after expanding the first subquestion (or by snapshot), sub_answer, sub_agent_response, and tool_call_input appear as expected where non-empty.

| File | Purpose |
|------|--------|
| `src/frontend/src/App.test.tsx` | Minimal-response test unchanged; add test for main_question, sub_qa accordion, and expanded content. |

**How to test:** Run frontend test suite; all tests must pass.

---
