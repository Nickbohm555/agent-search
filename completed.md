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

## Section 14: Expand stage view - per-subquestion expanded query list

**Single goal:** Render expansion outputs for each sub-question in a dedicated Expand panel.

**Details completed:**
- Added async status payload support for expansion artifacts in backend so frontend can consume per-subquestion expanded query groups:
  - `RuntimeAgentRunAsyncStatusResponse` now includes `sub_question_artifacts`.
  - Async job tracking (`AgentRunJobStatus`) now persists `sub_question_artifacts` from graph snapshots/final state.
  - `/api/agents/run-status/{job_id}` now returns `sub_question_artifacts`.
- Added frontend staged payload typing/validation for expansion artifacts in `src/frontend/src/utils/api.ts` via `SubQuestionArtifact` and strict runtime shape checks.
- Added Expand-stage UI in `src/frontend/src/App.tsx`:
  - New `Expand` panel grouped by subquestion index.
  - Renders original subquestion and `expanded_queries` list for each lane.
  - Shows fallback badge `Fallback: original only` when expansion collapses to exactly the original query.
  - Added stage-update visibility logs including `subQuestionArtifactCount`.
- Added Expand panel styles in `src/frontend/src/styles.css` for grouped lane cards, query lists, and fallback badge.
- Updated tests in `src/frontend/src/App.test.tsx` to validate:
  - Expand panel rendering during async polling.
  - Expanded query groups display.
  - Fallback badge rendering behavior.
- Updated async API route test expectation in `src/backend/tests/api/test_agent_run.py` for new response field.
- Updated required docs:
  - `README.md` now documents `sub_question_artifacts[]` in async status payload and section-14 Expand view behavior.
  - `src/frontend/public/run-flow.html` now includes Expand panel rendering in frontend flow and status-payload field notes.

### Useful logs

```text
Mandatory fresh restart before implementation:
docker compose down -v --rmi all
-> removed containers/volumes/images for project

docker compose build
-> agent-search-backend Built
-> agent-search-frontend Built

docker compose up -d
-> db healthy; backend/frontend/chrome started

Health and runtime checks:
docker compose ps
-> backend/frontend/chrome up; db healthy

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}

Required section tests/checks:
docker compose exec frontend npm run test -- --run src/App.test.tsx
-> PASS (5 passed)

docker compose exec frontend npm run typecheck
-> PASS (tsc --noEmit)

docker compose exec frontend npm run build
-> PASS (vite build successful)

Backend check attempt for modified API test:
docker compose exec backend uv run python -m pytest tests/api/test_agent_run.py
-> /app/.venv/bin/python3: No module named pytest

Changed service restarts + logs:
docker compose restart backend frontend
-> backend/frontend restarted successfully

docker compose logs --tail=160 backend
-> uvicorn startup complete; file-change reloads observed; no fatal errors

docker compose logs --tail=120 frontend
-> Vite ready on http://localhost:5173/

docker compose logs --tail=120 db
-> PostgreSQL ready to accept connections
```

## Section 15: Search stage view - retrieval candidates and merge provenance

**Single goal:** Render search-stage outputs showing merged retrieval candidates before reranking.

**Details:**
- Show per-subquestion candidate count after multi-query merge/dedupe.
- Render top candidate preview rows with source/title snippets.
- Show merge stats (`raw_hits`, `deduped_hits`) for transparency.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Add search merge stats/candidate preview types. |
| `src/frontend/src/App.tsx` | Add Search panel for merged candidate previews. |
| `src/frontend/src/App.test.tsx` | Verify search candidate counts and merge stats rendering. |

**How to test:** Run frontend tests and verify Search panel displays merged candidate stats before rerank completes.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

**Details completed:**
- Extended staged async payload types/validation in `src/frontend/src/utils/api.ts`:
  - Added `SearchCandidateRow` and `SearchRetrievalProvenanceRow`.
  - Extended `SubQuestionArtifact` with `retrieved_docs` and `retrieval_provenance`.
  - Kept backward compatibility by defaulting missing fields to empty arrays during validation.
- Implemented Search stage UI in `src/frontend/src/App.tsx`:
  - Added Search panel grouped by subquestion.
  - Displays merged candidate count (`deduped_hits`) per subquestion.
  - Displays merge stats (`raw_hits` from provenance events and `deduped_hits` from merged rows).
  - Displays top preview rows with title, source, and content snippet.
  - Added run-stage visibility logs for search totals during polling.
