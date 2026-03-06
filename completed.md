## Section 1: Add decomposition-only LLM call and prompt

**Onyx article:** Lesson 1 — "Agents are just prompts": planning is *completely isolated* from execution; use a specific system prompt and curate input so the planning task is well defined and simple.

**Single goal:** Add one new LLM call that takes user query + initial_search_context and returns a list of sub-questions. No flow tracking, write_todos, or task() in this call.

**Details:**
- In agent_service, after building initial_search_context and before invoking the coordinator, run a dedicated decomposition call.
- Input: user query + initial_search_context. Output: list of sub-questions only (e.g. JSON array or one-question-per-line).
- Add a dedicated system prompt (e.g. in coordinator.py as `_DECOMPOSITION_ONLY_PROMPT` or a small new module). This step produces the "plan"; Section 3 will consume it.

**Tech stack and dependencies**
- No new packages; one new LLM invoke path (same model as coordinator or env-configured).
- get_vector_store / build_initial_search_context unchanged.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/agent_service.py | Run decomposition-only step after initial_search_context is built; capture raw output for Section 2. |
| src/backend/agents/coordinator.py | Add _DECOMPOSITION_ONLY_PROMPT for the decomposition-only call. |

**How to test:** Run a query; in logs or trace confirm one LLM call returns only sub-questions (no task() or write_todos). Unit test: mock LLM returning a fixed list, assert agent_service captures it.

### Completion notes (March 6, 2026)
- Added `_DECOMPOSITION_ONLY_PROMPT` and exported prompt accessor via `agents`.
- Added `_run_decomposition_only_llm_call(...)` in `agent_service` and invoked it immediately after initial context construction and before coordinator invocation.
- Added runtime logging for decomposition-only output capture.
- Updated service unit test to mock decomposition call and assert capture.

### Useful logs
- `Runtime agent run start query=What is vector search? query_length=22`
- `Initial decomposition context built query=What is vector search? docs=0 k=5 score_threshold=None`
- `Decomposition-only LLM output captured output_length=26 output_preview=["What is vector search?"]`
- `Coordinator decomposition input prepared query=What is vector search? context_items=0`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`

### Tests run
- `docker compose exec backend uv run pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py` -> `16 passed`
- `docker compose exec backend uv run pytest tests/api -m smoke` -> `3 deselected / 0 selected`

---

## Section 2: Decomposition output format contract

**Onyx article:** Lesson 1 — Plan is the only context brought into the research phase; format must be consumable by the coordinator and _extract_sub_qa.

**Single goal:** Define and enforce the decomposition output format so the coordinator and _extract_sub_qa can consume it. Document the contract.

**Details:**
- Sub-questions must have trailing `?`, one concept per question. Format: list of strings (e.g. JSON array or one-per-line) matching _build_coordinator_input_message and _extract_sub_qa expectations.
- In agent_service: parse/validate decomposition LLM output into a list of sub-question strings; pass that list to the next phase (Section 3). If the LLM returns malformed output, normalize or fail clearly.
- Document the contract in coordinator.py (near _DECOMPOSITION_ONLY_PROMPT) or in docs/section-03: "Decomposition output is a list of sub-questions, each ending with ?, one concept per question."

**Tech stack and dependencies**
- No new packages; parsing/validation and docs only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/agent_service.py | Parse/validate decomposition output into list of sub-questions; pass to coordinator phase. |
| src/backend/agents/coordinator.py or docs/section-03 | Document decomposition output format contract. |

**How to test:** Unit test: mock LLM returning various formats (JSON, newline-separated); assert agent_service produces a list of strings with `?`. Run a query; confirm parsed list is passed to coordinator.

### Completion notes (March 6, 2026)
- Added `_parse_decomposition_output(...)` in `agent_service` with contract enforcement for JSON arrays and newline/bullet formats.
- Normalization now guarantees trailing `?`, removes duplicates, and falls back clearly to normalized main question on malformed/empty outputs.
- `run_runtime_agent(...)` now parses decomposition output and passes the normalized list into `_build_coordinator_input_message(...)`.
- Coordinator handoff message now includes `Normalized decomposition output (contract-compliant list of sub-questions)` for Section 3 consumption.
- Added contract documentation comment near `_DECOMPOSITION_ONLY_PROMPT` in `coordinator.py`.

### Useful logs
- `Decomposition-only LLM output captured output_length=2 output_preview=[]`
- `Decomposition output parsed sub_question_count=1 sub_questions=["What changed in NATO policy?"]`
- `Coordinator decomposition input prepared query=What changed in NATO policy? context_items=0 parsed_sub_questions=1`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- `Container agent-search-backend Restarting`

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py'` -> `20 passed`

---

## Section 3: Coordinator receives only sub-questions (no decomposition in same context)

**Onyx article:** Lesson 1 — Plan is the only context brought into the research phase; "contrast this with instructing the LLM to first generate a plan then immediately execute on it" (avoid that; we do decomposition then hand off).

**Single goal:** Coordinator receives only the list of sub-questions from Sections 1–2; it does not perform decomposition in the same context.

