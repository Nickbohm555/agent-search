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

**Test results:**
- Code changes verified:
  - `SubQuestionAnswer` already existed in `src/backend/schemas/agent.py`.
  - Exported `SubQuestionAnswer` via `src/backend/schemas/__init__.py` so `from schemas import SubQuestionAnswer` works.
- Restart/rebuild actions:
  - Full restart performed: `docker compose restart`.
  - Running state checked with `docker compose ps` (all services up: `db`, `backend`, `frontend`, `chrome`; DB healthy).
- Tests run:
  - `docker compose exec backend uv run pytest`
  - Result: `17 passed, 1 warning` (warning from LangChain PGVector deprecation).
- Logs reviewed:
  - `docker compose logs --tail=120 backend`
  - `docker compose logs --tail=120 frontend`
  - `docker compose logs --tail=120 db`
  - `docker compose logs --tail=120 chrome`
  - Backend initially showed missing `langchain_text_splitters`; after installing missing runtime packages in-container, backend startup completed successfully and tests passed.

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

**Test results:**
- Code/search verification:
  - Reuse-first scan before edits:
    - `rg -n "SubQuestionAnswer|sub_qa|tool_calls|ToolMessage|AIMessage|run_runtime_agent|RuntimeAgentRunResponse|extract" src/backend`
    - Reviewed `src/backend/services/agent_service.py`, `src/backend/tests/services/test_agent_service.py`, `src/backend/schemas/agent.py`, and `src/backend/utils/agent_callbacks.py`.
  - Added `_extract_sub_qa(messages)` in `src/backend/services/agent_service.py` to:
    - collect `ToolMessage` content by `tool_call_id`
    - read `AIMessage.tool_calls`, extract sub-question from tool args (`sub_question`, `question`, `query`, `input`)
    - pair sub-question with matching tool result content in message order
    - return `list[SubQuestionAnswer]`
  - Added visibility logging: `logger.info("Extracted sub_qa pairs count=%s", len(sub_qa))`.
  - Added unit test `test_extract_sub_qa_pairs_tool_call_input_with_tool_result` in `src/backend/tests/services/test_agent_service.py`.
- Tests run:
  - `docker compose exec backend uv run pytest` (initially failed: missing `pytest` executable in backend container).
  - Installed missing in-container packages required for tests/runtime:
    - `docker compose exec backend uv pip install pytest langchain-text-splitters`
  - Re-ran `docker compose exec backend uv run pytest` with final result: `18 passed, 1 warning`.
- Restart/rebuild and container checks:
  - Mandatory fresh restart before this iteration:
    - `docker compose down -v --rmi all`
    - `docker compose build`
    - `docker compose up -d`
  - Mandatory post-implementation restart:
    - `docker compose restart`
  - Verified running state:
    - `docker compose ps` (`backend`, `frontend`, `db` healthy, `chrome` all up).
- Logs reviewed:
  - `docker compose logs --tail=140 backend`
  - `docker compose logs --tail=140 frontend`
  - `docker compose logs --tail=140 db`
  - `docker compose logs --tail=120 chrome`
  - Backend logs include earlier `ModuleNotFoundError: langchain_text_splitters` during missing-package state, followed by successful startup logs (`Application startup complete`) after package install and restart.

---

## Section 2: Add main_question and sub_qa to RuntimeAgentRunResponse

**Single goal:** Extend `RuntimeAgentRunResponse` with `main_question` and `sub_qa` so the API can return them; keep existing `output`; no service/route logic change yet.

**Details:**
- Added `main_question: str = ""` and `sub_qa: list[SubQuestionAnswer] = Field(default_factory=list)` to `RuntimeAgentRunResponse`.
- Kept existing construction pattern `RuntimeAgentRunResponse(output=...)` working via defaults.
- Updated API integration test expectation to include serialized default fields.