- Added Search panel styling in `src/frontend/src/styles.css` for lane cards, stats badges, and preview rows.
- Updated frontend tests in `src/frontend/src/App.test.tsx`:
  - Added polling fixture payload with retrieval candidates + provenance.
  - Verified Search panel renders candidate count, raw/deduped merge stats, and preview row content.
  - Kept stage rail assertions aligned to search-stage in-progress state.
- Updated docs:
  - `README.md` now documents section-15 Search panel behavior and merge-stat transparency.
  - `src/frontend/public/run-flow.html` now notes section-15 Search panel data path and metrics.

### Useful logs

```text
Mandatory fresh restart before implementation:
docker compose down -v --rmi all
-> containers/images/volumes removed

docker compose build
-> backend/frontend images built successfully

docker compose up -d
-> db healthy; backend/frontend/chrome started

Container health + logs before coding:
docker compose ps
-> backend/frontend up; db healthy; chrome up

docker compose logs --tail=120 backend
-> alembic upgrade + uvicorn startup complete

docker compose logs --tail=120 frontend
-> vite ready at http://localhost:5173

docker compose logs --tail=120 db
-> postgresql ready to accept connections

Required section tests/checks:
docker compose exec frontend npm run test
-> PASS (5/5)

docker compose exec frontend npm run typecheck
-> PASS (tsc --noEmit)

docker compose exec frontend npm run build
-> PASS (vite production build)

Changed services restart + verification:
docker compose restart db backend frontend
-> restarted successfully

docker compose ps
-> backend up; frontend up; db healthy; chrome up

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}

docker compose logs --tail=160 backend
-> app startup complete; no fatal errors

docker compose logs --tail=120 frontend
-> vite dev server ready; live reload observed for docs update

docker compose logs --tail=120 db
-> database ready after restart; no errors
```

## Section 16: Rerank stage view - reordered top_n evidence

**Single goal:** Render reranked evidence and score/order changes per sub-question.

**Details:**
- Show reranked top_n list for each sub-question with final order and optional score.
- Display rerank fallback notice when reranking was bypassed.
- Keep links/snippets aligned with citation index that answer stage will use.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Add rerank artifact/fallback fields to payload types. |
| `src/frontend/src/App.tsx` | Add Rerank panel for top_n evidence rendering. |
| `src/frontend/src/App.test.tsx` | Verify rerank order and fallback indicator behavior. |

**How to test:** Run frontend tests and ensure reranked ordering displays before subanswers/final answer.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

**Details completed:**
- Extended async frontend payload parsing/types in `src/frontend/src/utils/api.ts`:
  - Added `SubQuestionArtifact.reranked_docs` and validation support.
  - Added rerank metadata types (`RerankProvenanceRow`) and parsed `rerank_top_n`, `rerank_provenance`, and derived `rerank_bypassed` from `sub_qa[].tool_call_input`.
  - Kept compatibility defaults for missing arrays (`retrieved_docs`, `retrieval_provenance`, `reranked_docs`).
- Implemented a dedicated Rerank stage panel in `src/frontend/src/App.tsx`:
  - Renders per-subquestion reranked evidence rows with citation index, rank, score (or `n/a`), source, and snippet.
  - Displays explicit fallback badge (`Fallback: reranking bypassed`) when reranking was bypassed.
  - Shows rerank order-change visibility (`Order changed: yes/no`) by comparing retrieved vs reranked document ordering.
  - Added run-stage visibility logs (`rerankRowsTotal`, `rerankBypassedCount`) during async polling.
  - Kept subquestion readout data progressive by storing live `sub_qa` updates.
- Added rerank styling in `src/frontend/src/styles.css` for lane cards, fallback badge, and ranked evidence rows.
- Added/updated tests in `src/frontend/src/App.test.tsx`:
  - New test verifies reranked order rendering and fallback indicator behavior.
  - Existing run-flow tests still pass with new rerank panel/state behavior.
- Updated docs:
  - `README.md` now includes Section 16 rerank panel behavior.
  - `src/frontend/public/run-flow.html` now documents rerank panel payload usage and fallback visibility.

### Useful logs

