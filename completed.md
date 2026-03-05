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
## Section 4: Instruct RAG sub-agent to send its answer as its final message

**Goal:** Ensure the RAG sub-agent (deepagent) is explicitly told to send its answer as its **final** message when done, so that the “last AIMessage” we extract in Section 3 is the intended answer.

**Details:**
- In `src/backend/agents/coordinator.py`, update `_RAG_SUBAGENT_PROMPT` (and any related instructions) to state clearly: when you have finished answering the sub-question, send your answer as your final message; do not make further tool calls after providing the answer. This aligns sub-agent behavior with Section 3’s extraction (last AIMessage per sub-agent).

| File | Purpose |
|------|--------|
| `src/backend/agents/coordinator.py` | Add to RAG sub-agent prompt: send answer as final message when done. |

**How to test:** Run backend pytest (including coordinator/agent tests). Optionally run a live query and confirm logs show the sub-agent’s final message as the one captured in `sub_agent_response`.

**Test results:**
- Code changes:
  - Updated `src/backend/agents/coordinator.py`:
    - Extended `_RAG_SUBAGENT_PROMPT` with explicit instruction to send the completed answer as the final message and make no further tool calls afterward.
    - Added run-time visibility log: `Coordinator subagent guardrail enabled ... final_message_only=true`.
  - Updated `src/backend/tests/agents/test_coordinator_agent.py`:
    - Updated strict prompt assertion to match the new final-message wording.
    - Added assertion that the new guardrail log line is emitted.
- Docker lifecycle and container handling:
  - Pre-work clean reboot completed: `docker compose down -v --rmi all && docker compose build && docker compose up -d`.
  - Post-change application restart completed: `docker compose restart`.
  - Backend runtime dependency issue addressed for operational validation in-container:
    - `docker compose exec backend uv pip install --python .venv/bin/python langchain-text-splitters pytest`
    - `docker compose restart backend`
- Tests run:
  - `docker compose exec backend uv run pytest`
    - Result: `19 passed, 1 warning`.
  - `docker compose exec backend uv run --with pytest --with langchain-text-splitters python -m pytest tests/agents/test_coordinator_agent.py -q`
    - Result: `1 passed`.
  - `docker compose exec backend uv run --with pytest --with langchain-text-splitters python -m pytest -q`
    - Result: `19 passed, 1 warning`.
- Logs reviewed:
  - `docker compose logs --no-color --tail=120 backend`
  - `docker compose logs --no-color --tail=80 frontend`
  - `docker compose logs --no-color --tail=80 db`
  - `docker compose ps` confirms all services up (`db` healthy; `backend`, `frontend`, `chrome` running).

---
## Section 5: Update _extract_sub_qa unit test

**Goal:** Unit test asserts all four fields: sub_question, sub_answer, tool_call_input, sub_agent_response.

**Details:**
- In `src/backend/tests/services/test_agent_service.py`: Update the `_extract_sub_qa` test so mock messages include an AIMessage after the ToolMessage. Assert the returned item(s) have `sub_question`, `sub_answer`, `tool_call_input`, and `sub_agent_response` set as expected.

| File | Purpose |
|------|--------|
| `src/backend/tests/services/test_agent_service.py` | Update _extract_sub_qa test for new fields and message shape. |

**How to test:** Run backend pytest; _extract_sub_qa test must pass.

**Test results:**
- Code changes:
  - Updated `src/backend/tests/services/test_agent_service.py`:
    - Renamed test to `test_extract_sub_qa_extracts_all_fields_from_tool_and_followup_messages`.
    - Added post-`ToolMessage` `AIMessage` content and a subsequent main-agent tool call message boundary.
    - Added assertions for all four fields on the extracted item: `sub_question`, `sub_answer`, `tool_call_input`, and `sub_agent_response`.
- Docker lifecycle and logs:
  - Pre-work full fresh reboot completed: `docker compose down -v --rmi all && docker compose build && docker compose up -d`.
  - Post-change application restart completed: `docker compose restart`.
  - Running state verified via `docker compose ps` (all services up; `db` healthy).
  - Logs reviewed for each service:
    - `docker compose logs --tail 120 backend`
    - `docker compose logs --tail 120 frontend`
    - `docker compose logs --tail 120 db`
- Backend tests:
  - Required command from task: `docker compose exec backend uv run pytest`.
    - Result: failed in this environment (`Failed to spawn: pytest`; executable not present).
  - Follow-up: `docker compose exec backend uv run --with pytest python -m pytest`.
    - Result: collection blocked by existing dependency error (`ModuleNotFoundError: langchain_text_splitters`) in unrelated test modules.
  - Task-targeted verification: `docker compose exec backend uv run --with pytest python -m pytest tests/services/test_agent_service.py -k extract_sub_qa -vv`.
    - Result: `2 passed, 1 deselected`.

---
## Section 6: Add run-end summary log for sub_qa

**Goal:** At end of each agent run, log a clear summary so docker logs show sub_question, tool input/output, and sub_agent_response for every SubQuestionAnswer.

