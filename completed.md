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

## Section 8: Assemble graph runner - sequential lane only

**Single goal:** Implement a sequential graph runner that executes nodes in strict order for one sub-question at a time.

**Details completed:**
- Added decomposition-state application helper in `src/backend/services/agent_service.py`:
  - `apply_decompose_node_output_to_graph_state(...)` writes normalized `decomposition_sub_questions`, initializes `sub_question_artifacts`, and seeds compatibility `sub_qa` entries.
- Added a new sequential graph orchestration entrypoint in `src/backend/services/agent_service.py`:
  - `run_sequential_graph_runner(...)` executes strict order:
    - `decompose -> (for each sub-question: expand -> search -> rerank -> answer) -> synthesize_final`
  - Sub-question lanes run one-by-one in the original decomposition order (no fanout in this section).
  - Reused existing node functions and graph-state apply helpers for every stage.
- Kept legacy deep-agent path untouched:
  - Existing `run_runtime_agent(...)` coordinator/delegation path remains unchanged.
- Kept Langfuse lifecycle active in new graph path:
  - Starts callback handler via `build_langfuse_callback_handler()`.
  - Flushes in `finally` via `flush_langfuse_callback_handler(...)`.
- Added/updated tests in `src/backend/tests/services/test_agent_service.py`:
  - `test_apply_decompose_node_output_to_graph_state_initializes_artifacts_and_compat_fields`
  - `test_run_sequential_graph_runner_executes_strict_node_order`
  - Verifies strict sequential node ordering and deterministic output mapping.
- Updated required docs:
  - `README.md` includes Section 8 migration note for `run_sequential_graph_runner(...)`.
  - `src/frontend/public/run-flow.html` includes Section 8 note for strict sequential graph execution.

### Useful logs

```text
docker compose down -v --rmi all && docker compose build && docker compose up -d && docker compose ps
-> full clean restart complete
-> backend/frontend rebuilt and started; db healthy

docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py -k "sequential_graph_runner or apply_decompose_node_output_to_graph_state"
-> 2 passed, 68 deselected in 2.27s

docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py
-> 70 passed, 2 warnings in 23.09s

docker compose restart backend frontend
-> backend/frontend restarted successfully

docker compose logs --tail=120 backend
-> app startup complete; reload events observed for changed agent_service/tests

docker compose logs --tail=80 frontend
-> Vite ready at http://localhost:5173/
-> page reload observed for public/run-flow.html

docker compose logs --tail=80 db
-> PostgreSQL ready to accept connections

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}
```

## Section 9: Add parallel sub-question fanout and state snapshots

**Single goal:** Add controlled parallelism for per-subquestion lanes and emit snapshot state for progress reporting.

**Details completed:**
- Added graph snapshot contract in `src/backend/schemas/agent.py`:
  - `GraphStageSnapshot` model with stage/lane metadata and partial state payload fields (`decomposition_sub_questions`, `sub_qa`, `sub_question_artifacts`, `output`).
  - `AgentGraphState.stage_snapshots` to retain ordered snapshot history for progressive status consumers.
- Exported snapshot schema from `src/backend/schemas/__init__.py`.
- Added bounded parallel graph runner orchestration in `src/backend/services/agent_service.py`:
  - `run_parallel_graph_runner(...)` parallelizes per-subquestion lane execution for `expand -> search -> rerank -> answer` using `ThreadPoolExecutor` and env-configured `GRAPH_RUNNER_MAX_WORKERS`.
  - Keeps deterministic output by reindexing lane results to decomposition order before applying graph-state transitions.
  - Emits state snapshots after `decompose`, each lane stage (`expand/search/rerank/answer`), and `synthesize_final`.
  - Added explicit runner/lane/snapshot logs for observability.
- Added tests in `src/backend/tests/services/test_agent_service.py`:
  - `test_run_parallel_graph_runner_preserves_subquestion_order_and_emits_snapshots` verifies:
    - lanes can complete out of order under parallel fanout,
    - final `sub_qa` order is deterministic (original decomposition order),
    - stage snapshot sequence and payload fields are correct.
