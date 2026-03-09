## Section 1: Define state graph contracts - graph state and node IO

**Single goal:** Introduce a typed state model and node contracts for the full workflow before migrating execution.

**Details completed:**
- Defined graph-level state for `main_question`, `decomposition_sub_questions`, per-subquestion artifacts (`expanded_queries`, `retrieved_docs`, `reranked_docs`, `sub_answer`), and `final_answer`.
- Added stable node input/output contracts for `decompose`, `expand`, `search`, `rerank`, `answer_subquestion`, and `synthesize_final`.
- Preserved compatibility fields used by current API response shape (`sub_qa`, `output`) in graph state and response mapping helper.
- Added citation carrier format in state using ranked source rows keyed by citation index.
- Added run observability metadata contracts (`run_id`, `thread_id`, `trace_id`, `correlation_id`) and shared Langfuse metadata helper conventions.
- Added graph-state conversion helpers in service layer and tests validating backward-compatible mapping to `RuntimeAgentRunResponse`.
- Updated documentation in `README.md` and `src/frontend/public/run-flow.html`.

### Useful logs

```text
docker compose build
-> agent-search-backend  Built
-> agent-search-frontend Built

docker compose up -d
-> backend/frontend/db/chrome started successfully

docker compose exec backend uv run python -m pytest tests/services/test_agent_service.py
-> 55 passed, 2 warnings in 23.87s

curl http://localhost:8000/api/health
-> {"status":"ok"}

docker compose ps
-> db healthy, backend/frontend/chrome up
```