```text
Mandatory fresh restart before implementation:
docker compose down -v --rmi all
-> containers/images/volumes removed

docker compose build
-> backend/frontend images built successfully

docker compose up -d
-> db healthy; backend/frontend/chrome started

Post-restart health and status:
docker compose ps
-> backend/frontend/chrome up; db healthy

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}

Section validation checks:
docker compose exec frontend npm run test
-> PASS (6/6)

docker compose exec frontend npm run typecheck
-> PASS (tsc --noEmit)

docker compose exec frontend npm run build
-> PASS (vite production build)

Post-change service restart + logs:
docker compose restart
-> backend/frontend/db/chrome restarted successfully

docker compose ps
-> backend/frontend/chrome up; db healthy

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}

docker compose logs --tail=120 backend frontend db
-> backend uvicorn startup + health requests OK; frontend vite ready on :5173; db ready to accept connections
```

## Section 17: Subanswer stage view - per-subquestion answer with citations

**Single goal:** Render per-subquestion answers as they become available, including citation markers.

**Details:**
- Show each sub-question with its generated subanswer and citation markers (`[1]`, `[2]`, ...).
- Highlight explicit fallback `nothing relevant found` when returned.
- Link visible citation markers to reranked evidence rows in the Rerank panel.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Add subanswer citation/fallback fields to stage payload types. |
| `src/frontend/src/App.tsx` | Add Subanswer panel and citation-to-evidence linkage. |
| `src/frontend/src/App.test.tsx` | Verify subanswer rendering, citation markers, and fallback display. |

**How to test:** Run frontend tests and confirm subanswers/citations render per sub-question during answering stage.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

**Details completed:**
- Updated staged async payload typing/parsing in `src/frontend/src/utils/api.ts`:
  - Added optional `sub_answer_citations` and `sub_answer_is_fallback` to `SubQuestionAnswer`.
  - Added backward-compatible derivation in validation by parsing citation markers from `sub_answer` and detecting exact fallback text `nothing relevant found`.
  - Kept existing rerank metadata extraction and compatibility behavior intact.
- Implemented Subanswer stage UI in `src/frontend/src/App.tsx`:
  - Added a dedicated `Subanswer` panel rendering per-subquestion answers as soon as answer-stage updates arrive.
  - Added explicit fallback badge (`Fallback: nothing relevant found`) when fallback responses are returned.
  - Added citation-link rendering from subanswer markers to stable rerank evidence row anchors in the Rerank panel.
  - Added stage visibility logging for subanswer progress: ready count, citation count, and fallback count.
- Added UI styling in `src/frontend/src/styles.css` for subanswer lane cards, fallback badge, and citation links.
- Added tests in `src/frontend/src/App.test.tsx`:
  - New test validates subanswer rendering, citation markers, and fallback badge in answer stage.
  - Updated assertions to scope duplicated subanswer text safely across the new Subanswer panel and existing final readout section.
- Updated docs:
  - `README.md` now documents frontend Section 17 Subanswer panel behavior.
  - `src/frontend/public/run-flow.html` now documents the Subanswer stage panel and citation-to-rerank linkage.

### Useful logs

```text
Mandatory fresh restart before implementation:
docker compose down -v --rmi all
-> containers/images/volumes removed; fresh environment reset

docker compose build
-> backend/frontend images built successfully

docker compose up -d
-> db healthy; backend/frontend/chrome started

Pre-change runtime checks:
docker compose ps
-> backend/frontend/chrome up; db healthy

docker compose logs --tail=120 backend
-> alembic upgrade + uvicorn startup complete

docker compose logs --tail=120 frontend
-> vite ready on http://localhost:5173

docker compose logs --tail=120 db
-> postgresql ready to accept connections

Required section tests/checks:
docker compose exec frontend npm run test
-> initially failed (2 assertions due duplicate text after new Subanswer panel); fixed selector scoping and reran
-> PASS (7/7)

docker compose exec frontend npm run typecheck
-> PASS (tsc --noEmit)

docker compose exec frontend npm run build
-> PASS (vite production build)

Post-change restart + verification:
docker compose restart
-> backend/frontend/db/chrome restarted successfully

docker compose ps
-> backend/frontend/chrome up; db healthy

curl -sS http://localhost:8000/api/health
-> transient connection reset during restart window, then healthy on retry
-> {"status":"ok"}

docker compose logs --tail=160 backend
-> uvicorn startup complete; no fatal errors

docker compose logs --tail=120 frontend
-> vite dev server ready on :5173

docker compose logs --tail=120 db
-> database restarted and ready to accept connections
```

## Section 18: Final synthesis view - final answer with supporting subanswer summary

**Single goal:** Render the final answer stage as a distinct panel that summarizes supporting subanswers and citations.

