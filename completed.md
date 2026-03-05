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