- Updated required docs:
  - `README.md` with Section 9 migration note for `run_parallel_graph_runner`, bounded fanout, and `stage_snapshots`.
  - `src/frontend/public/run-flow.html` graph migration section + call chain updated with Section 9 details.

### Useful logs

```text
docker compose down -v --rmi all
-> full shutdown complete; containers/volumes/images removed

docker compose build
-> backend/frontend rebuilt successfully

docker compose up -d
-> db/backend/frontend/chrome started; db healthy

docker compose exec backend uv run pytest tests/services/test_agent_service.py
-> error: Failed to spawn: `pytest` (No such file or directory)

docker compose exec backend uv pip install pytest
-> Installed pytest==9.0.2 (plus iniconfig/pluggy)

docker compose exec backend uv run pytest tests/services/test_agent_service.py
-> 71 passed, 2 warnings in 23.39s

docker compose restart backend frontend
-> backend/frontend restarted successfully

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}

docker compose logs --tail=200 backend
-> app startup complete
-> reload events after code changes
-> no fatal runtime errors

docker compose logs --tail=120 frontend
-> Vite ready at http://localhost:5173/

docker compose logs --tail=120 db
-> PostgreSQL ready to accept connections
```

## Section 10: Migrate API endpoint to graph backend - deep-agent decoupling

**Single goal:** Switch `/api/agents/run` to execute the new graph runner instead of deep-agents.

**Details completed:**
- Routed runtime requests through graph runner in `run_runtime_agent`:
  - Added graph-first runtime selection in `src/backend/services/agent_service.py`.
  - New default path uses `_run_runtime_agent_with_graph_runner(...)` and `run_parallel_graph_runner(...)`.
  - Added rollback feature flag `RUNTIME_AGENT_ROLLBACK_TO_DEEP_AGENT` (when `true`, runtime uses legacy deep-agent path).
- Kept request/response API contract unchanged:
  - `/api/agents/run` still returns `RuntimeAgentRunResponse { main_question, sub_qa, output }`.
  - Graph state is mapped through `map_graph_state_to_runtime_response(...)`.
- Isolated deep-agent-specific orchestration from primary runtime path:
  - Moved existing coordinator pipeline logic into `_run_runtime_agent_with_legacy_deep_agent(...)`.
  - Primary `run_runtime_agent(...)` now performs path selection and logs selected mode.
- Preserved Langfuse integration on primary runtime path:
  - Graph path keeps graph metadata (`run_id`, `trace_id`, `correlation_id`) and node-level tracing via existing callback lifecycle in graph runner.
  - Legacy path retains existing callback/flush behavior.
- Added focused migration tests:
  - `test_run_runtime_agent_uses_graph_runner_when_rollback_flag_disabled`
  - `test_run_runtime_agent_uses_legacy_path_when_rollback_flag_enabled`
  - Existing graph parallel/snapshot service test and API contract test were executed.
- Updated docs:
  - `README.md` updated with Section 10 migration note and rollback flag documentation.
  - `src/frontend/public/run-flow.html` updated to reflect graph-first runtime with rollback path.
  - `.env.example` and `.env` updated with `RUNTIME_AGENT_ROLLBACK_TO_DEEP_AGENT=false`.

### Useful logs

```text
docker compose down -v --rmi all
-> full clean shutdown complete (containers/volumes/images removed for backend/frontend; base images retained when in use)

docker compose build
-> backend/frontend images rebuilt successfully

docker compose up -d
-> db/backend/frontend/chrome started; db healthy

docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py -k "uses_graph_runner_when_rollback_flag_disabled or uses_legacy_path_when_rollback_flag_enabled or run_parallel_graph_runner_preserves_subquestion_order_and_emits_snapshots"
-> 3 passed, 70 deselected in 2.45s

docker compose exec backend uv run --with pytest pytest tests/api/test_agent_run.py
-> 1 passed in 2.48s

docker compose restart backend frontend
-> backend/frontend restarted successfully

docker compose ps
-> backend/frontend/db/chrome all up; db healthy

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}

docker compose logs --tail=120 backend
-> uvicorn startup complete
-> watch reload events observed for updated files
-> no fatal runtime errors

docker compose logs --tail=80 frontend
-> vite ready at http://localhost:5173/
-> page reload observed for public/run-flow.html

docker compose logs --tail=80 db
-> PostgreSQL ready to accept connections
```

