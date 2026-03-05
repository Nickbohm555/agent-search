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
## Section 3: Populate sub_agent_response in _extract_sub_qa (use last AIMessage per sub-agent)

**Goal:** In `_extract_sub_qa`, set `sub_agent_response` from the **last** AIMessage the sub-agent sends before control returns to the main agent—not the first AIMessage after the ToolMessage.

**Why last:** A sub-agent may make multiple tool calls and multiple AIMessages in one run. Example flow: sub-agent receives query → tool → tool → AIMessage (e.g. clarification) → tool → AIMessage (final answer). We must use that **final** AIMessage for `sub_agent_response`, so the main agent and UI get the sub-agent’s actual answer, not an intermediate message.

**Details:**
- In `src/backend/services/agent_service.py`: After collecting tool results by tool_call_id and building the initial `sub_qa` list, walk the message list in order. For each ToolMessage with a matching tool_call_id, find the **last** AIMessage (with non-empty `content`) that appears **after** that ToolMessage in the list—i.e. the final AIMessage from that sub-agent run before the next main-agent turn or end of list. Use that content as `sub_agent_response` for that item. If there is no such AIMessage, leave `""`.

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Set `sub_agent_response` in `_extract_sub_qa` from the last AIMessage per tool_call_id. |

**How to test:** Run backend pytest. Add or extend unit tests with a message sequence that has multiple AIMessages after a ToolMessage and assert the extracted `sub_agent_response` is the **last** one.

**Test results:**
- Code changes:
  - Updated `src/backend/services/agent_service.py`:
    - Added `_stringify_message_content` helper for consistent message content handling.
    - Added `_is_main_agent_turn` helper to detect coordinator delegation turns (`task` tool call) and stop sub-agent-response capture at that boundary.
    - Extended `_extract_sub_qa` to map tool message indices and assign `sub_agent_response` per `tool_call_id` from the last non-empty `AIMessage` after matching `ToolMessage` and before the next main-agent turn.
    - Added extraction log line per `tool_call_id` for `sub_agent_response` visibility (`Extracted sub_agent_response ...`).
  - Updated `src/backend/tests/services/test_agent_service.py`:
    - Added `test_extract_sub_qa_uses_last_ai_message_as_sub_agent_response` with multiple post-ToolMessage `AIMessage` entries and asserted the extracted `sub_agent_response` is the last qualifying message.
- Docker lifecycle:
  - Pre-work full reboot completed: `docker compose down -v --rmi all && docker compose build && docker compose up -d`.
  - Post-change backend restart completed: `docker compose restart backend`.
  - Runtime issue fixed and restart repeated: installed missing package in container (`docker compose exec backend uv pip install --python .venv/bin/python langchain-text-splitters`) then `docker compose restart backend`.
  - Running state verified via `docker compose ps` (`db` healthy; `backend`, `frontend`, and `chrome` up).
- Tests run:
  - `docker compose exec backend uv run --with pytest --with langchain-text-splitters python -m pytest`
    - Result: `19 passed, 1 warning`.
  - `docker compose exec backend uv run --with pytest --with langchain-text-splitters python -m pytest tests/services/test_agent_service.py -q`
    - Result: `3 passed`.
- Logs reviewed:
  - `docker compose logs --no-color --tail=120 backend`
  - `docker compose logs --no-color --tail=120 frontend`
  - `docker compose logs --no-color --tail=120 db`
  - `docker compose logs --no-color --tail=80 backend` (post-fix confirmation)
  - `docker compose logs --no-color --tail=40 frontend`
  - `docker compose logs --no-color --tail=40 db`
- Health endpoint check:
  - `curl http://localhost:8000/api/health` currently returns `404 {"detail":"Not Found"}` in this app state.

---