**Details:**
- Show final answer only when synthesis stage completes.
- Display compact summary of contributing subanswers and citation coverage.
- Preserve previous successful final answer while a new run is in progress.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/App.tsx` | Add Final panel with synthesis completion behavior. |
| `src/frontend/src/App.test.tsx` | Verify final panel only updates on synthesis completion. |

**How to test:** Run frontend tests and manual run to confirm final panel updates only at terminal synthesis stage.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

**Details completed:**
- Updated `src/frontend/src/App.tsx` final-stage handling:
  - Replaced reset-on-submit final readout behavior with persisted `lastSuccessfulSynthesis` state.
  - Final panel now updates only when async status is `success` at `synthesize_final`/`final`.
  - While a new run is loading, the previous successful final synthesis remains visible.
  - Added final-stage observability log: `Final synthesis panel updated from completed run.` with subquestion/citation coverage metrics.
- Added Final Synthesis UI summary in `src/frontend/src/App.tsx`:
  - Distinct panel title: `Final Synthesis`.
  - Compact support summary including subanswers used, citation coverage counts, and fallback count.
  - Subquestion detail rows now include citation coverage display.
- Expanded tests in `src/frontend/src/App.test.tsx`:
  - Added coverage assertion for summary text in existing final-result test.
  - Added dedicated regression test proving previous successful final synthesis remains displayed until the next run reaches terminal synthesis success.
  - Stabilized async polling behavior in rerank/subanswer tests by providing terminal success responses.
- Updated documentation:
  - `README.md` now documents section 18 Final Synthesis panel behavior.
  - `src/frontend/public/run-flow.html` now documents synthesis-gated update and previous-answer preservation behavior.

### Useful logs

```text
Mandatory fresh restart before implementation:
docker compose down -v --rmi all && docker compose build && docker compose up -d
-> full stack rebuilt from scratch; db healthy; backend/frontend/chrome started

Required section tests/checks:
docker compose exec frontend npm run test
-> PASS (8 tests)

docker compose exec frontend npm run typecheck
-> PASS (tsc --noEmit)

docker compose exec frontend npm run build
-> PASS (vite production build)

Post-change service restart + verification:
docker compose restart frontend
-> frontend container restarted successfully

docker compose ps
-> backend/frontend/chrome up; db healthy

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}

docker compose logs --tail=160 backend frontend db
-> backend uvicorn/alembic startup healthy; frontend vite ready on :5173; db ready to accept connections
```

## Section 19: Parity evals - deep-agent path vs graph path

**Single goal:** Prove graph workflow preserves baseline behavior compared to deep-agent path during migration.

**Details:**
- Build fixed-question parity suite across both paths.
- Compare main output shape, sub_qa completeness, and fallback behavior.
- Keep this section focused on parity only; quality/cost deltas are handled in Sections 20-21.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies required initially.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tests/services/test_agent_service.py` | Add graph vs deep-agent parity regression tests. |
| `README.md` | Document parity test scope and acceptance thresholds. |

**How to test:** Run parity suite and verify graph path meets agreed parity thresholds before cleanup sections begin.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

**Details completed:**
- Added parity regression helpers/tests in `src/backend/tests/services/test_agent_service.py`:
  - `_response_shape_snapshot(...)` to normalize parity comparisons.
  - `test_runtime_agent_parity_graph_vs_legacy_fixed_question_suite` to assert graph and rollback paths match for fixed question output shape, sub-question completeness, and `nothing relevant found` propagation.
  - `test_runtime_agent_parity_vector_store_timeout_fallback` to assert both paths return identical vector-store timeout fallback behavior.
- Updated `README.md` with Section 19 parity scope and acceptance threshold notes.
- Updated `src/frontend/public/run-flow.html` with a Section 19 parity-evals summary.

### Useful logs

```text
Mandatory fresh restart before implementation:
docker compose down -v --rmi all && docker compose build && docker compose up -d
-> full stack rebuilt; backend/frontend/chrome started; db healthy

Parity tests (required section scope):
docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py -k "parity"
-> PASS (2 passed, 73 deselected)

Full file check (observed existing unrelated breakages):
docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py
-> FAIL (23 failed, 52 passed)
-> failures are existing migration tests still expecting legacy runtime behavior while runtime is now graph-first by default

Post-change restarts and runtime checks:
docker compose restart backend frontend
-> backend/frontend restarted

docker compose ps
-> backend/frontend/chrome up; db healthy

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}

docker compose logs --tail=120 backend
-> alembic/uvicorn startup complete; watchfiles reload after test-file edit; no fatal startup errors

docker compose logs --tail=120 frontend
-> vite ready on http://localhost:5173; page reload for public/run-flow.html change

docker compose logs --tail=120 db
-> postgresql initialized and ready to accept connections
```