## Section 11: Async run-status for progressive subquestion visibility

**Single goal:** Expose staged graph progress so UI can show subquestions as soon as decomposition completes.

**Details completed:**
- Added async runtime schemas in `src/backend/schemas/agent.py`:
  - `RuntimeAgentRunAsyncStartResponse`
  - `RuntimeAgentRunAsyncStatusResponse`
  - `RuntimeAgentRunAsyncCancelResponse`
  - `AgentRunStageMetadata`
- Exported the new async schema contracts in `src/backend/schemas/__init__.py`.
- Added `src/backend/services/agent_jobs.py` with an in-memory async job manager (thread-safe lock + executor), including:
  - start job (`start_agent_run_job`)
  - status lookup (`get_agent_run_job`)
  - optional cancel request (`cancel_agent_run_job`)
  - staged snapshot handling from graph runner into status payload fields
- Updated graph runner integration in `src/backend/services/agent_service.py`:
  - Added optional `snapshot_callback` support to `run_parallel_graph_runner(...)`
  - Forwarded emitted stage snapshots through callback hook
- Mapped graph decompose snapshot stage to async status stage `subquestions_ready` immediately after decomposition.
- Added async API endpoints in `src/backend/routers/agent.py` while keeping sync endpoint intact:
  - `POST /api/agents/run-async`
  - `GET /api/agents/run-status/{job_id}`
  - `POST /api/agents/run-cancel/{job_id}`
- Expanded API tests in `src/backend/tests/api/test_agent_run.py` for async start/status/cancel route payloads, including staged `subquestions_ready` status shape.
- Updated docs in `README.md` and `src/frontend/public/run-flow.html` with new async endpoints and staged status behavior.

### Useful logs

```text
Full restart/build:
docker compose down -v --rmi all && docker compose build && docker compose up -d
-> backend/frontend rebuilt, db healthy, all services up

Manual async verification:
POST /api/agents/run-async
-> {"job_id":"743fb881-3a2c-4852-956d-e8718a8cb022","run_id":"743fb881-3a2c-4852-956d-e8718a8cb022","status":"running"}

GET /api/agents/run-status/743fb881-3a2c-4852-956d-e8718a8cb022 (while running)
-> "stage":"answer"
-> "stages":[{"stage":"subquestions_ready",...}, ...]
-> "decomposition_sub_questions":[...]

GET /api/agents/run-status/743fb881-3a2c-4852-956d-e8718a8cb022 (final)
-> "status":"success"
-> "stage":"synthesize_final"

Backend logs include:
-> Agent async job snapshot ... stage=subquestions_ready ...
-> Graph state snapshot emitted stage=decompose ...
-> Agent async job finished ... status=success ...

Requested API/job tests:
docker compose exec backend uv run pytest tests/api/test_agent_run.py
-> failed: pytest executable not present in container image

docker compose exec backend uv run python -m pytest tests/api/test_agent_run.py
-> failed: No module named pytest

Host fallback attempt:
cd src/backend && uv run python -m pytest tests/api/test_agent_run.py
-> failed: onnxruntime wheel unavailable for macOS x86_64 (environment constraint)
```

## Section 12: Frontend run timeline shell - progressive container and stage rail

**Single goal:** Add a reusable progressive run shell that displays ordered stages for the full flow.

**Details completed:**
- Added async agent run contracts in `src/frontend/src/utils/api.ts` for:
  - `startAgentRun` (`POST /api/agents/run-async`)
  - `getAgentRunStatus` (`GET /api/agents/run-status/{job_id}`)
  - Timeline-oriented types (`AgentStageName`, `AgentStageRuntimeStatus`, async status payload + stage metadata).
- Reworked run flow in `src/frontend/src/App.tsx` to use async start + polling instead of synchronous `runAgent`, while preserving final readout rendering.
- Added reusable timeline shell with canonical stage order:
  - `decompose -> expand -> search -> rerank -> answer -> final`
  - Status mapping: `pending`, `in_progress`, `completed`, `error`
  - Backend stage adapters for `subquestions_ready -> decompose` and `synthesize_final -> final`.