**Details:**
- In `src/backend/services/agent_service.py`: After extracting `sub_qa` and before returning (e.g. in `run_runtime_agent`), log a structured block: for each item in `sub_qa`, log sub_question (truncate if needed), tool_call_input, sub_answer, sub_agent_response (truncate if needed). Use a clear label (e.g. "SubQuestionAnswer", index). Optionally keep one "Extracted sub_qa count=N" and trim other per-message logs so the summary is easy to find.
- Optional: In `src/backend/utils/agent_callbacks.py`, trim or gate `log_agent_messages_summary` if too noisy.

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Log run-end summary per SubQuestionAnswer. |
| `src/backend/utils/agent_callbacks.py` | Optional: reduce log noise. |

**How to test:** Restart backend; run a query that produces at least one sub_qa; confirm docker logs show sub_question, tool_call_input, sub_answer, and sub_agent_response for every item at run end (tool_call stays in logs only, not on UI).

**Test results:**
- Code changes:
  - Updated `src/backend/services/agent_service.py`:
    - Added `_log_sub_qa_run_end_summary(sub_qa)` to emit an indexed run-end block for each item.
    - In `run_runtime_agent`, now calls `_extract_sub_qa(messages)` and logs `SubQuestionAnswer summary count=N` plus per-item fields (`sub_question`, `tool_call_input`, `sub_answer`, `sub_agent_response`) before returning.
  - Updated `src/backend/tests/services/test_agent_service.py`:
    - Extended `test_run_runtime_agent_returns_last_message_output_and_logs` to use a realistic AI→Tool→AI message flow and assert run-end summary log lines are emitted.
- Docker lifecycle and container handling:
  - Pre-work full fresh restart completed: `docker compose down -v --rmi all && docker compose build && docker compose up -d`.
  - Post-change backend restart completed: `docker compose restart backend`.
  - Runtime dependency issue surfaced in backend logs (`ModuleNotFoundError: langchain_text_splitters`); fixed in running backend venv with:
    - `docker compose exec backend uv pip install --python .venv/bin/python langchain-text-splitters`
    - then `docker compose restart backend`.
  - Running state verified with `docker compose ps` (`db` healthy; `backend`, `frontend`, `chrome` up).
- Tests run:
  - Required command from task guidance: `docker compose exec backend uv run pytest`.
    - Result: failed in this environment (`Failed to spawn: pytest`).
  - Backend service tests with explicit test dependency:
    - `docker compose exec backend uv run --with pytest --with langchain-text-splitters python -m pytest tests/services/test_agent_service.py -q`
    - Result: `3 passed`.
  - Full backend suite with explicit test dependency:
    - `docker compose exec backend uv run --with pytest --with langchain-text-splitters python -m pytest -q`
    - Result: `19 passed, 1 warning`.
- Logs reviewed:
  - `docker compose logs --no-color --tail=200 backend`
  - `docker compose logs --no-color --tail=120 frontend`
  - `docker compose logs --no-color --tail=120 db`
- Live runtime verification:
  - Ran: `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What changed in policy X?"}'`
  - Response returned successfully with output text.
  - Backend logs confirmed run-end summary for one extracted item:
    - `SubQuestionAnswer summary count=1`
    - `SubQuestionAnswer[1] ... sub_question=... tool_call_input=... sub_answer=... sub_agent_response=...`

---
## Section 7: Call _extract_sub_qa and return RuntimeAgentRunResponse with main_question and sub_qa

**Goal:** In `run_runtime_agent`, call `_extract_sub_qa(messages)` and return `RuntimeAgentRunResponse(main_question=payload.query, sub_qa=extracted, output=output)`.

**Details:**
- In `src/backend/services/agent_service.py`: After `agent.invoke()` and existing main-answer extraction, call `_extract_sub_qa(result["messages"])`. Build and return `RuntimeAgentRunResponse(main_question=payload.query, sub_qa=extracted, output=output)`. Ensure existing tests that mock the agent still pass (e.g. empty `sub_qa` when message shape doesn’t match).

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Call `_extract_sub_qa`; return `RuntimeAgentRunResponse` with `main_question`, `sub_qa`, `output`. |

**How to test:** Run full backend pytest. Restart backend; verify sub_qa in logs for a real run.

---
## Section 8: Integration test for run response shape

**Goal:** Integration test asserts `POST /api/agents/run` response includes `main_question`, `sub_qa` (with sub_question, sub_answer, tool_call_input, sub_agent_response), and `output`.

**Details:**
- In `src/backend/tests/api/test_agent_run.py` (or equivalent): Add or update a test that mocks the runtime agent to return messages yielding at least one sub_qa item, POSTs to `/api/agents/run`, and asserts the response has `main_question`, `sub_qa` (list of objects with those four fields), and `output`.

| File | Purpose |
|------|--------|
| `src/backend/tests/api/test_agent_run.py` | Integration test for run endpoint response shape. |