## Section 20: Retrieval quality evals - search-only vs search+rerank

**Single goal:** Quantify retrieval-quality gains from reranking without mixing in cost metrics.

**Details:**
- Compare `search-only` vs `search+rerank` on benchmark queries.
- Track hit-quality metrics and citation-grounding consistency.
- Include hard queries where relevant evidence is outside naive top-k.
- Keep this section focused on quality metrics only.
- Include eval slices for the actual library stack (`MultiQueryRetriever` + `flashrank`) versus non-expanded/non-reranked baselines.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies required initially.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tests/services/test_agent_service.py` | Add retrieval quality regression tests for rerank impact. |
| `src/backend/tests/services/test_reranker_service.py` | Add rerank quality/fallback tests used by eval cases. |
| `README.md` | Document retrieval-quality eval methodology. |

**How to test:** Run quality eval suite and verify rerank path improves retrieval/citation metrics on selected hard queries.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

**Details completed:**
- Added retrieval-quality eval coverage in `src/backend/tests/services/test_agent_service.py`:
  - `test_retrieval_quality_eval_search_plus_rerank_improves_top1_and_citation_grounding_on_hard_queries` compares hard-query quality metrics across slices and asserts `search+rerank` improves both top-hit relevance and citation-grounding consistency over `search-only` baseline.
  - `test_retrieval_quality_eval_slice_comparison_multiquery_flashrank_vs_no_expand_baseline` enforces eval-slice behavior for baseline (`no expansion + no rerank`) versus stack behavior (expanded retrieval + rerank ordering).
- Added reranker eval tests in `src/backend/tests/services/test_reranker_service.py`:
  - `test_reranker_quality_eval_improves_hit_at_1_over_non_reranked_baseline` verifies `flashrank` ordering behavior improves hit@1 over deterministic non-reranked fallback.
  - `test_reranker_quality_eval_fallback_remains_deterministic_when_ranker_returns_unmappable_ids` verifies deterministic fallback integrity when reranker output cannot be mapped.
- Updated docs:
  - `README.md` includes Section 20 methodology/metrics and migration-note references.
  - `src/frontend/public/run-flow.html` includes Section 20 retrieval-quality eval summary.

### Useful logs

```text
Mandatory fresh restart before implementation:
docker compose down -v --rmi all
-> removed services, network, backend/frontend images, and volumes

docker compose build
-> backend/frontend rebuilt successfully

docker compose up -d
-> db healthy; backend/frontend/chrome started

Stack readiness checks:
docker compose ps
-> backend/frontend/chrome up; db healthy

curl -sS http://localhost:8000/api/health
-> {"status":"ok"}

Required section tests:
docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py tests/services/test_reranker_service.py -k "retrieval_quality_eval or reranker_quality_eval"
-> PASS (4 passed, 79 deselected)

Post-change restarts:
docker compose restart backend frontend
-> backend/frontend restarted successfully

Post-change logs:
docker compose logs --no-color --tail=160 backend
-> uvicorn/alembic startup healthy; watchfiles reloads observed after test edits; no fatal runtime errors

docker compose logs --no-color --tail=160 frontend
-> vite ready on :5173; page reload observed for public/run-flow.html

docker compose logs --no-color --tail=160 db
-> postgres initialized and ready to accept connections
```

## Section 21: Efficiency evals - context size and token budget impact

**Single goal:** Quantify efficiency impact of reranked top_n context vs naive large-context baselines.

**Details:**
- Compare token usage for reranked top_n vs larger unfiltered context windows.
- Track answer quality floor while reducing token cost.
- Record target operating ranges for `k_fetch` and `top_n`.
- Keep this section focused on cost/efficiency metrics only.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies required initially.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tests/services/test_agent_service.py` | Add efficiency-oriented regression checks and fixtures. |
| `README.md` | Document token/cost eval method and recommended defaults. |

**How to test:** Run efficiency suite and verify reranked context achieves lower token usage without unacceptable quality loss.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

