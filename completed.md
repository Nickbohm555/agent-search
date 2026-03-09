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

## Section 2: Build decomposition node from existing logic - state-graph entry

**Single goal:** Reuse current decomposition logic as the first graph node that produces normalized sub-questions.

**Details completed:**
- Lifted decomposition runtime logic into a dedicated graph node function: `run_decomposition_node(...)` in `src/backend/services/agent_service.py`.
- Preserved normalization guarantees through existing parse helpers (`?` suffix, dedupe, bounded output behavior).
- Node now emits `decomposition_sub_questions` immediately through `DecomposeNodeOutput` for downstream graph fanout.
- Preserved fallback behavior on decomposition timeout/failure using normalized main question fallback.
- Updated `run_runtime_agent(...)` to call `run_decomposition_node(...)` as the decomposition entry path.
- Added decomposition-node tests for normalized output and timeout fallback in `src/backend/tests/services/test_agent_service.py`.
- Updated docs in `README.md` and `src/frontend/public/run-flow.html` to reflect the explicit decomposition node entry.

### Useful logs

```text
docker compose down -v --rmi all && docker compose build && docker compose up -d
-> backend/frontend rebuilt and all services started
-> db healthy, backend/frontend/chrome up

docker compose restart backend
-> backend restarted cleanly

docker compose logs --tail=160 backend
-> Uvicorn startup complete; app startup complete; no runtime errors

docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py -k decomposition
-> 12 passed, 45 deselected in 4.04s
```
