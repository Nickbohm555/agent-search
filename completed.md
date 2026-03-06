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
