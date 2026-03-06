## Section 1: Coordinator flow tracking via write_todos

**Single goal:** The coordinator agent uses the deep-agents (LangGraph) `write_todos` planning tool to keep track of the pipeline flow so it does not lose context across steps.

**Flow the coordinator coordinates (align with flow.jpg):**

1. **From the user question, parallel inputs:**
   - **Exploratory (fast & simple) search** / **full search on the original question** -> results feed into decomposition context and initial-answer generation.
   - **Decompose question into sub-questions** -> produces initial sub-questions (one per concept).

2. **Per initial sub-question (in parallel):** For each initial sub-question, run in order: **Expand** (query expansion) -> **Search** (retrieval) -> **Validate** (doc validation) -> **Rerank** -> **Answer** (subanswer generation) -> **Check** (subanswer verification). All sub-question results feed into **Generate initial answer**.

3. **Generate initial answer:** Combine initial-search results and the aggregated sub-answers into one initial answer.

4. **Need refinement?** Decision: if **No** -> output the initial answer as the final answer. If **Yes** -> continue below.

5. **Refinement path:**
   - **Generate new & informed sub-questions** from the initial answer and unanswerable sub-questions so the new sub-questions target gaps.
   - **Per refined sub-question (in parallel):** Same pipeline as step 2: Expand -> Search -> Validate -> Rerank -> Answer -> Check.
   - **Produce & validate refined answer** from the refined sub-answers.
   - **Compare refined to initial answer** (e.g. for quality or final synthesis), then output the final answer.

**Details:**
- At run start, the coordinator creates or updates a plan via `write_todos` with todos that mirror the stages above (e.g. initial search, decomposition, parallel initial sub-question pipelines, initial answer, refinement decision; and when refining: refined sub-questions, refined pipelines, refined answer, compare -> output).
- The coordinator marks items in_progress and completed as it delegates and synthesizes. No change to decomposition or RAG logic; only wiring so the coordinator uses the existing `write_todos` tool with a plan aligned to this flow (see flow.jpg). The only difference is the 'Entity Relationship' step no longer exists or is needed.

**Implemented files:**
- `src/backend/agents/coordinator.py`
- `src/backend/tests/agents/test_coordinator_agent.py`

**Validation logs:**
- Unit tests: `docker compose exec backend sh -lc 'uv pip install pytest && uv run pytest tests/agents/test_coordinator_agent.py tests/services/test_agent_service.py'`
  - Result: `4 passed in 1.25s`
- Integration runtime call:
  - `curl -sS -m 90 -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is the Strait of Hormuz?"}'`
  - Result: `200 OK` with populated `sub_qa` and final `output`.
- Backend log evidence included:
  - `Coordinator planning contract enabled tool=write_todos ...`
  - `Agent message[...] AI tool_call tool=write_todos args=...`
  - `Runtime agent run complete output_length=...`
