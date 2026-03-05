## Section 1: Add tool_call_input and sub_agent_response to SubQuestionAnswer schema

**Goal:** Add two optional string fields to the backend `SubQuestionAnswer` model.

**Details:**
- In `src/backend/schemas/agent.py`: Keep `sub_question: str` and `sub_answer: str`. Add `tool_call_input: str = ""` (serialized tool-call args). Add `sub_agent_response: str = ""` (sub-agent AIMessage content for this sub-question). No other file changes.

| File | Purpose |
|------|--------|
| `src/backend/schemas/agent.py` | Add `tool_call_input` and `sub_agent_response` with empty-string defaults. |

**How to test:** Run backend pytest. Tests that build `SubQuestionAnswer` may rely on defaults.

**Test results:**
- Code verification: confirmed `SubQuestionAnswer` already includes `tool_call_input: str = ""` and `sub_agent_response: str = ""` in `src/backend/schemas/agent.py`.
- Docker lifecycle: performed full fresh restart before work (`docker compose down -v --rmi all && docker compose build && docker compose up -d`), then post-task service restart (`docker compose restart`).
- Backend tests:
  - `docker compose exec backend uv run pytest` failed (`Failed to spawn: pytest`).
  - `docker compose exec backend uv run python -m pytest` failed (`No module named pytest`).
  - `docker compose exec backend uv run --with pytest --with langchain-text-splitters python -m pytest` passed: `18 passed, 1 warning`.
- Logs reviewed:
  - `docker compose logs --tail=80 backend`
  - `docker compose logs --tail=80 frontend`
  - `docker compose logs --tail=80 db`
- Runtime follow-up:
  - Backend restart initially showed `ModuleNotFoundError: langchain_text_splitters`; installed missing runtime package in container with `docker compose exec backend uv pip install langchain-text-splitters`, then restarted backend.
  - `docker compose ps` shows all services up (`db` healthy).
  - Health check attempted via `curl http://localhost:8000/api/health` returns `404 Not Found` in current app state.

---