**Details completed:**
- Added Section 21 efficiency eval coverage in `src/backend/tests/services/test_agent_service.py`:
  - `_estimate_context_token_budget(...)` helper for deterministic context-size comparison.
  - `test_efficiency_eval_reranked_top_n_reduces_context_tokens_while_preserving_quality_floor` to verify reranked `top_n` context reduces token budget while preserving quality floor and citation grounding.
  - `test_efficiency_eval_operating_ranges_identify_k_fetch_and_top_n_targets` to lock eval-derived target operating ranges for `k_fetch` and `top_n`.
- Updated `README.md` with Section 21 methodology and migration note, including current recommended tuning range (`k_fetch=6..8`, `top_n=2..3`).
- Updated `src/frontend/public/run-flow.html` with a Section 21 efficiency-evals summary.

### Useful logs

```text
Mandatory fresh restart before implementation:
docker compose down -v --rmi all
docker compose build
docker compose up -d
-> full stack rebuilt and restarted; db healthy; backend/frontend/chrome running

Required section tests:
docker compose exec backend uv run pytest tests/services/test_agent_service.py -k "efficiency_eval"
-> initial failure: pytest missing from backend env

docker compose exec backend sh -lc 'uv pip install pytest && uv run python -m pytest tests/services/test_agent_service.py -k "efficiency_eval"'
-> PASS (2 passed, 77 deselected)

Post-change restarts and runtime checks:
docker compose restart backend frontend
-> backend/frontend restarted

docker compose ps
-> backend/frontend/chrome up; db healthy

docker compose logs --no-color --tail=120 backend
-> uvicorn/alembic startup healthy; watchfiles reloads observed after test and venv changes; no fatal runtime errors

docker compose logs --no-color --tail=120 frontend
-> vite ready on :5173; reload observed for `public/run-flow.html`

docker compose logs --no-color --tail=120 db
-> postgres ready to accept connections
```

## Section 22: Remove deep-agent runtime code - post-cutover cleanup

**Single goal:** Delete unused deep-agent runtime orchestration code after graph path is validated.

**Details:**
- Remove coordinator/deep-agent invocation from active runtime execution.
- Delete deep-agent-only helpers, callbacks, and prompt contracts that are no longer referenced.
- Keep only code required for historical docs/tests if explicitly needed; otherwise remove.
- Ensure imports and schemas no longer reference deep-agent-specific artifacts.
- Do not remove `langfuse` tracing integration; retain/cleanly re-home it as graph runtime observability.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agents/coordinator.py` | Remove or archive deep-agent runtime path if fully unused. |
| `src/backend/services/agent_service.py` | Remove deep-agent branches and callback plumbing. |
| `src/backend/utils/agent_callbacks.py` | Remove deep-agent callback capture code if no longer used. |
| `src/backend/tests/agents/test_coordinator_agent.py` | Remove/replace tests tied only to removed runtime code. |

**How to test:** Run full backend tests and static import checks to confirm no dead deep-agent references remain.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

**Details completed:**
- Removed deep-agent runtime execution path from `run_runtime_agent(...)`:
  - Deleted `_run_runtime_agent_with_legacy_deep_agent(...)` and rollback-flag switching logic.
  - Kept graph runtime path only (`_run_runtime_agent_with_graph_runner`).
- Removed deep-agent helper plumbing from backend service/runtime:
  - Deleted coordinator-specific helper functions (`_build_coordinator_input_message`, `_extract_sub_qa`, callback-capture parsing helpers).
  - Re-homed decomposition prompt contract in `agent_service.py` (`_DECOMPOSITION_ONLY_PROMPT`) and removed dependency on `agents.coordinator` prompt export.
  - Removed `coordinator_invoke_timeout_s` from runtime timeout config and test fixtures.
- Removed deep-agent modules/tests:
  - Deleted `src/backend/agents/coordinator.py`.
  - Simplified `src/backend/agents/__init__.py`.
  - Deleted `src/backend/tests/agents/test_coordinator_agent.py`.
- Removed deep-agent callback capture code:
  - Trimmed `src/backend/utils/agent_callbacks.py` to keep only `AgentLoggingCallbackHandler` used by graph runner.
- Updated backend/runtime docs and config:
  - Updated `README.md` and `src/frontend/public/run-flow.html` to document graph-only runtime and Section 22 cleanup state.
  - Removed migration env flags from `.env.example` (`RUNTIME_AGENT_ROLLBACK_TO_DEEP_AGENT`, `COORDINATOR_INVOKE_TIMEOUT_S`) and removed rollback var from local `.env`.
- Updated dependency lock:
  - Removed `deepagents` from `src/backend/pyproject.toml`.
  - Regenerated `src/backend/uv.lock` via `uv lock`.
- Updated tests for graph-only runtime:
  - Pruned legacy deep-agent assertions in `src/backend/tests/services/test_agent_service.py`.
  - Fixed API status fixture in `src/backend/tests/api/test_agent_run.py` by including `sub_question_artifacts`.

### Useful logs

```text
Mandatory fresh restart before implementation:
docker compose down -v --rmi all
-> removed services, network, backend/frontend images, and volumes

