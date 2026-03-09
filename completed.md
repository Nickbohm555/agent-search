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

## Section 5: Build rerank node - reorder retrieved candidates before answering

**Single goal:** Add reranking node that reorders merged retrieval candidates and trims to final top_n context.

**Details completed:**
- Added production reranker dependency `flashrank>=0.2.10` in `src/backend/pyproject.toml` and refreshed `src/backend/uv.lock`.
- Replaced custom lexical-overlap reranking in `src/backend/services/reranker_service.py` with a `flashrank` adapter (`Ranker` + `RerankRequest`) and explicit env-driven config (`RERANK_ENABLED`, `RERANK_TOP_N`, `RERANK_MODEL_NAME`, `RERANK_CACHE_DIR`).
- Implemented deterministic fallback path to original document order when reranker is disabled/unavailable/fails.
- Added graph rerank node in `src/backend/services/agent_service.py`:
  - `run_rerank_node(...)` to rerank merged `retrieved_docs` and emit scored `reranked_docs`.
  - `apply_rerank_node_output_to_graph_state(...)` to persist reranked rows and scores into graph artifacts and compatibility payloads.
- Persisted rerank observability data in state/compat payload (`rerank_provenance`, `rerank_top_n`) and mapped rerank scores onto `CitationSourceRow.score`.
- Updated existing per-subquestion rerank pipeline logging/config usage to the new flashrank-backed config.
- Added/updated tests:
  - `src/backend/tests/services/test_reranker_service.py` (flashrank order/top_n + fallback scenarios).
  - `src/backend/tests/services/test_agent_service.py` (graph rerank node output/state updates and rerank application behavior).
- Updated docs in `README.md` and `src/frontend/public/run-flow.html` to reflect rerank node placement and flashrank-based production behavior.

### Useful logs

```text
docker compose exec backend uv lock
-> Added flashrank v0.2.10 and transitive packages (onnxruntime, tokenizers, huggingface-hub, etc.)

docker compose exec backend uv run --with pytest pytest tests/services/test_reranker_service.py tests/services/test_agent_service.py -k "rerank"
-> 10 passed, 57 deselected in 3.21s

docker compose exec backend uv run --with pytest pytest tests/services/test_reranker_service.py tests/services/test_agent_service.py
-> 67 passed, 2 warnings in 23.22s

docker compose build
-> agent-search-backend Built
-> agent-search-frontend Built

docker compose restart backend frontend
-> backend/frontend restarted successfully

curl http://localhost:8000/api/health
-> {"status":"ok"}

docker compose logs --tail=80 backend frontend db
-> backend startup complete (uvicorn + alembic)
-> frontend Vite ready on http://localhost:5173/
-> db ready to accept connections
```

## Section 6: Build subanswer node - answer per sub-question with citations

**Single goal:** Generate one grounded subanswer per sub-question using reranked docs and mandatory citation markers.

**Details completed:**
- Added graph subanswer-node runtime in `src/backend/services/agent_service.py`:
  - `run_answer_subquestion_node(...)` now generates a subanswer from reranked docs, verifies grounding, enforces citation markers (for example `[1]`), and validates citation indices map to ranked rows.
  - Enforces exact fallback text `nothing relevant found` when reranked docs are missing or the generated answer is unsupported.
- Added graph state application in `src/backend/services/agent_service.py`:
  - `apply_answer_subquestion_node_output_to_graph_state(...)` now persists `sub_answer`, citation usage, and supporting source rows into graph artifacts and compatibility `sub_qa` fields.
  - Added compatibility payload details in `tool_call_input`: `citation_usage` and `supporting_source_rows`.
- Extended node output schema in `src/backend/schemas/agent.py` (`AnswerSubquestionNodeOutput`) with:
  - `citation_indices_used`, `answerable`, and `verification_reason`.
- Added backend tests in `src/backend/tests/services/test_agent_service.py` for:
  - Cited success path (citation markers map to ranked doc rows).
  - Required fallback path (`nothing relevant found`) when unsupported.
  - Graph-state apply behavior for citation usage/supporting rows and `SubQuestionAnswer` compatibility fields.
- Updated required docs in `README.md` and `src/frontend/public/run-flow.html` to include the subanswer graph node and fallback behavior.

### Useful logs

```text
docker compose down -v --rmi all && docker compose build && docker compose up -d
-> full clean restart complete
-> backend/frontend rebuilt and started; db healthy

docker compose exec backend uv run --with pytest python -m pytest tests/services/test_agent_service.py tests/services/test_subanswer_service.py tests/services/test_subanswer_verification_service.py
-> 73 passed, 2 warnings in 24.22s

docker compose restart backend
-> backend restarted successfully

docker compose logs --tail=200 backend
-> Uvicorn startup complete
-> reload events for updated files (schemas/agent.py, services/agent_service.py, tests/services/test_agent_service.py)
-> app startup complete (no fatal errors)

docker compose logs --tail=120 frontend
-> Vite ready at http://localhost:5173/

docker compose logs --tail=120 db
-> PostgreSQL ready to accept connections

curl http://localhost:8000/api/health
-> {"status":"ok"}
```

## Section 7: Build final synthesis node - compose final answer from subanswers

**Single goal:** Synthesize final answer from per-subquestion answers while preserving grounded citations.

**Details completed:**
- Adapted synthesis service in `src/backend/services/initial_answer_service.py` with `generate_final_synthesis_answer(...)`, which composes final output from `main_question + sub_qa` and preserves citation markers through existing synthesis constraints.
- Added final synthesis graph node functions in `src/backend/services/agent_service.py`:
  - `run_synthesize_final_node(...)` to synthesize final answer from graph-state subanswers.
  - `apply_synthesize_final_node_output_to_graph_state(...)` to write deterministic compatibility fields (`final_answer` and `output`) back to state.
- Kept API response shape unchanged (`output` + `sub_qa`) by reusing existing runtime mapping contracts.
- Added synthesis-focused tests:
  - `src/backend/tests/services/test_initial_answer_service.py` verifies final synthesis wrapper preserves grounded citation-bearing subanswers.
  - `src/backend/tests/services/test_agent_service.py` verifies synthesize-node invocation inputs and graph-state apply behavior.
- Updated required docs:
  - `README.md` runtime map now includes final synthesis graph-node helper row.
  - `src/frontend/public/run-flow.html` call chain and runtime table now include `run_synthesize_final_node(...)` + `apply_synthesize_final_node_output_to_graph_state(...)`.

### Useful logs

```text
docker compose restart backend
-> Container agent-search-backend  Restarting
-> Container agent-search-backend  Started

docker compose exec backend uv run pytest tests/services/test_initial_answer_service.py tests/services/test_agent_service.py -k "synthesize_final_node or apply_synthesize_final_node_output_to_graph_state or generate_final_synthesis_answer"
-> error: Failed to spawn: `pytest`
-> Caused by: No such file or directory (os error 2)

docker compose exec backend uv run --with pytest pytest tests/services/test_initial_answer_service.py tests/services/test_agent_service.py -k "synthesize_final_node or apply_synthesize_final_node_output_to_graph_state or generate_final_synthesis_answer"
-> 3 passed, 69 deselected in 2.08s

docker compose logs --no-color --tail=160 backend frontend db
-> backend/app startup complete; watch reloads for changed synthesis files; no fatal runtime errors
-> frontend Vite ready on http://localhost:5173/
-> db ready to accept connections

docker compose ps
-> backend/frontend/chrome up; db healthy

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}
```
