# Agent-Search Implementation Plan

Tasks are ordered by **recommended implementation order**. Each section has a **single clear goal**, with **files and purpose** listed. Complete one section at a time; run the listed tests before moving on.

**MANDATORY before marking any section complete or moving it to `agent-search/completed.md`:**
1. **Restart the application** after all code for that section is built (e.g. stop then start the app/server/containers).
2. **Create all logs necessary to view** (add or adjust logging so app, build, and runtime behavior can be inspected). **Check all logs** (app logs, build logs, runtime logs) and **run all relevant tests** (unit, integration, or commands from "How to test").
3. **If anything fails** (startup error, test failure, bad logs, browser/API errors): read the logs and test output, fix the cause, then **repeat from step 1** (restart and re-check). Do **not** call the section "completed" or add it to `completed.md` until everything passes.
4. Only after a successful restart and passing checks (and browser check when applicable), record outcomes under **Test results** in `agent-search/completed.md` and then mark the section complete / move the section to `completed.md`.

---

## Scope: Sub-question breakdown and RAG routing (backend only)

The following atomic sections implement: main question → sub-questions → each sub-query to RAG sub-agent → capture sub-answers → return main question, sub_qa list, and main answer from `POST /api/agents/run`. No frontend changes.

---

## Section 1: Add SubQuestionAnswer model

**Single goal:** Add a Pydantic model for a single (sub_question, sub_answer) item so the run response can later expose a list of them as `sub_qa`.

**Details:**
- In `schemas/agent.py`, define `SubQuestionAnswer` with `sub_question: str` and `sub_answer: str`. This model represents one sub-question and its answer; the response will use `sub_qa: list[SubQuestionAnswer]` (many such items). Export it from schemas if needed. No other file changes.

**Tech stack and dependencies**
- Libraries/packages: None; existing Pydantic in `src/backend/pyproject.toml`.
- Tooling: No change.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/schemas/agent.py` | Add `SubQuestionAnswer` model with `sub_question` and `sub_answer` fields. |

**How to test:** Run backend pytest. Optionally instantiate `SubQuestionAnswer(sub_question="q", sub_answer="a")` in a small test and assert fields.

**Test results:** (Record in `agent-search/completed.md` when section is complete.)

---

## Section 2: Add main_question and sub_qa to RuntimeAgentRunResponse

**Single goal:** Extend `RuntimeAgentRunResponse` with `main_question` and `sub_qa` so the API can return them; keep existing `output`; no service/route logic change yet.

**Details:**
- Add `main_question: str = ""` and `sub_qa: list[SubQuestionAnswer] = Field(default_factory=list)` to `RuntimeAgentRunResponse`. Ensure existing code that builds `RuntimeAgentRunResponse(output=...)` still works (defaults or minimal call-site updates).

**Tech stack and dependencies**
- Libraries/packages: None.
- Tooling: No change.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/schemas/agent.py` | Add `main_question` and `sub_qa` to `RuntimeAgentRunResponse` with backward-friendly defaults. |

**How to test:** Run backend pytest. Existing run tests should still pass; optionally assert response model serialization includes the new fields.

**Test results:** (Record in `agent-search/completed.md` when section is complete.)

---

## Section 3: Update coordinator prompt for sub-question breakdown

**Single goal:** Change only `_COORDINATOR_PROMPT` so the coordinator is instructed to break the query into focused sub-questions and delegate each to the RAG sub-agent.

**Details:**
- In `coordinator.py`, rewrite `_COORDINATOR_PROMPT` to: (1) identify 1–N focused sub-questions covering the main query, (2) delegate each sub-question to the RAG sub-agent (e.g. task tool), one per delegation, (3) synthesize the final answer only from those retrieval results. Do not change the RAG sub-agent prompt or any other file in this section.