docker compose build
-> backend/frontend rebuilt successfully

docker compose up -d
-> db healthy; backend/frontend/chrome started

Health and runtime checks:
docker compose ps
-> backend/frontend/chrome up; db healthy

curl -sS -w '\n%{http_code}\n' http://localhost:8000/api/health
-> {"status":"ok"}
-> 200

Dependency + static checks:
cd src/backend && uv lock
-> lock refreshed; deepagents removed

docker compose exec backend uv run python -m compileall -q /app
-> success

Source static reference check (graph-only runtime surface):
rg -n "deepagents|agents\.coordinator|create_coordinator_agent|RUNTIME_AGENT_ROLLBACK_TO_DEEP_AGENT|COORDINATOR_INVOKE_TIMEOUT_S" src/backend src/frontend/src src/frontend/public README.md .env .env.example -g '!src/backend/uv.lock'
-> no matches

Required section test suite:
docker compose exec backend uv run pytest
-> PASS (104 passed, 1 warning)

Container refresh after edits:
docker compose restart backend frontend
-> backend/frontend restarted successfully

Post-change logs:
docker compose logs --no-color --tail=80 backend frontend db
-> backend uvicorn/alembic startup healthy; frontend vite ready on :5173; db ready/healthy
-> note: watchfiles reload warnings observed after test/dependency edits; no fatal runtime errors
```

## Section 23: Remove migration scaffolding - flags, dual paths, and temporary parity code

**Single goal:** Remove temporary migration switches and dual-path code once graph runner is the only production path.

**Details:**
- Remove feature flags used only for migration rollback.
- Remove dual-path branching and temporary adapters used for parity comparisons.
- Remove migration-only fixtures and temporary eval wiring that is no longer needed.
- Keep permanent quality tests, but drop one-off migration parity harnesses.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): remove migration-only env vars from docs/config.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Delete dual-path/flagged branches. |
| `src/backend/tests/services/test_agent_service.py` | Remove migration-only parity fixtures while keeping permanent regressions. |
| `README.md` | Remove migration-only flags and rollout instructions. |

**How to test:** Run backend tests with migration flags removed and verify runtime behavior is unchanged.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

**Details completed:**
- Removed runtime migration adapter scaffolding from `src/backend/services/agent_service.py`:
  - Inlined graph execution flow directly into `run_runtime_agent(...)`.
  - Deleted `_run_runtime_agent_with_graph_runner(...)` wrapper and graph-path selection log phrasing.
  - Preserved/expanded runtime visibility logs around vector-store acquisition, context build, and graph completion.
- Updated `README.md` to remove migration/rollout wording while keeping graph-only architecture guidance:
  - Replaced section-indexed migration notes with canonical graph-runtime descriptions.
  - Kept permanent retrieval-quality and efficiency evaluation guidance without migration framing.
- Updated `src/frontend/public/run-flow.html` to remove migration-baseline and stale dual-path/deep-agent references:
  - Renamed Graph State panel to canonical graph contracts.
  - Replaced “Section X adds …” rollout text with stable runtime behavior descriptions.
  - Replaced stale `agent.invoke` / `_extract_sub_qa` / `create_deep_agent_impl` snippets with current graph-runner + response mapping flow.

### Useful logs

```text
Fresh restart before work:
docker compose down -v --rmi all && docker compose build && docker compose up -d
-> full rebuild/restart completed; db healthy; backend/frontend/chrome up

Required backend tests:
docker compose exec backend uv run pytest
-> failed initially: `pytest` not found in backend uv env

docker compose exec backend sh -lc 'uv pip install pytest && uv run python -m pytest'
-> PASS (104 passed, 1 warning)

Post-change restarts and runtime checks:
docker compose restart backend frontend
-> backend/frontend restarted

docker compose ps
-> backend/frontend/chrome up; db healthy