**How to test:** Run backend pytest including this test; restart backend and confirm no regressions.

---
## Section 9: Frontend types for run response

**Goal:** Define `SubQuestionAnswer` and extend `RuntimeAgentRunResponse` with `main_question` and `sub_qa` in the frontend.

**Details:**
- In `src/frontend/src/utils/api.ts`: Add interface `SubQuestionAnswer` with `sub_question: string`, `sub_answer: string`, optional `tool_call_input?: string`, `sub_agent_response?: string` (treat absent as `""`). Extend `RuntimeAgentRunResponse` with `main_question?: string` (absent → `""`) and `sub_qa?: SubQuestionAnswer[]` (absent → `[]`). Keep `output: string` required.

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Add `SubQuestionAnswer`; extend `RuntimeAgentRunResponse` with `main_question`, `sub_qa`. |

**How to test:** Frontend tests; no runtime change yet.

---
## Section 10: Update runAgent response validator

**Goal:** `runAgent` validator accepts and validates `main_question` and `sub_qa`; older responses (only `output`) still pass.

**Details:**
- In `src/frontend/src/utils/api.ts`: Update the `validate` function in `runAgent` to accept and validate `main_question` (string) and `sub_qa` (array of objects with `sub_question`, `sub_answer`, and optionally `tool_call_input`, `sub_agent_response`). Treat missing fields as empty string or empty array.

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Update `runAgent` validator for new fields. |

**How to test:** Frontend tests. Call `POST /api/agents/run` from the app; confirm no "malformed response" when backend returns `main_question` and `sub_qa`.

---

## Section 11: Display main_question in Final Readout

**Goal:** Show main question from API response in "Final Readout"; fallback to submitted query when absent.

**Details:**
- In `src/frontend/src/App.tsx`: For the main question line, use `result.data.main_question` when non-empty, else `submittedQuery`. Store full run result if needed (e.g. `lastRunResponse`) so `main_question` and later `sub_qa` can be shown. Optionally update label (e.g. "Main question:" or "Requested query:").

| File | Purpose |
|------|--------|
| `src/frontend/src/App.tsx` | Use main_question from run response in Final Readout with fallback to submitted query. |

**How to test:** Frontend tests. Manually run a query; confirm main question line shows API `main_question` when present, else submitted query.

---
## Section 12: Final Readout layout — Main question, Final answer, Subquestions section

**Goal:** Restructure the "Final Readout" panel into three clear, labeled sections: **Main question**, **Final answer**, and **Subquestions & subanswers**. Use semantic markup and consistent spacing so the hierarchy is obvious. When there is no run yet or no `sub_qa`, the Subquestions section shows a short empty state (e.g. "No subquestions for this run.").

**Details:**
- In `src/frontend/src/App.tsx`: Replace the current single-block Final Readout with three distinct sections (e.g. subsections or clearly labeled blocks). (1) **Main question** — display `lastRunResponse?.main_question` or fallback to `submittedQuery` or "No query submitted yet." (2) **Final answer** — display `answer` or "No answer yet." (3) **Subquestions & subanswers** — container only: if `lastRunResponse?.sub_qa` is empty or missing, render the empty-state message; do not yet render per-item content (Section 13). Use clear headings/labels (e.g. "Main question", "Final answer", "Subquestions & subanswers").

| File | Purpose |
|------|--------|
| `src/frontend/src/App.tsx` | Three-section Final Readout layout and Subquestions empty state. |

**How to test:** Manually run a query; confirm Main question, Final answer, and Subquestions section (with empty state when no sub_qa) are clearly separated and readable.

**Test results:**
- Code changes:
  - Updated `src/frontend/src/App.tsx` to render Final Readout as three semantic subsections with headings: "Main question", "Final answer", and "Subquestions & subanswers".
  - Subquestions container currently renders only state text per scope: "No subquestions for this run." when `sub_qa` is empty/missing, and no per-item rendering.
  - Added run visibility log field in `handleRun` success path: `subQuestionCount`.
  - Updated `src/frontend/src/App.test.tsx` run-flow test assertions to verify the three Final Readout headings and the Subquestions empty state when response only has `output`.
- Docker lifecycle and container handling:
  - Pre-work full clean reboot completed: `docker compose down -v --rmi all && docker compose build && docker compose up -d`.
  - Post-change container restart completed: `docker compose restart frontend`.
  - Running state verified via `docker compose ps` (`db` healthy; `backend`, `frontend`, and `chrome` up).
- Tests run:
  - `docker compose exec frontend npm run test -- --run`
    - Result: `4 passed`.
  - `docker compose exec frontend npm run typecheck`
    - Result: pass.
  - `docker compose exec frontend npm run build`
    - Result: pass.
- Logs reviewed:
  - `docker compose logs --no-color --tail=120 frontend`
  - `docker compose logs --no-color --tail=120 backend`
  - `docker compose logs --no-color --tail=120 db`
- Log issues / results:
  - No new runtime errors introduced by this section.

---
