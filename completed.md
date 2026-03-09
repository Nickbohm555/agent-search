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

## Section 3: Build expansion node - query list generation per sub-question

**Single goal:** Add a graph node that expands each sub-question into a bounded query list.

**Details completed:**
- Added explicit backend dependency declarations for expansion flow in `src/backend/pyproject.toml` and lock refresh in `src/backend/uv.lock` (`langchain`, `langchain-classic`).
- Added `src/backend/services/query_expansion_service.py` with a `MultiQueryRetriever`-backed expansion wrapper.
- Implemented normalization and bounds in expansion service: trim/collapse whitespace, dedupe, drop empties, max query count, max query length.
- Implemented deterministic fallback to original sub-question when expansion cannot run (missing API key) or fails.
- Added expansion graph node in `src/backend/services/agent_service.py`: `run_expand_node(...)` with structured logging.
- Added graph-state update helper `apply_expand_node_output_to_graph_state(...)` to persist `expanded_queries` per sub-question artifact and keep compatibility `SubQuestionAnswer.expanded_query` populated.
- Added tests in `src/backend/tests/services/test_query_expansion_service.py` for normalization and fallback behavior.
- Added tests in `src/backend/tests/services/test_agent_service.py` for expansion node output and graph-state update behavior.
- Updated docs in `README.md` and `src/frontend/public/run-flow.html` to include expansion node/runtime references.

### Useful logs

```text
docker compose build && docker compose up -d
-> backend/frontend rebuilt and started
-> backend recreated with new dependency graph (langchain-classic installed)

curl http://localhost:8000/api/health
-> {"status":"ok"}

docker compose logs --tail=120 backend
-> Alembic migration context started
-> Uvicorn startup complete
-> GET /api/health 200 OK

docker compose logs --tail=120 frontend
-> Vite dev server ready at http://localhost:5173/

docker compose logs --tail=120 db
-> PostgreSQL ready to accept connections

docker compose exec backend uv run pytest tests/services/test_query_expansion_service.py tests/services/test_agent_service.py -k "expand_queries_for_subquestion or run_expand_node or apply_expand_node_output_to_graph_state or run_decomposition_node"
-> 7 passed, 55 deselected in ~2s
```

## Section 4: Build search node - multi-query retrieval with merge/dedupe

**Single goal:** Implement graph search node that retrieves across expanded queries and merges candidates.

**Details completed:**
- Implemented graph search-node execution in `src/backend/services/agent_service.py` via `run_search_node(...)`.
- Added configurable over-fetch via env var `SEARCH_NODE_K_FETCH` and per-call override.
- Added deterministic multi-query merge logic that dedupes by stable identity (`document_id` first; fallback `source+content`).
- Added retrieval provenance capture for every retrieval event (query index, query rank, dedupe flag, identity, source, document_id).
- Added graph-state update helper `apply_search_node_output_to_graph_state(...)` to persist `retrieved_docs`, `citation_rows_by_index`, and `retrieval_provenance` in sub-question artifacts.
- Preserved compatibility fields by writing merged retrieval output back into `sub_qa[].sub_answer` citation-contract lines and `sub_qa[].tool_call_input` payload metadata.
- Extended graph schema contracts in `src/backend/schemas/agent.py` with `retrieval_provenance` on `SubQuestionArtifacts` and `SearchNodeOutput`.
- Added reusable vector-store primitive `search_documents_for_queries(...)` in `src/backend/services/vector_store_service.py` for multi-query retrieval orchestration.
- Added/updated backend tests in `src/backend/tests/services/test_agent_service.py` covering merge/dedupe determinism and state-apply behavior.
- Updated required docs (`README.md` and `src/frontend/public/run-flow.html`) to reflect the explicit graph search node and provenance behavior.
- Fixed two unrelated failing backend tests discovered during mandatory full-suite run:
  - Restored legacy-compatible `wiki_page` metadata in vector-store normalization.
  - Preserved extra wiki metadata keys (for example `language`) while still normalizing `title`/`source`.

### Useful logs

```text
docker compose down -v --rmi all && docker compose build && docker compose up -d
-> backend/frontend rebuilt; db healthy; backend/frontend/chrome started

docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py -k "search_node or apply_search_node"'
-> 2 passed, 59 deselected in 2.12s

docker compose exec backend sh -lc 'cd /app && uv run pytest'
-> 111 passed, 3 warnings in 24.24s

docker compose restart backend frontend
-> backend/frontend restarted cleanly

curl http://localhost:8000/api/health
-> {"status":"ok"}

docker compose logs --tail=120 backend
-> Uvicorn startup complete, app startup complete, no fatal runtime errors

docker compose logs --tail=120 frontend
-> Vite ready on http://localhost:5173/

docker compose logs --tail=120 db
-> PostgreSQL ready; no crash/restart loops