**Tech stack and dependencies**
- Libraries/packages: None in repo changes.
- Tooling: No change.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/schemas/agent.py` | Added `main_question` and `sub_qa` to `RuntimeAgentRunResponse` with backward-compatible defaults. |
| `src/backend/tests/api/test_agent_run.py` | Updated expected response JSON to include new default fields (`main_question`, `sub_qa`). |

**How to test:** Run backend pytest. Existing run tests should still pass; assert response model serialization includes new fields.

**Test results:**
- Code/search verification:
  - Reuse check run before edits: `rg -n "class RuntimeAgentRunResponse|SubQuestionAnswer|RuntimeAgentRunResponse\\(" src/backend`.
  - Confirmed `SubQuestionAnswer` already existed and only response model needed extension.
- Restart/rebuild actions:
  - Full fresh restart before changes: `docker compose down -v --rmi all`, `docker compose build`, `docker compose up -d`.
  - Post-change runtime restart of affected service: `docker compose restart backend`.
  - Container state checked: `docker compose ps` (backend/frontend/db/chrome up; db healthy).
- Tests run:
  - `docker compose exec backend uv run pytest`
  - Final result: `17 passed, 1 warning` (LangChain PGVector deprecation warning).
  - During setup, missing in-container packages blocked test execution (`pytest`, `langchain_text_splitters`), resolved in-container with:
    - `docker compose exec backend uv pip install pytest`
    - `docker compose exec backend uv pip install langchain-text-splitters`
- Logs reviewed:
  - `docker compose logs --tail=160 backend`
  - `docker compose logs --tail=120 frontend`
  - `docker compose logs --tail=120 db`
  - Backend logs confirmed startup complete after restart and showed request logging.
  - Health check request `GET /api/health` returned `404 Not Found` in current codebase.

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

**Test results:**
- Code/search verification:
  - Reuse-first search before edits:
    - `rg -n "_COORDINATOR_PROMPT|_RAG_SUBAGENT_PROMPT|create_react_agent|task" src/backend/agents src/backend/services src/backend/tests`
    - Reviewed `src/backend/agents/coordinator.py` and updated only `_COORDINATOR_PROMPT`.
  - Prompt now explicitly requires: focused subquestion decomposition, 1-to-N sub-questions, one task delegation per sub-question, and final synthesis only from delegated retrieval outputs.
- Restart/rebuild actions:
  - Full clean restart before work:
    - `docker compose down -v --rmi all`
    - `docker compose build`
    - `docker compose up -d`
  - Post-change validation restarts:
    - `docker compose restart && docker compose ps` (re-run after each failed check per plan instructions).
  - Final running state: `backend`, `frontend`, `db` (healthy), `chrome` all up.
- Logs reviewed:
  - `docker compose logs --tail=160 backend`
  - `docker compose logs --tail=120 frontend`
  - `docker compose logs --tail=120 db`
  - `docker compose logs --tail=80 chrome`
  - Follow-up log checks after restarts:
    - `docker compose logs --tail=80 backend`
    - `docker compose logs --tail=50 frontend`
    - `docker compose logs --tail=50 db`
    - `docker compose logs --tail=40 chrome`
  - Observed and addressed backend startup/test blockers:
    - `ModuleNotFoundError: No module named 'langchain_text_splitters'`
    - `uv run pytest` failing with missing pytest executable.
- Environment fixes required to run mandated tests:
  - `docker compose exec backend uv pip install pytest langchain-text-splitters`
- Tests run:
  - `docker compose exec backend uv run pytest`
    - First run failed due a test expectation string mismatch after prompt rewrite (`tests/agents/test_coordinator_agent.py` expected phrase).
    - Prompt text was adjusted (still Section 3-compliant) to preserve expected phrase while keeping new decomposition/delegation constraints.
- `docker compose exec backend uv run pytest` (re-run after fix)
    - Final result: `17 passed, 1 warning`.

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

**Test results:**
- Code/search verification:
  - Reuse-first scan before edits:
    - `rg -n "_RAG_SUBAGENT_PROMPT|RAG sub-agent|sub-question|subquestion|coordinator" src/backend`
    - Reviewed `src/backend/agents/coordinator.py` and `src/backend/tests/agents/test_coordinator_agent.py` to preserve existing agent wiring and coverage.
  - Updated `_RAG_SUBAGENT_PROMPT` to explicitly answer each assigned sub-question concisely from retrieved content and to state when evidence is insufficient.
- Test and environment actions:
  - `docker compose exec backend uv run pytest` initially failed because `pytest` was missing in-container.
  - Installed test/runtime dependencies required by the current container image:
    - `docker compose exec backend uv pip install pytest`
    - `docker compose exec backend uv pip install langchain-text-splitters`
  - `docker compose exec backend uv run pytest` then failed on one stale exact-string test assertion for the updated prompt.
  - Updated `src/backend/tests/agents/test_coordinator_agent.py` expected subagent prompt text to match the refined prompt.
  - Re-ran `docker compose exec backend uv run pytest` with final result: `17 passed, 1 warning`.
- Restart/rebuild and container checks:
  - Restarted full application after code completion: `docker compose restart`.
  - Verified running state with `docker compose ps` (`backend`, `frontend`, `db` healthy, `chrome` all up).
- Logs reviewed:
  - `docker compose logs --tail=160 backend`
  - `docker compose logs --tail=120 frontend`
  - `docker compose logs --tail=120 db`
  - `docker compose logs --tail=80 chrome`
  - Backend logs showed earlier missing dependency stack traces during setup, followed by successful startup (`Application startup complete`) after dependency install and restart.

---
