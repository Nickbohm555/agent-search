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