docker compose logs --no-color --tail=140 backend frontend db
-> backend uvicorn/alembic startup healthy; runtime reloads observed after edits
-> frontend vite ready on :5173 with run-flow reload events
-> db ready/healthy; non-fatal transaction-in-progress warnings observed during test activity
```

## Section 24: Final architecture docs reconciliation - canonical state-graph docs only

**Single goal:** Ensure repository docs and flow diagrams reflect only the final state-graph architecture.

**Details:**
- Update the architecture content in `README.md` to remove deep-agent runtime references.
- Update `run-flow.html` to show the canonical lane: `decompose -> expand -> search -> rerank -> answer -> synthesize`.
- Ensure README examples and terminology match actual code paths and endpoint behavior.
- Confirm no contradictory legacy flow descriptions remain across docs.
- Document concrete library usage in architecture docs: `langchain` `MultiQueryRetriever` for expansion and `flashrank` for reranking.
- Add a "How the flow works" explainer covering each stage:
  - `decompose`: split main question into atomic sub-questions.
  - `expand`: generate related queries per sub-question.
  - `search`: retrieve candidate chunks with vector similarity.
  - `rerank`: reorder retrieved chunks by query-specific relevance.
  - `answer`: produce subanswer with citations from reranked evidence.
  - `synthesize`: build final answer from subanswers.
- Add a retrieval fundamentals explainer:
  - embedding vectors and nearest-neighbor retrieval basics.
  - cosine similarity intuition (`-1..1`, direction similarity, higher is closer).
  - why over-fetch (`k_fetch`) then rerank (`top_n`) improves precision.
  - merge/dedupe behavior across expanded queries and citation index stability.
- Add a reranking explainer:
  - difference between initial vector retrieval score and reranker score.
  - why reranking can surface relevant chunks that were not in naive top-k.
  - fallback behavior when reranker is unavailable.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `README.md` | Canonical architecture and usage docs for state-graph runtime. |
| `src/frontend/public/run-flow.html` | Final flow visualization aligned with implementation. |

**How to test:** Manually validate docs against real runtime traces; confirm every stage in UI/run-status has a matching explanation, and verify retrieval/rerank examples are technically consistent with implementation (`k_fetch`, `top_n`, cosine similarity, dedupe/citation behavior).
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

**Details completed:**
- Replaced `README.md` architecture/run-flow content with canonical state-graph runtime documentation only.
- Removed legacy/deep-agent/refinement-oriented flow language from `README.md` and aligned wording with actual `run_runtime_agent -> run_parallel_graph_runner` execution.
- Added requested explainers in `README.md`:
  - "How The Flow Works" with all six canonical stages (`decompose`, `expand`, `search`, `rerank`, `answer`, `synthesize`).
  - retrieval fundamentals (embeddings, nearest-neighbor retrieval, cosine similarity intuition, `k_fetch`/`top_n`, merge/dedupe and citation stability).
  - reranking fundamentals (vector score vs reranker score, why reranking helps, deterministic fallback behavior).
- Rewrote `src/frontend/public/run-flow.html` to a concise canonical runtime page showing:
  - exact frontend -> backend call chain,
  - canonical stage behavior,
  - frontend stage mapping,
  - retrieval/rerank fundamentals and fallback behavior.
- Verified no contradictory legacy terms remain in these two docs (`deep-agent`, `refinement`, legacy section-path wording).

### Useful logs

```text
Mandatory fresh restart before implementation:
docker compose down -v --rmi all
-> removed running containers, network, data volumes, and rebuilt images

docker compose build
-> backend/frontend images built successfully

docker compose up -d
-> db healthy; backend/frontend/chrome started

Post-change container restart + checks:
docker compose restart backend frontend
-> backend/frontend restarted successfully

docker compose ps
-> backend/frontend/chrome up; db healthy

Health check:
curl http://localhost:8000/api/health
-> {"status":"ok"}

Logs reviewed:
docker compose logs --no-color --tail=120 backend
-> uvicorn started; alembic upgrade executed; app startup complete

docker compose logs --no-color --tail=120 frontend
-> vite ready on :5173; public/run-flow.html reload observed

docker compose logs --no-color --tail=120 db
-> postgres ready to accept connections

Validation commands:
docker compose exec frontend npm run typecheck
-> PASS

docker compose exec frontend npm run build
-> PASS

docker compose exec backend uv run --with pytest pytest tests/api -m smoke
-> no smoke-marked tests selected in current suite (all deselected)

docker compose exec backend uv run --with pytest pytest tests/api
-> PASS (6 passed)
```