**Details:**
- Agent_service builds the coordinator input from the Section 2 sub-questions list only (e.g. a single HumanMessage listing them). Do not pass the full "Decomposition input" that asks the coordinator to derive sub-questions from context.
- Update _COORDINATOR_PROMPT: remove or narrow decomposition rules; state that sub-questions are provided and the coordinator must call write_todos, maintain the flow file, and delegate each via task(description=sub_question).
- _extract_sub_qa and the per-subquestion pipeline unchanged; only the input and coordinator role change.
- Update docs/section-03: note that decomposition is isolated in Sections 1–2.

**Tech stack and dependencies**
- No new packages; prompt and message-building only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/agent_service.py | Build coordinator message from sub-questions list (not _build_coordinator_input_message(query, context)). |
| src/backend/agents/coordinator.py | Update _COORDINATOR_PROMPT: no decomposition; receive sub-questions; write_todos, flow, task(description=sub_question). |
| docs/section-03-question-decomposition-informed-by-context.md | Note decomposition is done in a prior step (Sections 1–2). |

**How to test:** Run a query; confirm coordinator receives a message that lists sub-questions (not "derive sub-questions from context"). Confirm task() calls match that list. Extend test_agent_service / test_coordinator_agent as needed.

### Completion notes (March 6, 2026)
- Updated `agent_service._build_coordinator_input_message(...)` to accept only the normalized sub-question list and removed query/context decomposition payload from coordinator input.
- Updated coordinator handoff logging to `Coordinator sub-question input prepared ...` including delegated sub-question list for visibility.
- Updated `_COORDINATOR_PROMPT` so stage 2 consumes provided sub-questions and explicitly forbids same-context decomposition.
- Rewrote `docs/section-03-question-decomposition-informed-by-context.md` to document isolated decomposition handoff from Sections 1–2 into coordinator delegation.
- Updated backend tests (`test_agent_service`, `test_coordinator_agent`) to validate new coordinator input contract and prompt semantics.

### Useful logs
- `Runtime agent run start query=What is pgvector used for? query_length=26`
- `Decomposition output parsed sub_question_count=2 sub_questions=["What is pgvector?", "What are the use cases of pgvector?"]`
- `Coordinator sub-question input prepared parsed_sub_questions=2 sub_questions=["What is pgvector?", "What are the use cases of pgvector?"]`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- `docker compose ps` shows `db` healthy and `backend/frontend/chrome` up.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py'` -> `20 passed`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK`

---

## Section 4: Coordinator only delegates and gathers (no final answer synthesis)

**Onyx article:** Lesson 2 — "Deep frying is unhealthy": "The Orchestrator just gathers context. It doesn't meaningfully transform or reinterpret information"; orchestrator gathers, doesn't synthesize the final answer.

**Single goal:** The coordinator does not synthesize the final answer from subanswers; agent_service owns final answer generation via generate_initial_answer.

**Details:**
- In _COORDINATOR_PROMPT, remove or replace "After you have subanswers, use them to answer the main question with one concise answer." The coordinator only delegates via task() and gathers subagent responses.
- agent_service already uses generate_initial_answer(main_question, initial_search_context, sub_qa) for the API response; coordinator_output is only for logging. API response shape unchanged.
- If the framework expects a final assistant message from the coordinator, use a short summary like "Delegation complete; subanswers collected."

**Tech stack and dependencies**
- No new packages; prompt change in coordinator.py only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/agents/coordinator.py | Remove final-answer synthesis from _COORDINATOR_PROMPT; coordinator only delegates and reports completion. |

**How to test:** Run a query; confirm API response still comes from generate_initial_answer and shape is unchanged. Confirm coordinator's last message does not contain the main answer. test_agent_service assertions on RuntimeAgentRunResponse still pass.

### Completion notes (March 6, 2026)
- Updated `_COORDINATOR_PROMPT` flow stages so coordinator ends at delegation/gather completion handoff and no longer claims ownership of final answer synthesis.
- Replaced synthesis instruction with explicit completion behavior:
  - coordinator only delegates and gathers subagent outputs,
  - must not synthesize the final main-question answer,
  - must end with a short status message (`Delegation complete; subanswers collected.`).
- Added an explicit flow-file sequencing guardrail in prompt instructions: call `read_file` first, create with `write_file` if missing, then use `edit_file`.
- Updated `src/backend/tests/agents/test_coordinator_agent.py` expectations to assert delegate/gather-only completion semantics.

### Useful logs
- `Coordinator raw output captured output_length=42 output_preview=Delegation complete; subanswers collected.`
- `Initial answer generation start question_len=17 context_items=0 sub_qa_count=1`
- `Initial answer generation complete via LLM answer_len=373 model=gpt-4.1-mini`
- `Runtime agent run complete output_length=523 output_preview=Pgvector is a PostgreSQL extension ...`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- `docker compose ps` showed `backend` up, `db` healthy, `frontend` up after backend restart.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run python -m pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py'` -> `20 passed`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector?"}'` -> `200 OK` with unchanged `RuntimeAgentRunResponse` shape (`main_question`, `sub_qa`, `output`)