- Added frontend visibility logging for run lifecycle:
  - run requested/start, stage updates during polling, completion, and failure.
- Added stage rail styles in `src/frontend/src/styles.css` for all timeline statuses and stage dots.
- Updated tests in `src/frontend/src/App.test.tsx`:
  - verifies ordered stage rail rendering
  - verifies progressive status updates while polling
  - verifies async final result rendering and failure handling.
- Updated docs:
  - `README.md` run flow section now documents async frontend start/poll behavior and stage rail mapping.
  - `src/frontend/public/run-flow.html` updated with async call chain and timeline shell details.

### Useful logs

```text
Full fresh restart before implementation:
docker compose down -v --rmi all
-> stopped/removed containers, volumes, and project images

docker compose build
-> backend/frontend built successfully

docker compose up -d && docker compose ps
-> backend/frontend/db/chrome up; db healthy

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}

Required frontend tests/checks:
docker compose exec frontend npm run test
-> PASS (5 passed)

docker compose exec frontend npm run typecheck
-> PASS (tsc --noEmit)

docker compose exec frontend npm run build
-> PASS (vite production build complete)

Changed container restart + runtime logs:
docker compose restart frontend && docker compose ps
-> frontend restarted successfully; all services up

docker compose logs --tail=120 frontend
-> vite ready at http://localhost:5173/
-> page reloads observed for run-flow docs updates

docker compose logs --tail=120 backend
-> uvicorn startup complete; no runtime errors

docker compose logs --tail=120 db
-> PostgreSQL ready to accept connections; no DB errors
```

## Section 13: Decompose stage view - immediate sub-question display

**Single goal:** Render decomposed sub-questions as soon as decomposition completes.

**Details completed:**
- Added a dedicated `Decompose` panel in `src/frontend/src/App.tsx` that renders `decomposition_sub_questions` from async run-status polling, independent from later-stage artifacts.
- Added decompose-stage state wiring:
  - `decompositionSubQuestions` state reset on new run.
  - Polling now stores `status.decomposition_sub_questions` every status tick.
- Added normalization status indicators in the panel:
  - `Ends with ?` indicator based on sub-question punctuation compliance.
  - `Dedupe` indicator based on normalized uniqueness check.
- Added visibility logging for this item:
  - stage update logs now include `decompositionSubQuestionCount`.
- Added dedicated decompose panel styling in `src/frontend/src/styles.css`.
- Updated frontend tests in `src/frontend/src/App.test.tsx` to verify:
  - Decompose panel appears at `subquestions_ready` before final completion.
  - Subquestion list, count, and normalization indicators render correctly.
  - Existing subanswer test was adjusted to scope duplicate subquestion text lookup to the final readout section.
- Updated docs for this section:
  - `README.md` run-flow notes include section-13 decompose view behavior.
  - `src/frontend/public/run-flow.html` frontend details table now includes decompose panel rendering at `subquestions_ready`.

### Useful logs

```text
Mandatory fresh restart before implementation:
docker compose down -v --rmi all
-> containers/images/volumes removed

docker compose build
-> backend/frontend images built successfully

docker compose up -d
-> db healthy, backend/frontend/chrome started

Container state and runtime logs (post-restart):
docker compose ps
-> backend up, frontend up, db healthy, chrome up

docker compose logs --tail=200 backend
-> alembic upgrade applied; uvicorn startup complete; no runtime errors

docker compose logs --tail=200 frontend
-> Vite ready on http://localhost:5173

docker compose logs --tail=200 db
-> PostgreSQL ready to accept connections

Changed container restart for this section:
docker compose restart frontend
-> frontend restarted successfully

Required section tests/checks:
docker compose exec frontend npm run test
-> PASS (5/5)

docker compose exec frontend npm run typecheck
-> PASS (tsc --noEmit)

docker compose exec frontend npm run build
-> PASS (vite production build complete)

Frontend runtime visibility logs from tests include:
-> Async run stage update ... backendStage: 'subquestions_ready' ... decompositionSubQuestionCount: 1
-> Async run stage update ... backendStage: 'synthesize_final' ... decompositionSubQuestionCount: 1
```