**Tech stack and dependencies**
- Libraries/packages: None.
- Tooling: No change.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agents/coordinator.py` | Update `_COORDINATOR_PROMPT` only for sub-question decomposition and one-to-one RAG delegation. |

**How to test:** Restart backend; run backend pytest. Optionally call `POST /api/agents/run` and inspect logs to confirm coordinator behavior.

**Test results:** (Record in `agent-search/completed.md` when section is complete.)

---

## Section 4: Update RAG sub-agent prompt for per–sub-question answers

**Single goal:** Refine `_RAG_SUBAGENT_PROMPT` so the RAG agent returns concise, grounded answers per sub-question.

**Details:**
- In `coordinator.py`, update `_RAG_SUBAGENT_PROMPT` so the retrieval subagent is explicitly instructed to answer the given sub-question concisely from retrieved content. No other code or schema changes.

**Tech stack and dependencies**
- Libraries/packages: None.
- Tooling: No change.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agents/coordinator.py` | Update `_RAG_SUBAGENT_PROMPT` only for concise, grounded per–sub-question answers. |

**How to test:** Restart backend; run backend pytest.

**Test results:** (Record in `agent-search/completed.md` when section is complete.)

---

## Section 5: Implement _extract_sub_qa(messages) helper

**Single goal:** Implement a function that parses the agent message list and returns `list[SubQuestionAnswer]`; add a unit test for it.

**Details:**
- In `agent_service.py` (or a small helper module), implement `_extract_sub_qa(messages) -> list[SubQuestionAnswer]` that: finds AIMessage(s) with tool_calls (e.g. to the RAG/task tool), extracts the sub-question from each tool input; finds the corresponding ToolMessage(s) by tool_call_id; pairs each sub-question with the tool result content as sub_answer. Return list in order. Add a unit test that builds a minimal `messages` list (AIMessage with tool_calls + ToolMessage) and asserts the returned list matches. Do not call this from `run_runtime_agent` yet.

**Tech stack and dependencies**
- Libraries/packages: None; use LangChain message types already in use.
- Tooling: No change.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` (or shared util) | Implement `_extract_sub_qa(messages)` and keep it testable in isolation. |
| `src/backend/tests/services/test_agent_service.py` | Add unit test for `_extract_sub_qa` with mocked messages. |

**How to test:** Run backend pytest; the new unit test must pass.

**Test results:** (Record in `agent-search/completed.md` when section is complete.)

---

## Section 6: Call _extract_sub_qa in run_runtime_agent and return new fields

**Single goal:** In `run_runtime_agent`, call `_extract_sub_qa(result["messages"])`, set `main_question` from `payload.query`, and return `RuntimeAgentRunResponse(main_question=..., sub_qa=..., output=...)` with `output` unchanged from current logic.

**Details:**
- After `agent.invoke()` and existing main-answer extraction, call `_extract_sub_qa(messages)`. Build and return `RuntimeAgentRunResponse(main_question=payload.query, sub_qa=extracted, output=output)`. Ensure existing tests that mock the agent still pass (e.g. by returning empty `sub_qa` when message shape doesn’t match). Add any logging needed to inspect sub_qa at runtime.

**Tech stack and dependencies**
- Libraries/packages: None.
- Tooling: No change.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Call `_extract_sub_qa`; build and return `RuntimeAgentRunResponse` with `main_question`, `sub_qa`, and `output`; add logs if needed. |

**How to test:** Run full backend pytest. Restart backend; create/check logs necessary to verify sub_qa in a real run.

**Test results:** (Record in `agent-search/completed.md` when section is complete.)

---

## Section 7: Add integration test for run response shape

**Single goal:** Add or update an integration test that asserts `POST /api/agents/run` response JSON includes `main_question`, `sub_qa`, and `output`.

**Details:**
- In `tests/api/test_agent_run.py` (or equivalent), add a test that mocks the runtime agent to return a result with messages that yield at least one sub_qa pair, then POST to `/api/agents/run` and assert the response has `main_question`, `sub_qa` (list of objects with `sub_question` and `sub_answer`), and `output`. Ensure all backend tests pass.

**Tech stack and dependencies**
- Libraries/packages: None.
- Tooling: No change.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tests/api/test_agent_run.py` | Add or update integration test for run endpoint response shape (`main_question`, `sub_qa`, `output`). |

**How to test:** Run backend pytest including the new/updated test; restart backend and confirm no regressions.

**Test results:** (Record in `agent-search/completed.md` when section is complete.)

---
