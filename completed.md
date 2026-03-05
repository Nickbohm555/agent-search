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

## Section 2: Populate tool_call_input in _extract_sub_qa

**Goal:** In `_extract_sub_qa`, set `tool_call_input` on each `SubQuestionAnswer` from the tool-call args.

**Details:**
- In `src/backend/services/agent_service.py`: When building each `SubQuestionAnswer`, set `tool_call_input` to a string representation of the tool call `args` (e.g. `json.dumps(args)` or the value used for sub_question if a single key). Keep `sub_answer` from ToolMessage content; leave `sub_agent_response` as `""` for this section.

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Set `tool_call_input` in `_extract_sub_qa`. |

**How to test:** Run backend pytest (existing _extract_sub_qa test may need a small assertion update for tool_call_input).

**Test results:**
- Code verification:
  - Confirmed `_extract_sub_qa` already sets `tool_call_input` from tool-call args in `src/backend/services/agent_service.py`.
  - Confirmed unit assertion exists in `tests/services/test_agent_service.py` for `tool_call_input == '{"query": "What changed in policy X?"}'`.
- Docker lifecycle and logs:
  - Pre-work clean reboot completed: `docker compose down -v --rmi all && docker compose build && docker compose up -d`.
  - Post-verification full restart completed: `docker compose down && docker compose up -d`.
  - Logs reviewed for each service:
    - `docker compose logs --no-color --tail=120 backend`
    - `docker compose logs --no-color --tail=120 frontend`
    - `docker compose logs --no-color --tail=120 db`
  - `docker compose ps` confirms `db`, `backend`, `frontend`, and `chrome` are up (`db` healthy).
- Backend tests:
  - Initial required command `docker compose exec backend uv run pytest` failed because `pytest` entrypoint is not included in project dependencies.
  - `docker compose exec backend uv run python -m pytest` initially failed (`No module named pytest`).
  - Installed runtime test tools in backend container venv (no repo dependency changes):
    - `uv pip install --python .venv/bin/python pytest`
    - `uv pip install --python .venv/bin/python langchain-text-splitters`
  - Ran targeted section test:
    - `docker compose exec backend uv run python -m pytest tests/services/test_agent_service.py -q`
    - Result: `2 passed`.
  - Ran full backend suite:
    - `docker compose exec backend uv run python -m pytest -q`
    - Result: `18 passed, 1 warning`.

---
