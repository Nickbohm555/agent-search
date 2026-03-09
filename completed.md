## Completed - 2026-03-09 - Section 1

## Section 1: Baseline contract snapshot - runtime behavior guardrail

**Single goal:** Capture current backend runtime response contracts so all refactors and benchmark integration are validated against fixed baselines.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Snapshot sync/async agent-run payload shapes.
- Snapshot current route inventory and response schemas.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): existing backend pytest workflow.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tests/api/test_agent_run.py` | API response-shape baseline assertions. |
| `src/backend/tests/api/test_health.py` | Baseline API sanity guard. |
| `test_completed.md` | Track baseline results and commands. |

**How to test:** Run backend API tests for route/shape stability.

**Test results:** (Add when section is complete.)
- Pending.

---


**Completion notes:**
- Added API route inventory snapshot test and OpenAPI response schema snapshot test.
- Added async completed run-status payload shape baseline (including nested result and elapsed timing).

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d --remove-orphans`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/api"`
- `docker compose restart backend`
- `docker compose logs --tail=120`

**Useful logs (excerpt):**
```text
backend: Uvicorn running on http://0.0.0.0:8000
backend: GET /api/health 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
pytest: 9 passed in 2.04s
```


## Completed - 2026-03-09 - Section 2

## Section 2: Shared contract freeze - SDK + benchmark interfaces

**Single goal:** Freeze public interfaces used by both SDK extraction and benchmark system before implementation diverges.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Lock `agent_search.public_api` sync/async signatures.
- Lock benchmark API schema contracts and core request/response models.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/public_api.py` | Canonical SDK function signatures. |
| `src/backend/schemas/benchmark.py` | Canonical benchmark API model contracts. |
| `src/backend/tests/contracts/test_public_contracts.py` | Contract freeze tests for signatures/schemas. |

**How to test:** Run contract tests and verify no interface drift.

**Test results:** (Add when section is complete.)
- Pending.

---

**Completion notes:**
- Added new SDK boundary package `agent_search` with canonical public API function signatures: `run`, `run_async`, `get_run_status`, `cancel_run`.
- Added benchmark contract schemas in `schemas/benchmark.py` for run create/list/status/cancel payloads plus mode/status enums and targets.
- Added contract freeze tests to pin SDK function signatures/return annotations and benchmark schema field/required sets.
- Updated `schemas/__init__.py` exports to include benchmark contract models.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose restart backend`
- `docker compose exec backend uv run pytest tests/contracts/test_public_contracts.py` (failed: `pytest` missing from env)
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/contracts/test_public_contracts.py"`
- `docker compose ps`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=60 frontend`
- `docker compose logs --tail=60 db`

**Useful logs (excerpt):**
```text
pytest: tests/contracts/test_public_contracts.py ...... [100%]
pytest: 6 passed in 0.06s
backend: Application startup complete.
backend: Uvicorn running on http://0.0.0.0:8000
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 3

## Section 3: SDK public sync API contract - stable callable entrypoint

**Single goal:** Expose primary in-process SDK sync entrypoint requiring `query`, `vector_store`, and `model`.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Enforce required `model` argument.
- Return type compatible with runtime response model.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/__init__.py` | Public SDK import surface. |
| `src/backend/agent_search/public_api.py` | Sync SDK entrypoint. |
| `src/backend/tests/sdk/test_public_api.py` | Signature and return-contract tests. |

**How to test:** Run SDK sync API contract tests.

**Test results:** (Add when section is complete.)
- Pending.

---

**Completion notes:**
- Implemented SDK sync `run` in `agent_search.public_api` by delegating to `services.agent_service.run_runtime_agent` with `RuntimeAgentRunRequest`.
- Added explicit runtime input enforcement for `model` and `vector_store` (`TypeError` when either is `None`).
- Added completion logging for sync SDK run output visibility.
- Added SDK tests in `tests/sdk/test_public_api.py` covering frozen sync signature, delegation/return type contract, and required-model validation behavior.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose ps`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`
- `docker compose exec backend uv run --with pytest pytest tests/sdk/test_public_api.py tests/contracts/test_public_contracts.py`
- `docker compose restart backend`
- `curl -i -sS http://localhost:8000/api/health`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_public_api.py ... [ 33%]
pytest: tests/contracts/test_public_contracts.py ...... [100%]
pytest: 9 passed in 1.49s
backend: Application startup complete.
backend: Uvicorn running on http://0.0.0.0:8000
backend: WatchFiles detected changes in 'agent_search/public_api.py'. Reloading...
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 4

## Section 4: SDK public async API contract - stable lifecycle entrypoint

**Single goal:** Expose SDK async `run_async`, `get_run_status`, and `cancel_run` interfaces.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Keep payload fields aligned with current async runtime shape.
- Keep cancellation/status semantics stable.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/public_api.py` | Async SDK lifecycle functions. |
| `src/backend/tests/sdk/test_public_api_async.py` | Async lifecycle contract tests. |

**How to test:** Run SDK async contract tests.

**Test results:** (Add when section is complete.)
- Pending.

---

**Completion notes:**
- Implemented SDK async lifecycle functions in `agent_search.public_api`: `run_async`, `get_run_status`, and `cancel_run`.
- Reused existing runtime job orchestration in `services.agent_jobs` to keep SDK lifecycle behavior aligned with API runtime semantics.
- Added runtime visibility logs for async queue, status resolution, and cancel acceptance/failure paths.
- Added `tests/sdk/test_public_api_async.py` to lock async SDK signature, start payload shape, status payload timing/result shape, and missing/uncancellable job error semantics.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose ps`
- `docker compose logs --tail=120 backend frontend db`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/sdk/test_public_api_async.py tests/contracts/test_public_contracts.py"`
- `docker compose restart backend`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --tail=140 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_public_api_async.py ...... [ 50%]
pytest: tests/contracts/test_public_contracts.py ...... [100%]
pytest: 12 passed in 1.56s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 5

## Section 5: SDK error taxonomy - explicit consumer-facing exceptions

**Single goal:** Add deterministic SDK exception types.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Define configuration, retrieval, model, and timeout exceptions.
- Map internal errors to public SDK exception hierarchy.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/errors.py` | SDK exception hierarchy. |
| `src/backend/agent_search/public_api.py` | Boundary exception mapping. |
| `src/backend/tests/sdk/test_errors.py` | Exception contract tests. |

**How to test:** Run SDK error-path tests.

**Test results:** (Add when section is complete.)
- Pending.

---

**Completion notes:**
- Added public SDK exception taxonomy in `agent_search.errors`: `SDKError`, `SDKConfigurationError`, `SDKRetrievalError`, `SDKModelError`, and `SDKTimeoutError`.
- Added deterministic boundary exception mapping in `agent_search.public_api` across sync run, async run, status, and cancel SDK entrypoints.
- Added failure-path visibility logs for mapped error class and original error class at each SDK boundary.
- Added SDK error-path tests in `tests/sdk/test_errors.py` and updated existing SDK contract tests to assert SDK configuration exceptions.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`
- `curl -sS -i --retry 5 --retry-connrefused --retry-delay 1 http://localhost:8000/api/health`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/sdk/test_errors.py tests/sdk/test_public_api.py tests/sdk/test_public_api_async.py tests/contracts/test_public_contracts.py"`
- `docker compose restart backend`
- `docker compose logs --tail=180 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_errors.py ...... [ 28%]
pytest: tests/sdk/test_public_api.py ... [ 42%]
pytest: tests/sdk/test_public_api_async.py ...... [ 71%]
pytest: tests/contracts/test_public_contracts.py ...... [100%]
pytest: 21 passed in 1.58s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 6

## Section 6: VectorStore protocol contract - runtime storage abstraction

**Single goal:** Define SDK retrieval protocol boundary.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Specify required retrieval methods and document semantics.
- Fail fast on protocol-incompatible stores.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/vectorstore/protocol.py` | `VectorStoreProtocol` definition. |
| `src/backend/tests/sdk/test_vectorstore_protocol.py` | Protocol compatibility tests. |

**How to test:** Run protocol contract tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `agent_search.vectorstore.protocol.VectorStoreProtocol` as the SDK retrieval boundary with documented similarity-search semantics and optional filtering behavior.
- Added `assert_vector_store_compatible` fail-fast validator with structured logging and signature checks for `similarity_search(query, k, filter=None)`.
- Wired fail-fast vector-store validation into SDK entrypoints `run` and `run_async` in `agent_search.public_api`.
- Added protocol tests in `tests/sdk/test_vectorstore_protocol.py` for compatible/incompatible stores and early rejection before runtime/job invocation.
- Updated existing SDK tests to use minimal protocol-compatible fake vector stores so error-mapping and response-shape contracts continue to execute.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose restart backend`
- `docker compose exec backend sh -lc 'cd /app && /app/.venv/bin/python -m pytest tests/sdk/test_vectorstore_protocol.py -q'`
- `docker compose exec backend sh -lc 'cd /app && /app/.venv/bin/python -m pytest tests/sdk/test_public_api.py tests/sdk/test_public_api_async.py tests/sdk/test_errors.py -q'`
- `curl -sS http://localhost:8000/api/health`
- `docker compose ps`
- `docker compose logs --tail=150 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_vectorstore_protocol.py ..... [100%]
pytest: 5 passed in 1.50s
pytest: tests/sdk/test_public_api.py tests/sdk/test_public_api_async.py tests/sdk/test_errors.py ............... [100%]
pytest: 15 passed in 1.61s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: {"status":"ok"}
```

## Completed - 2026-03-09 - Section 7

## Section 7: LangChain vector store adapter - first-class implementation

**Single goal:** Implement LangChain adapter for SDK vector store protocol.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Support similarity retrieval and score behaviors currently used.
- Preserve fallback retrieval paths.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): reuse existing LangChain packages.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/vectorstore/langchain_adapter.py` | Production protocol adapter. |
| `src/backend/tests/sdk/test_langchain_vectorstore_adapter.py` | Adapter behavior tests. |

**How to test:** Run adapter tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `LangChainVectorStoreAdapter` in `agent_search.vectorstore.langchain_adapter` as a production adapter over LangChain-compatible vector stores.
- Implemented `similarity_search(query, k, filter=None)` with stable `k` coercion and fallback for stores that do not accept `filter` in method signature.
- Implemented `similarity_search_with_relevance_scores(...)` that uses native score APIs when available and falls back to `similarity_search` when unavailable.
- Added structured retrieval-path logs (`mode=with_filter`, `mode=without_filter`, `mode=with_scores`, `mode=similarity_search`) for runtime visibility.
- Added SDK adapter tests in `tests/sdk/test_langchain_vectorstore_adapter.py` covering filter passing, fallback paths, relevance-score behavior, and score fallback behavior.
- Exported the adapter from `agent_search.vectorstore.__init__` for first-class SDK access.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`
- `docker compose exec backend uv run --with pytest pytest tests/sdk/test_langchain_vectorstore_adapter.py`
- `docker compose exec backend uv run --with pytest pytest tests/sdk/test_vectorstore_protocol.py`
- `docker compose restart backend`
- `curl -sS http://localhost:8000/api/health`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_langchain_vectorstore_adapter.py .... [100%]
pytest: 4 passed in 1.49s
pytest: tests/sdk/test_vectorstore_protocol.py ..... [100%]
pytest: 5 passed in 1.50s
backend: Application startup complete.
backend: Uvicorn running on http://0.0.0.0:8000
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: {"status":"ok"}
```

## Completed - 2026-03-09 - Section 8

## Section 8: Runtime configuration model - explicit SDK knobs

**Single goal:** Add public `RuntimeConfig` for SDK execution controls.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Include timeout, retrieval, and rerank controls.
- Defaults must preserve current behavior.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/config.py` | SDK runtime configuration model. |
| `src/backend/tests/sdk/test_runtime_config.py` | Config defaults/override tests. |

**How to test:** Run runtime config tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `agent_search.config` with public `RuntimeConfig` and nested `RuntimeTimeoutConfig`, `RuntimeRetrievalConfig`, and `RuntimeRerankConfig`.
- Added default-preserving coercion for timeout/retrieval/rerank overrides to keep runtime behavior stable when config is omitted or malformed.
- Added structured logging in config coercion and in SDK `run`/`run_async` to make effective runtime controls visible.
- Exported runtime config types from `agent_search.__init__` so SDK consumers can import them directly.
- Added `tests/sdk/test_runtime_config.py` validating defaults, nested overrides, and invalid override fallback behavior.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`
- `docker compose restart backend`
- `docker compose exec backend uv run pytest tests/sdk/test_runtime_config.py` (failed: `pytest` not found in base env)
- `docker compose exec backend uv run --with pytest pytest tests/sdk/test_runtime_config.py`
- `docker compose exec backend uv run --with pytest pytest tests/sdk/test_public_api.py tests/sdk/test_public_api_async.py`
- `docker compose exec backend uv run python -c "from agent_search.config import RuntimeConfig; print(RuntimeConfig.from_dict({'timeout': {'initial_search_timeout_s': 55}, 'rerank': {'provider': 'flashrank', 'top_n': 5}}))"`
- `curl -sS http://localhost:8000/api/health`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=60 frontend`
- `docker compose logs --tail=60 db`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_runtime_config.py ... [100%]
pytest: 3 passed in 1.43s
pytest: tests/sdk/test_public_api.py tests/sdk/test_public_api_async.py ......... [100%]
pytest: 9 passed in 1.46s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: {"status":"ok"}
```

## Completed - 2026-03-09 - Section 9

## Section 9: Runtime core module boundary - framework-independent orchestration shell

**Single goal:** Extract framework-independent runtime orchestrator.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Move orchestration into SDK runtime module.
- Remove FastAPI/SQLAlchemy coupling at core runtime boundary.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/runner.py` | Core orchestration boundary. |
| `src/backend/services/agent_service.py` | Compatibility wrapper during migration. |
| `src/backend/tests/services/test_agent_service.py` | Wrapper parity tests. |

**How to test:** Run runtime + service parity tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added framework-independent runtime entrypoint `agent_search.runtime.runner.run_runtime_agent` that performs vector-store acquisition, initial context retrieval, graph execution, and runtime-response mapping without requiring FastAPI or SQLAlchemy session types.
- Converted `services.agent_service.run_runtime_agent` into a compatibility wrapper that preserves existing API shape (`db` argument) while delegating orchestration to the runtime core module.
- Added explicit delegation logs at both service-wrapper and runtime-core boundaries for visibility.
- Added service parity tests validating runtime-core execution without DB dependency and wrapper delegation behavior.
- Fixed `_build_callbacks` recursion in `services.agent_service` (runtime bug surfaced during container log verification), restoring callback construction and preventing runtime 500s.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs --tail=160 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`
- `docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py`
- `docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py -k 'runtime_runner_executes_without_db_dependency or run_runtime_agent_wrapper_delegates_to_runtime_runner'`
- `docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py -k 'run_sequential_graph_runner_executes_strict_node_order or run_parallel_graph_runner_preserves_subquestion_order_and_emits_snapshots or runtime_runner_executes_without_db_dependency or run_runtime_agent_wrapper_delegates_to_runtime_runner'`
- `docker compose exec backend uv run --with pytest pytest tests/api/test_agent_run.py`
- `docker compose exec backend uv run --with pytest pytest tests/sdk/test_public_api.py tests/sdk/test_errors.py tests/sdk/test_vectorstore_protocol.py`
- `docker compose down && docker compose up -d`
- `curl -sS http://localhost:8000/api/health`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What changed in policy X?"}'`
- `docker compose restart backend`
- `docker compose logs --tail=260 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`

**Useful logs (excerpt):**
```text
pytest: tests/services/test_agent_service.py .... [100%]
pytest: 4 passed, 48 deselected in 1.69s
pytest: tests/api/test_agent_run.py ..... [100%]
pytest: 5 passed in 1.92s
pytest: tests/sdk/test_public_api.py ...
pytest: tests/sdk/test_errors.py ......
pytest: tests/sdk/test_vectorstore_protocol.py .....
pytest: 14 passed in 1.63s
backend: Runtime agent service wrapper delegating to runtime core query=What changed in policy X? ...
backend: Runtime core run start query=What changed in policy X? ...
backend: Runtime core run complete sub_qa_count=5 output_length=165 snapshot_count=22 ...
backend: Runtime agent service wrapper completed delegation sub_qa_count=5 output_length=165
backend: POST /api/agents/run HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: {"status":"ok"}
```

## Completed - 2026-03-09 - Section 10

## Section 10: Decomposition node extraction - isolated runtime node module

**Single goal:** Extract decomposition node without behavior change.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Preserve prompt/parse/fallback semantics.
- Keep output guarantees unchanged.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/decompose.py` | Decomposition node. |
| `src/backend/tests/sdk/test_node_decompose.py` | Decomposition tests. |

**How to test:** Run decomposition node tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `agent_search.runtime.nodes.decompose` as an isolated runtime node module with decomposition prompt execution, output parsing, timeout handling, fallback behavior, and structured node logs.
- Added `agent_search.runtime.nodes.__init__` export so node modules are first-class runtime components.
- Updated `services.agent_service.run_decomposition_node` to delegate to the new runtime node module while preserving existing behavior through dependency injection hooks.
- Preserved compatibility with existing decomposition tests/patch points in `services.agent_service` and avoided orchestration behavior changes.
- Fixed an import-cycle regression surfaced in backend container logs by moving the runtime-node import in `agent_service` to function scope (lazy import).
- Added `tests/sdk/test_node_decompose.py` to validate normalized outputs, timeout fallback, and parse/fallback semantics from the new node module.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose ps`
- `docker compose exec backend uv run --with pytest pytest tests/sdk/test_node_decompose.py`
- `docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py -k 'parse_decomposition_output or run_decomposition_node_uses_fallback_on_timeout or run_decomposition_node_emits_normalized_subquestions'`
- `docker compose restart backend`
- `docker compose logs --tail=160 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`
- `docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py -k 'run_decomposition_node_emits_normalized_subquestions or run_decomposition_node_uses_fallback_on_timeout'`
- `docker compose restart backend`
- `curl -sS http://localhost:8000/api/health`
- `docker compose logs --tail=180 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_node_decompose.py ... [100%]
pytest: 3 passed in 1.65s
pytest: tests/services/test_agent_service.py ........ [100%]
pytest: 8 passed, 44 deselected in 2.08s
backend: ImportError: cannot import name 'cancel_agent_run_job' from partially initialized module 'services.agent_jobs' (resolved by lazy runtime-node import)
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: {"status":"ok"}
```

## Completed - 2026-03-09 - Section 11

## Section 11: Expansion node extraction - isolated runtime node module

**Single goal:** Extract query expansion node without behavior change.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Preserve bounds, dedupe, fallback behavior.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/expand.py` | Expansion node. |
| `src/backend/tests/sdk/test_node_expand.py` | Expansion tests. |

**How to test:** Run expansion node tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `agent_search.runtime.nodes.expand` as an isolated expansion-node module with runtime start/complete logs and dependency-injection hooks for parity testing.
- Updated `services.agent_service.run_expand_node` to delegate to the runtime node while preserving existing config defaults and query expansion behavior.
- Exported `run_expansion_node` from `agent_search.runtime.nodes`.
- Added `tests/sdk/test_node_expand.py` to validate expansion node output passthrough and explicit config forwarding.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `curl -sS http://localhost:8000/api/health`
- `docker compose exec backend uv run --with pytest pytest tests/sdk/test_node_expand.py`
- `docker compose exec backend uv run --with pytest pytest tests/services/test_agent_service.py -k 'run_expand_node_emits_bounded_query_list or apply_expand_node_output_to_graph_state_updates_artifacts_and_compat_fields'`
- `docker compose restart backend`
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_node_expand.py .. [100%]
pytest: 2 passed in 1.97s
pytest: tests/services/test_agent_service.py .. [100%]
pytest: 2 passed, 50 deselected in 2.01s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: {"status":"ok"}
```

## Completed - 2026-03-09 - Section 12

## Section 12: Search node extraction - protocol-backed retrieval module

**Single goal:** Extract retrieval/merge/dedupe logic into protocol-backed node.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Use `VectorStoreProtocol` only.
- Preserve provenance output used for citations/debug.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/search.py` | Search node implementation. |
| `src/backend/tests/sdk/test_node_search.py` | Search node tests. |

**How to test:** Run search node tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `agent_search.runtime.nodes.search.run_search_node` with extracted retrieval/merge/dedupe behavior.
- Enforced protocol boundary in search node via `assert_vector_store_compatible` and `VectorStoreProtocol` typing.
- Preserved search provenance payload structure (`query`, `query_index`, `query_rank`, `document_identity`, `document_id`, `source`, `deduped`).
- Delegated `services.agent_service.run_search_node` to runtime node as compatibility wrapper.
- Added SDK-level tests in `tests/sdk/test_node_search.py` for dedupe/merge behavior, empty-query skip behavior, and protocol incompatibility rejection.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d && docker compose ps`
- `docker compose restart backend && docker compose ps`
- `docker compose exec backend uv run pytest tests/sdk/test_node_search.py` (failed: `pytest` missing)
- `docker compose exec backend uv run pytest tests/services/test_agent_service.py -k test_run_search_node_merges_and_dedupes_multi_query_results` (failed: `pytest` missing)
- `docker compose exec backend uv run python -m pytest --version` (failed: `No module named pytest`)
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/sdk/test_node_search.py"`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/services/test_agent_service.py -k test_run_search_node_merges_and_dedupes_multi_query_results"`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`
- `curl -sS http://localhost:8000/api/health`

**Useful logs (excerpt):**
```text
backend: Application startup complete.
backend: Uvicorn running on http://0.0.0.0:8000
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: {"status":"ok"}
uv: error: Failed to spawn: `pytest` (No such file or directory)
python: No module named pytest
pytest: tests/sdk/test_node_search.py ... [100%]
pytest: 3 passed in 1.56s
pytest: tests/services/test_agent_service.py . [100%]
pytest: 1 passed, 51 deselected in 1.62s
```

## Completed - 2026-03-09 - Section 13

## Section 13: Rerank node extraction - isolated ranking module

**Single goal:** Extract rerank logic without behavior change.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Preserve deterministic fallback.
- Preserve citation row remapping semantics.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): reuse existing `flashrank`.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/rerank.py` | Rerank node. |
| `src/backend/tests/sdk/test_node_rerank.py` | Rerank tests. |

**How to test:** Run rerank node tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added runtime rerank node module `agent_search.runtime.nodes.rerank` and extracted rerank execution logic from `services.agent_service`.
- Preserved deterministic fallback behavior by continuing to route through existing `services.reranker_service.rerank_documents` with unchanged config defaults.
- Preserved citation row remapping semantics by retaining original-rank to document-id mapping while reindexing citation rows by reranked order.
- Kept service compatibility by turning `services.agent_service.run_rerank_node` into a thin delegation wrapper to the runtime node.
- Added SDK rerank node tests for reordering/remapping behavior, query fallback behavior, and empty-candidate short-circuit behavior.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/sdk/test_node_rerank.py"`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/services/test_agent_service.py -k 'run_rerank_node_reorders_and_trims_documents or apply_rerank_node_output_to_graph_state_updates_artifacts_and_compat_fields'"`
- `docker compose restart backend`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --tail=180 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_node_rerank.py ... [100%]
pytest: 3 passed in 1.86s
pytest: tests/services/test_agent_service.py .. [100%]
pytest: 2 passed, 50 deselected in 1.99s
backend: Application startup complete.
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 14

## Section 14: Subanswer node extraction - isolated answer module

**Single goal:** Extract subanswer generation/verification node.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Preserve answerability verification and fallback behavior.
- Keep sub-question output fields stable.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/answer.py` | Subanswer node implementation. |
| `src/backend/tests/sdk/test_node_answer.py` | Subanswer node tests. |

**How to test:** Run subanswer node tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `agent_search.runtime.nodes.answer.run_answer_node` and extracted subanswer generation + verification flow from `services.agent_service`.
- Preserved fallback behavior for `no_reranked_documents`, unsupported answers, and citation-contract enforcement (`missing_citation_markers`, `missing_supporting_source_rows`).
- Preserved stable output fields for `AnswerSubquestionNodeOutput` including `sub_answer`, `citation_indices_used`, `answerable`, `verification_reason`, and `citation_rows_by_index`.
- Updated `services.agent_service.run_answer_subquestion_node` to delegate to runtime node while keeping existing dependency wiring and constants.
- Exported new runtime node in `agent_search.runtime.nodes.__init__`.
- Added SDK tests in `tests/sdk/test_node_answer.py` for fallback, supported-answer, and citation-contract enforcement cases.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build && docker compose up -d && docker compose ps`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/sdk/test_node_answer.py"`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/services/test_agent_service.py -k 'run_answer_subquestion_node or apply_answer_subquestion_node_output_to_graph_state'"`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/sdk/test_node_answer.py tests/services/test_agent_service.py -k 'run_answer_subquestion_node or apply_answer_subquestion_node_output_to_graph_state or test_node_answer'"`
- `docker compose restart backend && docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --tail=140 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_node_answer.py .... [100%]
pytest: 4 passed in 1.45s
pytest: tests/services/test_agent_service.py ... [100%]
pytest: 3 passed, 49 deselected in 1.41s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 15

## Section 15: Final synthesis node extraction - isolated output module

**Single goal:** Extract final synthesis/citation contract logic.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Preserve final output shape and fallback selection behavior.
- Preserve citation contract enforcement.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/synthesize.py` | Final synthesis node. |
| `src/backend/tests/sdk/test_node_synthesize.py` | Synthesis node tests. |

**How to test:** Run synthesis node tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Extracted final synthesis/citation-contract behavior from `services/agent_service.py` into `agent_search.runtime.nodes.synthesize.run_synthesize_node`.
- Preserved fallback selection behavior (answerable-first, dedupe, citation-index validation, timeout-prefix fallback).
- Added dedicated SDK node tests in `tests/sdk/test_node_synthesize.py` for valid synthesis pass-through, missing-citation fallback, invalid-citation fallback, and timeout-prefix fallback paths.
- Updated `services.agent_service.run_synthesize_final_node` to delegate directly to the extracted runtime node.
- Exported the new node via `agent_search.runtime.nodes.__init__`.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose exec backend uv run --with pytest pytest tests/sdk/test_node_synthesize.py tests/services/test_agent_service.py -k synthesize`
- `docker compose restart backend`
- `docker compose ps`
- `docker compose logs --tail=180 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`
- `curl -sS -i http://localhost:8000/api/health`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_node_synthesize.py .... [ 50%]
pytest: tests/services/test_agent_service.py .... [100%]
pytest: 8 passed, 48 deselected in 1.72s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 16

## Section 16: SDK sync runtime wiring - end-to-end sync path

**Single goal:** Wire public SDK sync API to extracted runtime graph.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Use extracted runtime modules only.
- Require caller-provided `model` and `vector_store`.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/public_api.py` | Sync execution wiring. |
| `src/backend/agent_search/runtime/runner.py` | Sync orchestration entry. |
| `src/backend/tests/sdk/test_sdk_run_e2e.py` | Sync E2E tests. |

**How to test:** Run SDK sync E2E tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Rewired `agent_search.public_api.run` to call `agent_search.runtime.runner.run_runtime_agent` instead of legacy `services.agent_service.run_runtime_agent`.
- Preserved required SDK inputs (`model` and `vector_store`) and existing SDK error mapping/logging behavior.
- Added SDK sync E2E coverage in `tests/sdk/test_sdk_run_e2e.py` to verify the end-to-end path `public_api.run -> runtime.runner` uses caller-provided dependencies and runtime orchestration output mapping.
- Updated `tests/sdk/test_public_api.py` to match the new sync runtime call signature.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d && docker compose ps`
- `docker compose exec backend uv run --with pytest pytest tests/sdk/test_sdk_run_e2e.py tests/sdk/test_public_api.py tests/sdk/test_errors.py tests/sdk/test_vectorstore_protocol.py`
- `docker compose restart backend && docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --tail=220 backend`
- `docker compose logs --tail=100 frontend`
- `docker compose logs --tail=100 db`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_sdk_run_e2e.py . [  6%]
pytest: tests/sdk/test_public_api.py ... [ 26%]
pytest: tests/sdk/test_errors.py ...... [ 66%]
pytest: tests/sdk/test_vectorstore_protocol.py ..... [100%]
pytest: 15 passed in 1.45s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 17

## Section 17: SDK async runtime wiring - end-to-end async path

**Single goal:** Wire SDK async lifecycle to shared runtime job manager.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Implement start/status/cancel manager.
- Preserve stage snapshots and cancellation semantics.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/jobs.py` | Async job manager. |
| `src/backend/agent_search/public_api.py` | Async lifecycle wiring. |
| `src/backend/tests/sdk/test_sdk_async_e2e.py` | Async E2E tests. |

**How to test:** Run SDK async E2E tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `agent_search.runtime.jobs` as the shared SDK async job manager with start/status/cancel operations, job state store, stage snapshot mapping, and cancellation handling.
- Wired `agent_search.public_api` async lifecycle methods to the new runtime manager and passed caller-provided `model` and `vector_store` through async execution.
- Added `tests/sdk/test_sdk_async_e2e.py` to validate end-to-end async wiring, snapshot stage propagation, and cancellation semantics.
- Updated `tests/sdk/test_public_api_async.py` start-hook assertion to match new async manager call signature (`model` and `vector_store` kwargs).

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/sdk/test_sdk_async_e2e.py tests/sdk/test_public_api_async.py"` (first run: 1 failed, fixed assertion)
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/sdk/test_sdk_async_e2e.py tests/sdk/test_public_api_async.py"` (second run: passed)
- `docker compose restart backend`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose ps`
- `docker compose logs --tail=140 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/sdk/test_sdk_async_e2e.py .. [ 25%]
pytest: tests/sdk/test_public_api_async.py ...... [100%]
pytest: 8 passed in 1.39s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 18

## Section 18: Backend endpoint delegation - SDK-only runtime path

**Single goal:** Delegate backend sync/async agent routes to SDK public API.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- `/api/agents/run` delegates to SDK sync.
- Async start/status/cancel routes delegate to SDK async lifecycle.
- Preserve current payload contracts.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/routers/agent.py` | SDK delegation for all agent routes. |
| `src/backend/tests/api/test_agent_run.py` | Delegation parity tests. |

**How to test:** Run backend agent API tests for sync+async.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Updated `routers/agent.py` to delegate all agent endpoints to `agent_search.public_api` (`sdk_run`, `sdk_run_async`, `sdk_get_run_status`, `sdk_cancel_run`).
- Added router-level runtime dependency resolver for SDK calls using existing backend vector store and model configuration.
- Preserved async status/cancel 404 response contracts by mapping SDK configuration errors to the existing route-level HTTP exceptions.
- Added delegation-parity API tests to assert sync/async SDK delegation inputs and response-shape stability, including 404 mapping tests for status/cancel missing jobs.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=200 frontend`
- `docker compose logs --tail=200 db`
- `docker compose exec backend uv run --with pytest pytest tests/api/test_agent_run.py`
- `docker compose restart backend`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health` (first attempt failed during restart; second attempt succeeded)
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`
- `docker compose exec backend uv run python - <<'PY' ... BenchmarkRunStatusResponse(...).model_dump(mode='json')['objective'] ... PY`

**Useful logs (excerpt):**
```text
pytest: tests/api/test_agent_run.py ....... [100%]
pytest: 7 passed in 1.97s
backend: Application startup complete.
backend: Uvicorn running on http://0.0.0.0:8000
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
manual-status-objective: {'primary_kpi': 'correctness', 'secondary_kpi': 'latency', 'execution_mode': 'manual_only', 'targets': {'min_correctness': 0.75, 'max_latency_ms_p95': 30000, 'max_cost_usd': 5.0}}
```

## Completed - 2026-03-09 - Section 19

## Section 19: Legacy runtime cleanup - single orchestration implementation

**Single goal:** Remove duplicate orchestration paths outside SDK runtime.

**Why:** This establishes the stable SDK/runtime core that every later benchmark and product feature depends on.


**Details:**
- Keep service wrappers thin.
- Ensure backend and internal callers share same runtime path.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Thin SDK wrapper only. |
| `src/backend/services/agent_jobs.py` | Delegate to SDK jobs manager. |
| `src/backend/tests/services/test_agent_service.py` | Single-path behavior tests. |

**How to test:** Run service tests and verify no duplicate path usage.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Replaced legacy `services/agent_jobs.py` orchestration implementation with a compatibility wrapper that delegates `start/get/cancel` directly to `agent_search.runtime.jobs`.
- Kept and validated `services/agent_service.run_runtime_agent` as a thin wrapper to `agent_search.runtime.runner.run_runtime_agent`.
- Added service-level delegation tests for `agent_jobs` wrappers and retained wrapper delegation coverage for `agent_service`.
- Fixed pre-existing `test_agent_service.py` incompatibilities surfaced by full service test execution (timeout default expectation and monkeypatched callback signatures) so the required service suite now passes.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`
- `docker compose exec backend uv pip install pytest`
- `docker compose exec backend uv run pytest tests/services/test_agent_service.py -k "runtime_runner_executes_without_db_dependency or run_runtime_agent_wrapper_delegates_to_runtime_runner or agent_jobs_"`
- `docker compose exec backend uv run pytest tests/services/test_agent_service.py`
- `docker compose restart backend`
- `docker compose ps`
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=100 frontend`
- `docker compose logs --tail=100 db`
- `curl -sS http://localhost:8000/api/health`

**Useful logs (excerpt):**
```text
pytest: tests/services/test_agent_service.py ................................... [ 63%]
pytest: ....................                                                     [100%]
pytest: 55 passed in 7.08s
backend: Application startup complete.
backend: Uvicorn running on http://0.0.0.0:8000
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: {"status":"ok"}
```

## Completed - 2026-03-09 - Section 20

## Section 20: Benchmark charter - correctness and latency targets

**Single goal:** Define benchmark objective contract used by APIs, runner, and UI.

**Why:** This builds the benchmark execution foundation so runs are reproducible, operable, and stored correctly before adding advanced analysis.


**Details:**
- Primary KPI correctness, secondary KPI latency.
- v1 thresholds: correctness >= 0.75 and p95 latency <= 30,000ms.
- Manual-only benchmark execution.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `spec.md` | Benchmark requirement source of truth. |
| `src/backend/schemas/benchmark.py` | Threshold models used by API/UI. |

**How to test:** Validate threshold block appears in benchmark run status response.

**Test results:**
- Completed.

---

**Completion notes:**
- Added explicit benchmark objective contract models in `src/backend/schemas/benchmark.py`: `BenchmarkKPI`, `BenchmarkExecutionMode`, and `BenchmarkObjective`.
- Updated `BenchmarkTargets` default correctness threshold from `0.70` to `0.75` while keeping latency p95 threshold at `30000ms` and cost tracking separate.
- Added `objective` to `BenchmarkRunStatusResponse` with a default objective block so status payload serialization always includes KPI priority, manual-only execution mode, and thresholds.
- Updated schema exports in `src/backend/schemas/__init__.py` and synced `spec.md` charter wording to the objective model.
- Extended `tests/contracts/test_public_contracts.py` to freeze the new status schema field and assert objective threshold block serialization in a status response payload.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=200 frontend`
- `docker compose logs --tail=200 db`
- `docker compose exec backend uv run pytest tests/contracts/test_public_contracts.py` (failed: pytest not present in uv run env)
- `docker compose exec backend uv run --with pytest pytest tests/contracts/test_public_contracts.py`
- `docker compose restart backend`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose ps`
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`

**Useful logs (excerpt):**
```text
pytest: tests/contracts/test_public_contracts.py ........ [100%]
pytest: 8 passed in 1.52s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 21

## Section 21: Benchmark runtime settings - env-backed and reproducible

**Single goal:** Add centralized benchmark settings and context fingerprinting.

**Why:** This builds the benchmark execution foundation so runs are reproducible, operable, and stored correctly before adding advanced analysis.


**Details:**
- Add settings for dataset default, judge model, timeout caps, and targets.
- Compute execution context fingerprint for run reproducibility.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): update `.env.example` only.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/config.py` | Benchmark runtime settings. |
| `.env.example` | Benchmark env docs. |
| `src/backend/tests/utils/test_benchmark_config.py` | Config parsing tests. |

**How to test:** Run benchmark config tests.

**Test results:**
- Completed.

---

**Completion notes:**
- Added new backend benchmark runtime settings module at `src/backend/config.py` with centralized env-backed parsing for dataset defaults, judge model, timeout caps, and KPI targets.
- Added deterministic execution context building and SHA-256 fingerprinting helpers for benchmark reproducibility (`build_benchmark_execution_context`, `compute_benchmark_context_fingerprint`, `get_benchmark_context_fingerprint`).
- Added visibility logs for invalid env values, resolved settings, and computed fingerprints.
- Extended `.env.example` with benchmark runtime configuration keys.
- Added `src/backend/tests/utils/test_benchmark_config.py` covering defaults, env overrides, invalid fallback behavior, and fingerprint stability/change semantics.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps -a`
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=200 db`
- `curl -sS http://localhost:8000/api/health`
- `docker compose exec backend uv run --with pytest pytest tests/utils/test_benchmark_config.py`
- `docker compose restart`
- `docker compose ps -a`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`

**Useful logs (excerpt):**
```text
pytest: tests/utils/test_benchmark_config.py ..... [100%]
pytest: 5 passed in 0.03s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 22

## Section 22: Internal benchmark dataset schema - DeepResearchBench-aligned

**Single goal:** Define strict JSONL schema for internal benchmark questions.

**Why:** This builds the benchmark execution foundation so runs are reproducible, operable, and stored correctly before adding advanced analysis.


**Details:**
- Required fields: `question_id`, `question`, `domain`, `difficulty`, `expected_answer_points`, `required_sources`, `disallowed_behaviors`.
- v1 dataset size target: 120 public questions.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/benchmarks/datasets/schema.md` | Dataset contract documentation. |
| `src/backend/benchmarks/datasets/internal_v1/questions.jsonl` | v1 benchmark questions. |
| `src/backend/tests/benchmarks/test_dataset_schema.py` | Schema/distribution tests. |

**How to test:** Run dataset schema tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added strict benchmark dataset validation model in `src/backend/benchmarks/datasets/schema.py` with extra-field rejection and per-line JSON/schema validation.
- Added loader visibility logs for dataset load start/completion and validation failures.
- Added DeepResearchBench-aligned dataset contract documentation in `src/backend/benchmarks/datasets/schema.md`.
- Added `internal_v1` benchmark dataset fixture with exactly 120 JSONL question rows and all required fields.
- Added `tests/benchmarks/test_dataset_schema.py` covering strict field set checks, unique ID format checks, domain/difficulty distribution checks, and loader logging checks.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d && docker compose ps`
- `docker compose exec backend uv run --with pytest pytest tests/benchmarks/test_dataset_schema.py`
- `docker compose restart backend`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose ps`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/benchmarks/test_dataset_schema.py ..... [100%]
pytest: 5 passed in 0.03s
backend: Application startup complete.
backend: Uvicorn running on http://0.0.0.0:8000
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 23

## Section 23: Dataset curation workflow - generation and human review

**Single goal:** Build reproducible question generation and review workflow.

**Why:** This builds the benchmark execution foundation so runs are reproducible, operable, and stored correctly before adding advanced analysis.


**Details:**
- Generate question candidates from public corpora via OpenAI.
- Require human approval and provenance metadata before dataset freeze.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): optional `typer` or argparse.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/benchmarks/tools/generate_questions.py` | Candidate generation utility. |
| `src/backend/benchmarks/tools/review_queue.py` | Review/approval workflow utility. |
| `src/backend/benchmarks/datasets/internal_v1/provenance.jsonl` | Provenance ledger. |

**How to test:** Run unit tests for review transitions and export.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `benchmarks.tools.generate_questions` with deterministic candidate IDs, OpenAI-backed generation path (via `langchain_openai`), strict JSON output validation, JSONL review queue export, and generation visibility logs.
- Added `benchmarks.tools.review_queue` with explicit review state transitions (`pending_review` -> `approved`/`rejected`), immutable provenance ledger append events, and dataset freeze export that blocks while pending candidates exist.
- Added benchmark unit tests covering candidate generation, review transition/provenance behavior, export ordering/schema, and pending-review freeze guardrail.
- Added `src/backend/benchmarks/datasets/internal_v1/provenance.jsonl` ledger file for review events.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose restart backend`
- `docker compose exec backend uv run --with pytest pytest tests/benchmarks/test_dataset_curation_workflow.py -q`
- `docker compose ps`
- `docker compose logs --tail=160 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`
- `curl -sS -i http://localhost:8000/api/health`

**Useful logs (excerpt):**
```text
pytest: tests/benchmarks/test_dataset_curation_workflow.py .... [100%]
pytest: 4 passed in 0.04s
backend: Application startup complete.
backend: Uvicorn running on http://0.0.0.0:8000
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 24

## Section 24: Benchmark corpus fixture - deterministic source loading

**Single goal:** Ensure benchmark runs operate on deterministic indexed source corpus.

**Why:** This builds the benchmark execution foundation so runs are reproducible, operable, and stored correctly before adding advanced analysis.


**Details:**
- Define corpus manifest.
- Add repeatable load/reset utility and corpus hash generation.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): reuse existing internal-data load/wipe flow.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/benchmarks/corpus/internal_v1_manifest.json` | Source manifest for benchmark corpus. |
| `src/backend/benchmarks/tools/load_corpus.py` | Deterministic corpus loader/reset tool. |
| `src/backend/tests/benchmarks/test_corpus_loader.py` | Deterministic corpus tests. |

**How to test:** Run corpus load twice and verify identical hash/counts.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `benchmarks/corpus/internal_v1_manifest.json` with fixed-order curated wiki source IDs for benchmark corpus determinism.
- Added `benchmarks.tools.load_corpus` loader utility with strict manifest validation, reset support via existing `wipe_internal_data`, deterministic ordered loads via existing `load_internal_data`, and SHA-256 manifest/corpus hash generation.
- Added CLI entrypoint (`python -m benchmarks.tools.load_corpus`) with `--manifest` and `--no-reset` flags for repeatable operator runs.
- Added benchmark tests validating deterministic repeated load hash/count parity, manifest duplicate-ID guardrails, source-scoped corpus hashing, and visibility logs.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build && docker compose up -d && docker compose ps`
- `docker compose exec backend uv run --with pytest pytest tests/benchmarks/test_corpus_loader.py -q`
- `docker compose restart backend`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --tail=180 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`

**Useful logs (excerpt):**
```text
pytest: tests/benchmarks/test_corpus_loader.py .... [100%]
pytest: 4 passed in 1.10s
backend: Application startup complete.
backend: Uvicorn running on http://0.0.0.0:8000
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 25

## Section 25: Benchmark DB foundation - run metadata tables

**Single goal:** Add persistent run metadata schema.

**Why:** This builds the benchmark execution foundation so runs are reproducible, operable, and stored correctly before adding advanced analysis.


**Details:**
- Add `benchmark_runs` and `benchmark_run_modes`.
- Record SLO snapshot, context fingerprint, and corpus hash.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/models.py` | Benchmark run metadata models. |
| `src/backend/alembic/versions/002_add_benchmark_run_metadata_tables.py` | Migration file. |
| `src/backend/tests/db/test_benchmark_run_metadata_schema.py` | Schema tests. |

**How to test:** Run alembic upgrade and schema tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `BenchmarkRun` and `BenchmarkRunMode` ORM models in `src/backend/models.py` with persisted run metadata fields for `slo_snapshot`, `context_fingerprint`, and `corpus_hash`.
- Added relational guarantees for run modes: foreign key to `benchmark_runs.run_id`, cascade delete, and unique `(run_id, mode)` constraint.
- Added Alembic migration `002_add_benchmark_run_metadata_tables.py` to create tables/indexes and added migration visibility logs for upgrade/downgrade lifecycle.
- Added DB schema tests in `tests/db/test_benchmark_run_metadata_schema.py` validating table/column presence, uniqueness enforcement, and cascade delete behavior.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs --no-color --tail=120 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 db`
- `docker compose exec backend uv run alembic upgrade head`
- `docker compose exec backend uv run --with pytest pytest tests/db/test_benchmark_run_metadata_schema.py`
- `docker compose restart`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --no-color --tail=220 backend`
- `docker compose logs --no-color --tail=140 frontend`
- `docker compose logs --no-color --tail=140 db`
- `docker compose exec backend uv run alembic current`
- `docker compose exec db psql -U agent_user -d agent_search -c "\\dt benchmark_*"`
- `docker compose exec db psql -U agent_user -d agent_search -c "\\d benchmark_runs"`
- `docker compose exec db psql -U agent_user -d agent_search -c "\\d benchmark_run_modes"`

**Useful logs (excerpt):**
```text
alembic: Running upgrade 001_internal -> 002_benchmark_run_metadata
pytest: tests/db/test_benchmark_run_metadata_schema.py .. [100%]
pytest: 2 passed in 0.78s
alembic current: 002_benchmark_run_metadata (head)
psql: benchmark_runs, benchmark_run_modes tables present
db: duplicate key value violates unique constraint "uq_benchmark_run_modes_run_id_mode" (expected by uniqueness test)
health: HTTP/1.1 200 OK {"status":"ok"}
backend: Application startup complete.
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 26

## Section 26: Benchmark DB outputs - per-question result table

**Single goal:** Add persistent per-question/per-mode result storage.

**Why:** This builds the benchmark execution foundation so runs are reproducible, operable, and stored correctly before adding advanced analysis.


**Details:**
- Add `benchmark_results` keyed by `(run_id, mode, question_id)`.
- Persist answer payload, citations, latency, tokens, execution errors.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/models.py` | `BenchmarkResult` model. |
| `src/backend/alembic/versions/003_add_benchmark_results_table.py` | Migration file. |
| `src/backend/tests/db/test_benchmark_results_schema.py` | Schema/constraint tests. |

**How to test:** Run migration and DB tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `BenchmarkResult` ORM model to `src/backend/models.py` with uniqueness on `(run_id, mode, question_id)`, FK cascade to `benchmark_runs`, and persisted fields for answer payload, citations, latency, token usage, and execution errors.
- Added `BenchmarkRun.results` relationship for run-level access to per-question result rows.
- Added Alembic migration `003_add_benchmark_results_table.py` with table creation, indexes, unique constraint, and migration lifecycle logs for upgrade/downgrade visibility.
- Added DB schema tests in `tests/db/test_benchmark_results_schema.py` covering expected columns, uniqueness enforcement, and cascade delete behavior.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs --no-color --tail=120 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 db`
- `docker compose restart backend`
- `docker compose logs --no-color --tail=200 backend`
- `docker compose exec backend uv run alembic current`
- `docker compose exec backend uv run alembic upgrade head`
- `docker compose exec backend uv run --with pytest python -m pytest tests/db/test_benchmark_results_schema.py tests/db/test_benchmark_run_metadata_schema.py`
- `docker compose logs --no-color --tail=200 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=160 db`

**Useful logs (excerpt):**
```text
alembic current: 003_benchmark_results (head)
alembic: Running upgrade 002_benchmark_run_metadata -> 003_benchmark_results
pytest: tests/db/test_benchmark_results_schema.py .. [ 50%]
pytest: tests/db/test_benchmark_run_metadata_schema.py .. [100%]
pytest: 4 passed in 0.85s
backend: Application startup complete.
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
db: duplicate key value violates unique constraint "uq_benchmark_results_run_mode_question" (expected by uniqueness test)
```

## Completed - 2026-03-09 - Section 27

## Section 27: Benchmark mode registry - deterministic evaluation modes

**Single goal:** Define stable benchmark mode registry.

**Why:** This builds the benchmark execution foundation so runs are reproducible, operable, and stored correctly before adding advanced analysis.


**Details:**
- Modes: `baseline_retrieve_then_answer`, `agentic_default`, `agentic_no_rerank`, `agentic_single_query_no_decompose`.
- Reject unknown modes at validation time.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_modes.py` | Mode definitions and overrides. |
| `src/backend/schemas/benchmark.py` | Mode enums/validators. |
| `src/backend/tests/services/test_benchmark_modes.py` | Registry tests. |

**How to test:** Run benchmark mode tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added deterministic benchmark mode registry in `services/benchmark_modes.py` with explicit runtime override blocks for all four required modes.
- Updated `schemas/benchmark.py` mode enum values to the required mode set and added validation-time rejection/logging for unsupported modes.
- Added `tests/services/test_benchmark_modes.py` covering registry ordering, mode override definitions, defensive override-copy behavior, and unknown mode validation failure.
- Updated `tests/contracts/test_public_contracts.py` mode snapshot assertion to align with the new frozen mode values.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose exec backend uv run --with pytest pytest tests/services/test_benchmark_modes.py tests/contracts/test_public_contracts.py`
- `docker compose restart backend`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --tail=160 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/services/test_benchmark_modes.py .... [ 33%]
pytest: tests/contracts/test_public_contracts.py ........ [100%]
pytest: 12 passed in 1.47s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 28

## Section 28: Benchmark execution adapter - SDK boundary isolation

**Single goal:** Add adapter layer so benchmark runner depends only on SDK public API boundary.

**Why:** This builds the benchmark execution foundation so runs are reproducible, operable, and stored correctly before adding advanced analysis.


**Details:**
- Runner calls adapter, adapter calls `agent_search.public_api` sync/async.
- Prevent direct dependency on legacy service internals.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_execution_adapter.py` | SDK-boundary execution adapter. |
| `src/backend/tests/services/test_benchmark_execution_adapter.py` | Adapter contract tests. |

**How to test:** Run adapter tests with mocked SDK public API.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `BenchmarkExecutionAdapter` in `services/benchmark_execution_adapter.py` as an SDK-boundary wrapper so benchmark flows call only `agent_search.public_api`.
- Implemented adapter methods for sync run, async run, async status, and async cancel, each with structured logs for operational visibility.
- Added `tests/services/test_benchmark_execution_adapter.py` with mocked SDK API calls verifying delegation and argument/response contract forwarding for all adapter methods.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/services/test_benchmark_execution_adapter.py"`
- `docker compose restart backend`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/services/test_benchmark_execution_adapter.py .... [100%]
pytest: 4 passed in 1.58s
backend: Application startup complete.
backend: Uvicorn running on http://0.0.0.0:8000
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 29

## Section 29: Benchmark runner core - synchronous evaluation engine

**Single goal:** Implement core runner iterating mode x question and persisting raw outputs.

**Why:** This builds the benchmark execution foundation so runs are reproducible, operable, and stored correctly before adding advanced analysis.


**Details:**
- Load dataset by version.
- Execute through benchmark execution adapter.
- Persist incremental results for crash-safe partial progress.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_runner.py` | Core benchmark execution loop. |
| `src/backend/tests/services/test_benchmark_runner.py` | Iteration/persistence tests. |

**How to test:** Run runner tests and smoke run on small dataset.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `BenchmarkRunner` in `services/benchmark_runner.py` with a synchronous mode x question execution loop that loads dataset versions from `benchmarks/datasets/<dataset_id>/questions.jsonl`.
- Implemented crash-safe incremental persistence by upserting each `benchmark_results` row and committing per question; failures are stored in `execution_error` and re-raised to fail the run.
- Added resume behavior that skips only previously successful `(run_id, mode, question_id)` rows and retries failed rows.
- Added run initialization/metadata handling for `benchmark_runs` and `benchmark_run_modes`, including SLO snapshot defaults, context fingerprint, dataset hash as corpus hash, and per-mode runtime override metadata.
- Added `tests/services/test_benchmark_runner.py` covering full iteration persistence and failed-run resume semantics.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose exec backend sh -lc "uv run --with pytest python -m pytest tests/services/test_benchmark_runner.py"`
- `docker compose exec backend sh -lc "uv run python - <<'PY' ... section-29 smoke runner ... PY"`
- `docker compose restart backend`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --no-color --tail=200 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=160 db`

**Useful logs (excerpt):**
```text
pytest: tests/services/test_benchmark_runner.py .. [100%]
pytest: 2 passed in 1.46s
smoke: SMOKE_SUMMARY BenchmarkRunSummary(run_id='benchmark-run-a444f8d1-30a1-4507-a7ce-1d2f2c9791c2', dataset_id='smoke_v1', mode_count=1, question_count=1, completed_results=1)
backend: Benchmark runner persisted result run_id=benchmark-run-a444f8d1-30a1-4507-a7ce-1d2f2c9791c2 mode=agentic_default question_id=DRB-901 latency_ms=0 has_error=False
backend: Application startup complete.
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 30

## Section 30: Benchmark run lifecycle API - manual orchestration endpoints

**Single goal:** Expose manual benchmark create/list/get/cancel APIs.

**Why:** This builds the benchmark execution foundation so runs are reproducible, operable, and stored correctly before adding advanced analysis.


**Details:**
- Endpoints: create/list/get/cancel for runs.
- Async job lifecycle semantics mirror existing agent async behavior.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/routers/benchmarks.py` | Benchmark lifecycle endpoints. |
| `src/backend/services/benchmark_jobs.py` | Benchmark job manager. |
| `src/backend/main.py` | Router registration. |
| `src/backend/tests/api/test_benchmark_runs_api.py` | Lifecycle API tests. |

**How to test:** Run benchmark lifecycle API tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `POST /api/benchmarks/runs`, `GET /api/benchmarks/runs`, `GET /api/benchmarks/runs/{run_id}`, and `POST /api/benchmarks/runs/{run_id}/cancel`.
- Added async benchmark run job manager (`services/benchmark_jobs.py`) with in-memory job tracking, queue/start/cancel states, background runner execution, and DB-backed list/get status reads.
- Registered benchmarks router in FastAPI app startup.
- Added benchmark lifecycle API contract tests with mocked service-layer calls for success and 404 paths.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/api/test_benchmark_runs_api.py"`
- `docker compose restart backend`
- `docker compose ps`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`
- `curl -sS -i http://localhost:8000/api/health`

**Useful logs (excerpt):**
```text
pytest: tests/api/test_benchmark_runs_api.py ...... [100%]
pytest: 6 passed in 1.75s
backend: Application startup complete.
backend: GET /api/health HTTP/1.1 200 OK
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```
## Completed - 2026-03-09 - Section 31

## Section 31: DeepResearchBench compatibility export - minimal v1 I/O bridge

**Single goal:** Add a lightweight export bridge so benchmark artifacts can be emitted in a DeepResearchBench-inspired format.

**Why:** This keeps v1 evaluation simple while creating compatibility scaffolding for future DeepResearchBench-style expansion without rework.


**Details:**
- Support export records with DRB-inspired required fields (`id`, `prompt`, `article`) from internal benchmark results.
- Keep internal dataset/result schema unchanged and map through an export adapter.
- Scope is export compatibility only; no DRB evaluator execution in v1.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/benchmarks/drb/io_contract.py` | DRB-inspired schema mapping and validators. |
| `src/backend/benchmarks/drb/export_raw_data.py` | Export utility for DRB-inspired raw data artifacts. |
| `src/backend/tests/benchmarks/test_drb_io_contract.py` | I/O compatibility and validation tests. |

**How to test:** Run DRB I/O tests and validate exported records include required fields.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added DRB compatibility contract models in `benchmarks/drb/io_contract.py` with strict required-field validation for `id`, `prompt`, and `article`.
- Added internal-result mapping adapter `map_internal_result_to_drb_record` that converts benchmark result rows into DRB-inspired records without changing internal schemas.
- Added DRB JSONL exporter in `benchmarks/drb/export_raw_data.py` with export summary output and visibility logs for start, skip, and completion paths.
- Added targeted benchmark tests in `tests/benchmarks/test_drb_io_contract.py` for contract enforcement, mapping behavior, and JSONL export required-field output.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose exec backend uv run pytest tests/benchmarks/test_drb_io_contract.py` (failed: `pytest` missing in base env)
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/benchmarks/test_drb_io_contract.py"`
- `docker compose restart backend`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=100 frontend`
- `docker compose logs --tail=100 db`

**Useful logs (excerpt):**
```text
pytest: tests/benchmarks/test_drb_io_contract.py ... [100%]
pytest: 3 passed in 0.02s
backend: Application startup complete.
backend: Uvicorn running on http://0.0.0.0:8000
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 32

## Section 32: Evaluation artifact scaffolding - versioned prompt and report registry

**Single goal:** Add a versioned artifact registry that future advanced evaluators can plug into without schema changes.

**Why:** This keeps v1 evaluation simple while creating compatibility scaffolding for future DeepResearchBench-style expansion without rework.


**Details:**
- Version and persist benchmark evaluation prompt templates.
- Store optional reference-report pointers/versions per dataset/run.
- Attach artifact versions to each run for reproducibility and future evaluator upgrades.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/benchmarks/drb/prompts/` | Versioned evaluation prompt templates. |
| `src/backend/benchmarks/drb/reference_reports/manifest.json` | Optional reference report version manifest. |
| `src/backend/services/benchmark_artifact_registry.py` | Resolve artifact versions for a run. |
| `src/backend/tests/benchmarks/test_benchmark_artifact_registry.py` | Artifact registry/version resolution tests. |

**How to test:** Run artifact registry tests and verify run metadata captures prompt/reference versions.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added versioned DRB prompt artifacts under `benchmarks/drb/prompts/` with a manifest (`default_prompt_version`) and `quality_judge_v1.txt` template.
- Added optional reference report manifest at `benchmarks/drb/reference_reports/manifest.json` to support dataset-level pointers and version placeholders.
- Implemented `BenchmarkArtifactRegistry` to resolve prompt and reference artifacts, including deterministic SHA-256 hashes and run-level override support via `run_metadata.artifact_overrides`.
- Integrated artifact resolution into `BenchmarkRunner` so each new run persists `run_metadata.artifact_versions` for reproducibility, with explicit logs for resolved prompt/reference versions.
- Added `tests/benchmarks/test_benchmark_artifact_registry.py` covering default resolution, run-level override resolution, and benchmark-run metadata persistence.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose exec backend uv run pytest tests/benchmarks/test_benchmark_artifact_registry.py` (failed: `pytest` missing in base env)
- `docker compose exec backend uv run pytest tests/services/test_benchmark_runner.py` (failed: `pytest` missing in base env)
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/benchmarks/test_benchmark_artifact_registry.py"`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/services/test_benchmark_runner.py"`
- `docker compose restart`
- `docker compose ps`
- `docker compose logs --tail=160 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`
- `curl -sS -i http://localhost:8000/api/health`

**Useful logs (excerpt):**
```text
pytest: tests/benchmarks/test_benchmark_artifact_registry.py ... [100%]
pytest: 3 passed in 1.91s
pytest: tests/services/test_benchmark_runner.py .. [100%]
pytest: 2 passed in 1.92s
backend: Benchmark runner resolved artifact versions run_id=<id> dataset_id=<id> prompt_version=v1 reference_version=None
backend: Application startup complete.
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 33

## Section 33: Simple quality evaluator - single-judge correctness profile

**Single goal:** Implement one simple quality evaluator for v1 while preserving extension points for multi-dimension scoring later.

**Why:** This keeps v1 evaluation simple while creating compatibility scaffolding for future DeepResearchBench-style expansion without rework.

**Details:**
- Evaluate each result with one deterministic OpenAI judge rubric and store a normalized `0..1` score.
- Persist an optional `subscores_json` field for future advanced frameworks (e.g., RACE-like dimensions) without enforcing them in v1.
- Use this score as the canonical quality metric for v1 pass/fail.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): use existing OpenAI path via project key.
- Tooling (uv, poetry, Docker): Alembic migration for simple quality score persistence.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_quality_service.py` | Deterministic single-judge quality scoring workflow. |
| `src/backend/models.py` | Add `benchmark_quality_scores` model with optional extension fields. |
| `src/backend/alembic/versions/004_add_benchmark_quality_scores_table.py` | Migration for quality score storage. |
| `src/backend/tests/services/test_benchmark_quality_service.py` | Simple quality scoring tests. |

**How to test:** Run quality tests and verify deterministic score output + persistence.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `BenchmarkQualityScore` ORM model and relationships in `src/backend/models.py` with normalized score storage, pass/fail flag, judge metadata, and optional `subscores_json` extension field for future multi-dimension evaluators.
- Added Alembic migration `004_add_benchmark_quality_scores_table.py` to persist quality scores with constraints: unique per `(run_id, mode, question_id)`, one-to-one with benchmark result, and cascading deletes.
- Implemented `BenchmarkQualityService` in `src/backend/services/benchmark_quality_service.py` with deterministic single-judge prompt workflow using OpenAI model settings (temperature `0`), strict JSON parsing, score normalization (`0..1`), and pass/fail thresholding against benchmark correctness target.
- Added persistence upsert flow in quality service to update/rewrite scores for existing run/mode/question records and log each evaluation + persistence event.
- Added tests in `src/backend/tests/services/test_benchmark_quality_service.py` covering deterministic judge output parsing and persistence/update behavior including optional `subscores_json` handling.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose restart backend`
- `docker compose logs --tail=160 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`
- `docker compose exec backend uv run pytest tests/services/test_benchmark_quality_service.py` (failed: `pytest` missing in default backend env)
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/services/test_benchmark_quality_service.py"`
- `docker compose exec backend uv run alembic current`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=60 frontend`
- `docker compose logs --tail=60 db`

**Useful logs (excerpt):**
```text
alembic: Running upgrade 003_benchmark_results -> 004_benchmark_quality_scores
alembic current: 004_benchmark_quality_scores (head)
pytest: tests/services/test_benchmark_quality_service.py .. [100%]
pytest: 2 passed in 1.26s
backend: Uvicorn running on http://0.0.0.0:8000
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 34

## Section 34: Simple citation evaluator - citation presence and support checks

**Single goal:** Implement a lightweight citation quality evaluator for v1 with schema hooks for future FACT-style expansion.

**Why:** This keeps v1 evaluation simple while creating compatibility scaffolding for future DeepResearchBench-style expansion without rework.


**Details:**
- Compute v1 citation metrics: `citation_presence_rate` and `basic_support_rate` using retrieved context checks.
- Persist per-citation verification records in a generic structure reusable by future FACT-style claim-level evaluators.
- Keep evaluation deterministic and low-cost for manual benchmark runs.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration for citation evaluation outputs.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_citation_service.py` | Basic citation extraction and support verification workflow. |
| `src/backend/models.py` | Add `benchmark_citation_scores` and per-citation verification model(s). |
| `src/backend/alembic/versions/005_add_benchmark_citation_tables.py` | Migration for citation score storage tables. |
| `src/backend/tests/services/test_benchmark_citation_service.py` | Citation metric and verification tests. |

**How to test:** Run citation tests and validate presence/support calculations.

**Test results:** (Add when section is complete.)
- Pending.

---

**Completion notes:**
- Added deterministic citation evaluator service in `src/backend/services/benchmark_citation_service.py` that extracts bracket citations (e.g. `[1]`), computes `citation_presence_rate`, and performs low-cost lexical overlap checks for `basic_support_rate`.
- Added reusable per-citation verification persistence with support labels (`supported`, `unsupported`, `missing_context`) and generic JSON payload hooks for future FACT-style evaluators.
- Extended ORM models with `BenchmarkCitationScore` and `BenchmarkCitationVerification` plus run/result relationships for one score per result and many verifications per score.
- Added Alembic migration `005_add_benchmark_citation_tables.py` to create citation score and verification tables with indexes and cascade FKs.
- Added service tests in `tests/services/test_benchmark_citation_service.py` covering deterministic metric calculation and replacement of old verification rows on rescore.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose exec backend uv run alembic upgrade head`
- `docker compose exec backend uv run --with pytest pytest tests/services/test_benchmark_citation_service.py` (initial failure fixed in service flush order)
- `docker compose exec backend uv run --with pytest pytest tests/services/test_benchmark_citation_service.py`
- `docker compose restart backend`
- `docker compose ps`
- `docker compose logs --tail=160 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`
- `docker compose exec backend uv run alembic current`
- `curl -sS -i http://localhost:8000/api/health`

**Useful logs (excerpt):**
```text
alembic: Running upgrade 004_benchmark_quality_scores -> 005_benchmark_citation_tables
pytest: tests/services/test_benchmark_citation_service.py .. [100%]
pytest: 2 passed in 0.78s
alembic current: 005_benchmark_citation_tables (head)
health: HTTP/1.1 200 OK {"status":"ok"}
backend: Application startup complete.
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 35

## Section 35: Advanced evaluator scaffolding docs - deferred DRB parity path

**Single goal:** Document and scaffold the upgrade path from simple v1 evaluators to full DRB-style parity later.

**Why:** This keeps v1 evaluation simple while creating compatibility scaffolding for future DeepResearchBench-style expansion without rework.


**Details:**
- Add explicit deferred-scope docs for future RACE/FACT-equivalent evaluators and pairwise/multi-judge expansion.
- Provide stub interfaces and TODO markers so advanced evaluators can be added without changing existing run APIs.
- Add one smoke parity check that validates export shape only (not full evaluator parity).

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `docs/benchmark/ADVANCED_EVALUATION_PLAN.md` | Deferred roadmap for DRB-style advanced evaluators. |
| `src/backend/benchmarks/drb/parity_runner.py` | Export-shape parity runner stub for future expansion. |
| `src/backend/tests/e2e/test_drb_export_parity_smoke.py` | Smoke test for DRB-inspired export compatibility. |

**How to test:** Run export parity smoke test and verify documented deferred-scope checklist exists.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added deferred roadmap in `docs/benchmark/ADVANCED_EVALUATION_PLAN.md` with explicit future scope for RACE/FACT-equivalent evaluators, pairwise/multi-judge expansion, and a checklist for additive rollout.
- Implemented `benchmarks.drb.parity_runner` scaffold that reuses the existing DRB export contract, validates required export fields only (`id`, `prompt`, `article`), and logs parity smoke execution start/finish.
- Added `DRBAdvancedEvaluator` protocol plus deferred runner hook and TODO markers so advanced evaluators can be introduced without changing benchmark run APIs.
- Added `tests/e2e/test_drb_export_parity_smoke.py` to assert export-shape parity behavior and parity smoke logging.
- Updated `benchmarks.drb.__init__` exports to expose parity smoke and deferred evaluator hooks.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose ps`
- `docker compose exec backend uv run --with pytest pytest tests/e2e/test_drb_export_parity_smoke.py`
- `docker compose restart backend`
- `rg -n "Deferred implementation checklist|RACE|FACT|pairwise|multi-judge" docs/benchmark/ADVANCED_EVALUATION_PLAN.md`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/e2e/test_drb_export_parity_smoke.py . [100%]
pytest: 1 passed in 0.02s
health: HTTP/1.1 200 OK {"status":"ok"}
backend: Application startup complete.
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 36

## Section 36: Quality evaluator pipeline wiring - run-time integration

**Single goal:** Wire the simple quality evaluator into benchmark execution so each completed result is automatically scored.

**Why:** This keeps v1 evaluation simple while creating compatibility scaffolding for future DeepResearchBench-style expansion without rework.


**Details:**
- Invoke `benchmark_quality_service` as a post-processing step in benchmark runner/job flow.
- Persist quality score linkage to `(run_id, mode, question_id)` and expose score in run detail API payloads.
- Ensure failures in quality scoring are captured as non-fatal evaluation errors, not execution crashes.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_runner.py` | Call quality evaluator after each answer result is persisted. |
| `src/backend/services/benchmark_jobs.py` | Ensure job lifecycle includes evaluation stage updates. |
| `src/backend/routers/benchmarks.py` | Expose quality score fields in run detail responses. |
| `src/backend/tests/services/test_benchmark_runner.py` | Validate quality scoring integration and error handling. |
| `src/backend/tests/api/test_benchmark_runs_api.py` | Verify score visibility in API responses. |

**How to test:** Run benchmark runner/API tests and confirm scored outputs appear for completed results.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Wired `BenchmarkQualityService` into `BenchmarkRunner` so each successful persisted result is quality-scored immediately after save.
- Added non-fatal quality error capture in run metadata (`run_metadata.evaluation_errors[]`) keyed by mode/question; execution continues and run can still complete.
- Added progress callback emission for quality evaluation start/success/failure and hooked benchmark jobs to update lifecycle messages and logs during evaluation stages.
- Extended benchmark run-detail schema payload with `results[]` entries including per-result `quality` block (`score`, `passed`, `rubric_version`, `judge_model`, `subscores`, `error`).
- Expanded tests to validate quality persistence linkage, API response visibility, and non-fatal evaluator failure behavior.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose restart backend`
- `docker compose exec backend uv pip install pytest`
- `docker compose exec backend uv run pytest tests/services/test_benchmark_runner.py tests/api/test_benchmark_runs_api.py`
- `docker compose exec backend uv run pytest tests/contracts/test_public_contracts.py`
- `docker compose logs --no-color --tail=200 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 db`
- `docker compose ps`

**Useful logs (excerpt):**
```text
pytest: tests/services/test_benchmark_runner.py ... [ 33%]
pytest: tests/api/test_benchmark_runs_api.py ...... [100%]
pytest: 9 passed in 1.83s
pytest: tests/contracts/test_public_contracts.py ........ [100%]
pytest: 8 passed in 1.51s
backend: Application startup complete.
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 37

## Section 37: Latency instrumentation - end-to-end and stage timings

**Single goal:** Capture per-result end-to-end and stage-level latency.

**Why:** This turns raw benchmark data into actionable metrics, operator controls, and frontend visibility for real product usage.


**Details:**
- Persist e2e latency and optional stage timing blocks.
- Distinguish timeout/cancel timing outcomes.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration if new fields/tables required.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_runner.py` | Timing checkpoint instrumentation. |
| `src/backend/models.py` | Timing model/fields. |
| `src/backend/alembic/versions/006_add_benchmark_timing_fields.py` | Timing migration. |
| `src/backend/tests/services/test_benchmark_latency_capture.py` | Timing tests. |

**How to test:** Run timing tests and verify DB timing fields after run.

**Test results:** (Add when section is complete.)
- Pending.

---


**Completion notes:**
- Added benchmark timing persistence fields on `benchmark_results`: `e2e_latency_ms`, `stage_timings` (JSONB), and `timing_outcome`.
- Added Alembic migration `006_benchmark_timing_fields` and applied it to `head`.
- Instrumented benchmark runner checkpoints for runtime execution, result persistence, and quality evaluation timing.
- Added timing outcome classification (`completed`, `timeout`, `cancelled`, `error`) from execution outcomes and persisted per result.
- Added dedicated latency tests in `tests/services/test_benchmark_latency_capture.py` covering e2e/stage timings and timeout/cancel classification.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose exec backend uv run alembic upgrade head`
- `docker compose exec backend uv run --with pytest pytest tests/services/test_benchmark_latency_capture.py tests/services/test_benchmark_runner.py`
- `docker compose exec backend uv run --with pytest pytest tests/db/test_benchmark_results_schema.py`
- `docker compose restart backend`
- `docker compose ps`
- `docker compose logs --tail=140 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose exec db psql -U agent_user -d agent_search -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='benchmark_results' AND column_name IN ('e2e_latency_ms','stage_timings','timing_outcome','latency_ms') ORDER BY column_name;"`
- `docker compose exec db psql -U agent_user -d agent_search -c "SELECT run_id, mode, question_id, e2e_latency_ms, timing_outcome, stage_timings FROM benchmark_results WHERE run_id LIKE 'run-benchmark-latency-%' OR run_id LIKE 'run-benchmark-timeout-%' OR run_id LIKE 'run-benchmark-cancel-%' ORDER BY created_at DESC LIMIT 5;"`

**Useful logs (excerpt):**
```text
alembic: Running upgrade 005_benchmark_citation_tables -> 006_benchmark_timing_fields
pytest: tests/services/test_benchmark_latency_capture.py ..
pytest: tests/services/test_benchmark_runner.py ...
pytest: 5 passed in 1.73s
pytest: tests/db/test_benchmark_results_schema.py ..
pytest: 2 passed in 0.89s
backend: Application startup complete.
health: HTTP/1.1 200 OK {"status":"ok"}
db columns: e2e_latency_ms (integer), stage_timings (jsonb), timing_outcome (character varying), latency_ms (integer)
db sample rows:
  run-benchmark-latency-... timing_outcome=completed stage_timings={"persist_result_ms": 1, "runtime_execution_ms": 0, "quality_evaluation_ms": 0}
  run-benchmark-timeout-... timing_outcome=timeout stage_timings={"persist_result_ms": 1, "runtime_execution_ms": 0}
  run-benchmark-cancel-... timing_outcome=cancelled stage_timings={"persist_result_ms": 0, "runtime_execution_ms": 0}
```

## Completed - 2026-03-09 - Section 38

## Section 38: Retrieval diagnostics - benchmark retrieval quality signals

**Single goal:** Add retrieval diagnostics for failure analysis.

**Why:** This turns raw benchmark data into actionable metrics, operator controls, and frontend visibility for real product usage.


**Details:**
- Persist `recall@k`, `mrr`, `ndcg`, and retrieved IDs where labels allow.
- Expose diagnostics in run detail payloads.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/models.py` | `benchmark_retrieval_metrics` model. |
| `src/backend/alembic/versions/007_add_benchmark_retrieval_metrics_table.py` | Migration file. |
| `src/backend/services/benchmark_retrieval_metrics_service.py` | Metrics service. |
| `src/backend/tests/services/test_benchmark_retrieval_metrics_service.py` | Retrieval diagnostics tests. |

**How to test:** Run retrieval diagnostics tests and inspect saved metrics.

**Test results:** (Add when section is complete.)
- Pending.

---

**Completion notes:**
- Added `BenchmarkRetrievalMetric` ORM model and relationships from `BenchmarkRun` + `BenchmarkResult`.
- Added Alembic migration `007_benchmark_retrieval_metrics` creating `benchmark_retrieval_metrics` with uniqueness constraints and indexes.
- Implemented `BenchmarkRetrievalMetricsService` to compute/persist `recall@k`, `mrr`, `ndcg`, retrieved ids, relevant ids, and label source.
- Wired retrieval diagnostics into benchmark execution flow (`BenchmarkRunner`) so each persisted benchmark result gets retrieval diagnostics recorded.
- Extended run detail payload results with `retrieval` diagnostics block via `BenchmarkResultRetrievalDiagnostics` and `benchmark_jobs.get_benchmark_run_status`.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose restart backend`
- `docker compose ps`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=60 frontend`
- `docker compose logs --tail=60 db`
- `docker compose exec backend uv run --with pytest pytest tests/services/test_benchmark_retrieval_metrics_service.py tests/api/test_benchmark_runs_api.py`
- `docker compose exec backend uv run alembic current`
- `docker compose exec db psql -U agent_user -d agent_search -c "\\dt benchmark_*"`
- `docker compose exec db psql -U agent_user -d agent_search -c "SELECT run_id, mode, question_id, recall_at_k, mrr, ndcg, k, label_source, retrieved_document_ids, relevant_document_ids FROM benchmark_retrieval_metrics ORDER BY created_at DESC LIMIT 5;"`

**Useful logs (excerpt):**
```text
alembic: Running upgrade 006_benchmark_timing_fields -> 007_benchmark_retrieval_metrics
pytest: tests/services/test_benchmark_retrieval_metrics_service.py ...
pytest: tests/api/test_benchmark_runs_api.py ......
pytest: 9 passed in 1.73s
alembic current: 007_benchmark_retrieval_metrics (head)
psql \dt: benchmark_retrieval_metrics table present
db sample rows:
  run-retrieval-unlabeled-... DRB-002 recall_at_k=NULL mrr=NULL ndcg=NULL k=5 label_source=NULL retrieved=["doc-a","doc-b","doc-c"] relevant=[]
  run-retrieval-... DRB-001 recall_at_k=1 mrr=1 ndcg=1 k=1 label_source=manual retrieved=["doc-x","doc-gold","doc-y"] relevant=["doc-x"]
backend: Application startup complete.
frontend: VITE v5.4.21 ready.
db: database system is ready to accept connections.
```

## Completed - 2026-03-09 - Section 39

## Section 39: Benchmark aggregation service - run and mode summaries

**Single goal:** Compute run-level and mode-level summary metrics.

**Why:** This turns raw benchmark data into actionable metrics, operator controls, and frontend visibility for real product usage.


**Details:**
- Aggregate correctness and latency percentiles.
- Produce deterministic pass/fail summaries.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_metrics_service.py` | Aggregation logic. |
| `src/backend/services/benchmark_summary_service.py` | Summary payload assembly. |
| `src/backend/tests/services/test_benchmark_metrics_service.py` | Aggregation tests. |

**How to test:** Run metric aggregation tests and SQL spot checks.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `BenchmarkMetricsService` with deterministic run/mode aggregation for `correctness_rate`, `avg_latency_ms`, and nearest-rank `p95_latency_ms`, plus deterministic pass/fail gating against run SLO thresholds.
- Added `BenchmarkSummaryService` to assemble run-level and mode-level summary bundles from DB rows, including internal `run_passed` and per-mode pass/fail map for operator visibility.
- Refactored `get_benchmark_run_status` in `benchmark_jobs.py` to consume the new summary service rather than inline aggregation logic, preserving existing API response shape while improving metric quality.
- Added service tests in `tests/services/test_benchmark_metrics_service.py` covering percentile math, missing-signal fail behavior, and DB-backed mode/run summary assembly.
- Added log visibility in aggregation/status paths (`threshold resolution`, `metric aggregates`, `summary assembly`, and `run_passed/mode_pass_fail` in status resolution logs).

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose exec backend uv run --with pytest pytest tests/services/test_benchmark_metrics_service.py tests/api/test_benchmark_runs_api.py`
- `docker compose exec db psql -U agent_user -d agent_search -c "SELECT mode, COUNT(*) AS total, COUNT(*) FILTER (WHERE execution_error IS NULL) AS completed, ROUND(AVG(latency_ms)::numeric, 2) AS avg_latency_ms, ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)::numeric, 2) AS p95_latency_ms FROM benchmark_results GROUP BY mode ORDER BY mode;"`
- `docker compose restart backend`
- `docker compose ps`
- `docker compose logs --tail=160 backend`
- `docker compose logs --tail=80 frontend`
- `docker compose logs --tail=80 db`
- `curl -sS -i http://localhost:8000/api/health`

**Useful logs (excerpt):**
```text
pytest: tests/services/test_benchmark_metrics_service.py ...
pytest: tests/api/test_benchmark_runs_api.py ......
pytest: 9 passed in 1.75s

sql spot-check:
mode               | total | completed | avg_latency_ms | p95_latency_ms
agentic_default    | 4     | 4         | 140.00         | 180.00
agentic_no_rerank  | 2     | 2         | 260.00         | 260.00

backend: Application startup complete.
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
health: HTTP/1.1 200 OK {"status":"ok"}
```

## Completed - 2026-03-09 - Section 40

## Section 40: Benchmark compare API - mode delta endpoint

**Single goal:** Add run-level mode comparison endpoint.

**Why:** This turns raw benchmark data into actionable metrics, operator controls, and frontend visibility for real product usage.


**Details:**
- Endpoint: `GET /api/benchmarks/runs/{run_id}/compare`.
- Report correctness and p95 latency deltas vs baseline mode.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/routers/benchmarks.py` | Compare endpoint. |
| `src/backend/schemas/benchmark.py` | Compare response models. |
| `src/backend/tests/api/test_benchmark_compare_api.py` | Compare API tests. |

**How to test:** Run compare API tests.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added compare response schemas: `BenchmarkModeComparison` and `BenchmarkRunCompareResponse`.
- Added `GET /api/benchmarks/runs/{run_id}/compare` route that reuses `get_benchmark_run_status` summaries, validates baseline mode presence, and computes correctness/p95 deltas per mode.
- Added router-level visibility logs for compare request, baseline-missing warning, and successful compare resolution.
- Added API tests for success shape/deltas, missing run (404), and missing baseline summary (400).

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose exec backend uv run --with pytest pytest tests/api/test_benchmark_compare_api.py`
- `docker compose restart backend`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `curl -sS -i http://localhost:8000/api/benchmarks/runs/nonexistent/compare`
- `docker compose logs --tail=80 backend`
- `docker compose logs --tail=40 frontend`
- `docker compose logs --tail=40 db`

**Useful logs (excerpt):**
```text
pytest: tests/api/test_benchmark_compare_api.py ...
pytest: 3 passed in 1.62s

health: HTTP/1.1 200 OK
{"status":"ok"}

compare probe: HTTP/1.1 404 Not Found
{"detail":"Benchmark run not found."}

backend: Benchmarks router compare requested run_id=nonexistent
backend: GET /api/benchmarks/runs/nonexistent/compare HTTP/1.1" 404 Not Found
frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 41

## Section 41: Benchmark admin controls - benchmark-only wipe and retention

**Single goal:** Add safe benchmark maintenance controls.

**Why:** This turns raw benchmark data into actionable metrics, operator controls, and frontend visibility for real product usage.


**Details:**
- Add benchmark-only wipe endpoint/utility.
- Add retention command for old benchmark runs.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/common/db/benchmark_wipe.py` | Benchmark-only cleanup utility. |
| `src/backend/benchmarks/retention.py` | Retention command utility. |
| `src/backend/tests/db/test_benchmark_wipe.py` | Cleanup safety tests. |

**How to test:** Run cleanup tests and verify non-benchmark tables untouched.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `wipe_all_benchmark_data` in `common/db/benchmark_wipe.py` with safe benchmark-table-only deletion and explicit logging for both PostgreSQL (`TRUNCATE ... CASCADE`) and SQLite test paths.
- Added retention utility/command in `benchmarks/retention.py`:
  - `purge_old_benchmark_runs(...)` for age/status filtered cleanup with dry-run support.
  - CLI entrypoint with flags: `--older-than-days`, `--status`, `--limit`, `--dry-run`.
- Added benchmark admin endpoint `POST /api/benchmarks/wipe` with commit/rollback safety and visibility logs.
- Added `BenchmarkWipeResponse` schema and exports.
- Added API tests for wipe endpoint success/failure shape and DB tests verifying benchmark cleanup + retention do not affect internal tables.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose restart backend`
- `docker compose exec backend uv run --with pytest pytest tests/db/test_benchmark_wipe.py tests/api/test_benchmark_runs_api.py`
- `curl -sS -i http://localhost:8000/api/health`
- `curl -sS -i -X POST http://localhost:8000/api/benchmarks/wipe`
- `docker compose exec backend uv run python benchmarks/retention.py --dry-run --older-than-days 1`
- `docker compose ps`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=60 frontend`
- `docker compose logs --tail=80 db`

**Useful logs (excerpt):**
```text
pytest: tests/db/test_benchmark_wipe.py ..
pytest: tests/api/test_benchmark_runs_api.py ........
pytest: 10 passed in 1.81s

health: HTTP/1.1 200 OK
{"status":"ok"}

benchmark wipe: HTTP/1.1 200 OK
{"status":"success","message":"All benchmark run data removed.","deleted_runs":0}

retention dry-run:
benchmark_retention candidate_runs=0 deleted_runs=0 dry_run=True cutoff_utc=2026-03-08T19:40:38.283843+00:00 statuses=completed,failed,cancelled limit=None

backend:
Benchmarks router wipe requested
Wiped benchmark data via TRUNCATE deleted_runs=0
Benchmarks router wipe completed deleted_runs=0

frontend: VITE v5.4.21 ready
db: database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 42

## Section 42: Manual benchmark operator CLI - run and export

**Single goal:** Provide CLI commands for manual benchmark runs and artifact export.

**Why:** This turns raw benchmark data into actionable metrics, operator controls, and frontend visibility for real product usage.


**Details:**
- Add run command with dataset/mode flags.
- Add export command for JSON results.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): optional `typer`; argparse acceptable.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/benchmarks/run.py` | Benchmark run CLI entrypoint. |
| `src/backend/benchmarks/export.py` | Benchmark export CLI entrypoint. |
| `README.md` | CLI usage documentation. |

**How to test:** Run CLI help and manual smoke run/export.

**Test results:** (Add when section is complete.)
- Completed.

---

**Completion notes:**
- Added `benchmarks/run.py` argparse CLI with required `--dataset-id` and repeatable `--mode` flags, plus optional `--run-id`, `--metadata key=value`, `--max-questions` (subset/smoke support), model/vector-store overrides, and `--dry-run` planning output.
- Reused existing runtime services (`BenchmarkRunner`, `get_vector_store`, `get_embedding_model`, `ChatOpenAI`) so CLI executes the same benchmark pipeline and persistence contracts as API jobs.
- Added `benchmarks/export.py` argparse CLI that exports benchmark artifacts to JSON by `--run-id` or latest run, including run metadata, status summary, and raw persisted result rows.
- Added explicit operator visibility logs for CLI request/execute/complete stages in both commands.
- Updated README with backend-container command examples for benchmark run and export workflows.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose exec backend uv run python benchmarks/run.py --help`
- `docker compose exec backend uv run python benchmarks/export.py --help`
- `docker compose exec backend uv run python benchmarks/run.py --dataset-id internal_v1 --mode baseline_retrieve_then_answer --max-questions 1 --metadata operator=manual_cli_smoke --metadata section=42`
- `docker compose exec backend uv run python benchmarks/export.py --run-id benchmark-run-eb45ac1f-93e8-44a3-99d1-11bf5bba182a --output benchmarks/exports/section42-smoke.json`
- `docker compose restart backend`
- `docker compose ps`
- `docker compose logs --no-color --tail=120 backend`
- `docker compose logs --no-color --tail=80 frontend`
- `docker compose logs --no-color --tail=80 db`
- `curl -sS http://localhost:8000/api/health`

**Useful logs (excerpt):**
```text
run.py --help:
usage: run.py [-h] --dataset-id DATASET_ID --mode {baseline_retrieve_then_answer,agentic_default,agentic_no_rerank,agentic_single_query_no_decompose} ...

export.py --help:
usage: export.py [-h] [--run-id RUN_ID] [--output OUTPUT]

run smoke summary:
{"completed_results": 1, "dataset_id": "internal_v1__subset_1", "mode_count": 1, "question_count": 1, "run_id": "benchmark-run-eb45ac1f-93e8-44a3-99d1-11bf5bba182a", "selected_question_count": 1, "source_dataset_id": "internal_v1"}

export smoke summary:
{"mode_count": 1, "output_path": "benchmarks/exports/section42-smoke.json", "result_count": 1, "run_id": "benchmark-run-eb45ac1f-93e8-44a3-99d1-11bf5bba182a", "status": "completed"}

backend:
Benchmark run cli completed run_id=benchmark-run-eb45ac1f-93e8-44a3-99d1-11bf5bba182a dataset_id=internal_v1__subset_1 completed_results=1
Benchmark export cli wrote JSON run_id=benchmark-run-eb45ac1f-93e8-44a3-99d1-11bf5bba182a output_path=benchmarks/exports/section42-smoke.json mode_count=1 result_count=1

health:
{"status":"ok"}
```

## Completed - 2026-03-09 - Section 43

## Section 43: Frontend benchmark run list - historical visibility

**Single goal:** Add frontend run-list view for benchmark history and KPIs.

**Why:** This turns raw benchmark data into actionable metrics, operator controls, and frontend visibility for real product usage.


**Details:**
- Show status, dataset, modes, correctness, p95 latency, start time, duration.
- Display pass/fail badge from threshold contract.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/components/BenchmarkRunList.tsx` | Run history table view. |
| `src/frontend/src/utils/api.ts` | Run list API client/types. |
| `src/frontend/src/App.tsx` | Run list integration. |
| `src/frontend/src/components/BenchmarkRunList.test.tsx` | Run list UI tests. |

**How to test:** Run frontend typecheck/tests and manual UI check.

**Test results:**
- Completed.

---

**Completion notes:**
- Added `BenchmarkRunList` React component with a run-history table showing status, dataset, modes, correctness, p95 latency, start time, duration, and threshold pass/fail badge.
- Implemented frontend KPI enrichment by combining `/api/benchmarks/runs` with per-run `/api/benchmarks/runs/{run_id}` calls.
- Implemented deterministic pass/fail evaluation in the UI using threshold contract (`targets` fallback to `objective.targets`) and computed correctness/p95 from result rows.
- Added explicit frontend visibility logs (`console.info`, `console.warn`, `console.error`) for benchmark history refresh lifecycle and enrichment failures.
- Extended frontend API client (`utils/api.ts`) with benchmark list/status types, validators, and fetch functions.
- Integrated the new run-list view into `App.tsx` and fixed a strict type issue in async run success fallback payload (`final_citations: []`).
- Added focused component tests for successful run-list rendering and HTTP failure handling.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose exec frontend npm run test`
- `docker compose exec frontend npm run typecheck`
- `docker compose exec frontend npm run build`
- `docker compose restart frontend`
- `docker compose ps`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 backend`
- `docker compose logs --tail=120 db`
- `curl -sS -i http://localhost:8000/api/benchmarks/runs`
- `curl -sS -I http://localhost:5173/`

**Useful logs (excerpt):**
```text
frontend tests:
Test Files  2 passed (2)
Tests      10 passed (10)

frontend typecheck:
> tsc --noEmit

frontend build:
✓ built in 597ms

docker compose ps:
backend   Up
frontend  Up
db        Up (healthy)

backend API checks:
GET /api/health -> HTTP/1.1 200 OK {"status":"ok"}
GET /api/benchmarks/runs -> HTTP/1.1 200 OK {"runs":[]}

frontend logs:
VITE v5.4.21 ready in 318 ms
Local: http://localhost:5173/
```

## Completed - 2026-03-09 - Section 44

## Section 44: Frontend benchmark detail view - per-mode and per-question insights

**Single goal:** Add run detail UI with mode deltas and question-level outcomes.

**Why:** This turns raw benchmark data into actionable metrics, operator controls, and frontend visibility for real product usage.


**Details:**
- Show mode scorecards and compare deltas.
- Show question rows with correctness, latency, and error status.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/components/BenchmarkRunDetail.tsx` | Benchmark run detail view. |
| `src/frontend/src/utils/api.ts` | Detail/compare API client methods. |
| `src/frontend/src/components/BenchmarkRunDetail.test.tsx` | Detail view tests. |

**How to test:** Run frontend tests and manual detail page check.

**Test results:**
- Completed.

---

**Completion notes:**
- Added `BenchmarkRunDetail` component with run-id driven loading flow, explicit lifecycle logs, mode scorecard rendering, and question-level outcome rows.
- Added benchmark compare API client contract support in `utils/api.ts` (`BenchmarkRunCompareResponse`, `BenchmarkModeComparison`, `getBenchmarkRunCompare`) with runtime shape validation.
- Wired detail view into `App.tsx` below the run history list.
- Extended shared styles for detail form input + layout classes while reusing benchmark table styles.
- Added focused component tests for successful detail rendering (mode deltas + per-question correctness/latency/error) and failure handling.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose logs --no-color --tail=120 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 db`
- `docker compose restart frontend`
- `docker compose ps`
- `docker compose exec frontend npm run test -- src/components/BenchmarkRunDetail.test.tsx`
- `docker compose exec frontend npm run test`
- `docker compose exec frontend npm run typecheck`
- `docker compose exec frontend npm run build`
- `curl -sS http://localhost:5173`
- `curl -sS http://localhost:8000/api/health`
- `curl -sS http://localhost:8000/api/benchmarks/runs`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 backend`
- `docker compose logs --no-color --tail=120 db`

**Useful logs (excerpt):**
```text
BenchmarkRunDetail test:
Benchmark run detail load started. { runId: 'run-42' }
Benchmark run detail load completed. { runId: 'run-42', modeCount: 2, resultCount: 2 }
Benchmark run detail load failed. {
  runId: 'missing-run',
  statusError: { type: 'http', message: 'Request failed with status 404' },
  compareError: { type: 'http', message: 'Request failed with status 404' }
}

frontend test suite:
Test Files  3 passed (3)
Tests      12 passed (12)

frontend typecheck:
> tsc --noEmit

frontend build:
✓ built in 829ms

runtime checks:
frontend_status=200
health_status=200
runs_status=200

backend logs:
GET /api/health HTTP/1.1 200 OK
Benchmarks router list requested
Benchmark runs listed count=0
GET /api/benchmarks/runs HTTP/1.1 200 OK
```

## Completed - 2026-03-09 - Section 45

## Section 45: OpenAPI synchronization - canonical contract refresh (final)

**Single goal:** Regenerate and commit final OpenAPI after both SDK and benchmark routes are in place.

**Why:** This synchronizes generated artifacts and release/CI safeguards so the integrated system remains consistent over time.


**Details:**
- Ensure agent async/sync and benchmark endpoints are present.
- Avoid intermediate spec churn before final endpoint set stabilizes.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): use existing OpenAPI export workflow.

**Files and purpose**

| File | Purpose |
|------|--------|
| `openapi.json` | Final canonical OpenAPI artifact. |
| `scripts/export_openapi.py` | Spec generation utility. |

**How to test:** Regenerate spec and verify path inventory includes benchmark + agent routes.

**Test results:**
- Completed.

---

**Completion notes:**
- Regenerated `openapi.json` from the running FastAPI app in the backend container (`uv run` runtime) so the canonical spec reflects the final integrated routes and schemas.
- Verified path inventory includes agent sync/async lifecycle endpoints and benchmark run/list/detail/cancel/compare/wipe endpoints.
- Ran OpenAPI validation with `scripts/validate_openapi.sh` to confirm schema consistency.
- Restarted all services post-update and re-checked backend/frontend/db logs plus health for runtime visibility.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs --no-color --tail=120 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 db`
- `curl -sS http://localhost:8000/api/health`
- `docker compose exec -T backend sh -lc 'uv run python - <<"PY" ... app.openapi() ... PY' > openapi.json`
- `python3 - <<"PY" ... verify required OpenAPI paths ... PY`
- `./scripts/validate_openapi.sh openapi.json`
- `docker compose restart`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --no-color --tail=120 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 db`

**Useful logs (excerpt):**
```text
OpenAPI route verification:
path_count=16
missing_required_paths=[]

OpenAPI validator:
INFO validate_openapi: starting validation spec=/Users/nickbohm/Desktop/tinkering/agent-search/openapi.json
No validation issues detected.
INFO validate_openapi: validation passed spec=/Users/nickbohm/Desktop/tinkering/agent-search/openapi.json

docker compose ps (post-restart):
backend   Up
frontend  Up
db        Up (healthy)

health check:
HTTP/1.1 200 OK
{"status":"ok"}

backend log excerpt:
Uvicorn running on http://0.0.0.0:8000
GET /api/health HTTP/1.1 200 OK

frontend log excerpt:
VITE v5.4.21 ready
Local: http://localhost:5173/

DB log excerpt:
database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 46

## Section 46: Generated HTTP client refresh - post-contract artifact alignment

**Single goal:** Regenerate Python OpenAPI client from final spec.

**Why:** This synchronizes generated artifacts and release/CI safeguards so the integrated system remains consistent over time.


**Details:**
- Refresh generated methods/models including benchmark endpoints.
- Keep generated client secondary to in-process SDK.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new runtime dependencies.
- Tooling (uv, poetry, Docker): use existing generation scripts.

**Files and purpose**

| File | Purpose |
|------|--------|
| `sdk/python/openapi_client/**` | Refreshed generated client code. |
| `sdk/python/docs/**` | Refreshed generated docs. |
| `sdk/README.md` | Artifact role clarification. |

**How to test:** Regenerate and verify benchmark endpoints in generated classes.

**Test results:**
- Completed.

---

**Completion notes:**
- Regenerated Python SDK artifacts using existing generator workflow (`./scripts/generate_sdk.sh`) against the current canonical `openapi.json`.
- Verified benchmark endpoints now exist in generated classes/docs (`BenchmarksApi` with create/list/get/cancel/compare/wipe methods).
- Clarified SDK role in `sdk/README.md`: generated HTTP client is secondary to in-process `agent_search` SDK.
- Restarted the full Docker stack and re-checked backend/frontend/db logs and runtime health endpoints.

**Commands run:**
- `./scripts/update_sdk.sh` (failed on host uv platform mismatch)
- `./scripts/generate_sdk.sh`
- `rg -n "class BenchmarksApi|def .*benchmark|/api/benchmarks" sdk/python/openapi_client/api/benchmarks_api.py sdk/python/docs/BenchmarksApi.md`
- `test -f sdk/python/openapi_client/api/benchmarks_api.py && test -f sdk/python/docs/BenchmarksApi.md && rg -n "create_benchmark_run_api_benchmarks_runs_post|list_runs_api_benchmarks_runs_get|get_run_api_benchmarks_runs_run_id_get|cancel_run_api_benchmarks_runs_run_id_cancel_post|compare_run_modes_api_benchmarks_runs_run_id_compare_get|wipe_benchmark_data_api_benchmarks_wipe_post" sdk/python/openapi_client/api/benchmarks_api.py sdk/python/docs/BenchmarksApi.md`
- `docker compose restart`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `curl -sS -i http://localhost:8000/api/benchmarks/runs`
- `docker compose logs --no-color --tail=120 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 db`

**Useful logs (excerpt):**
```text
sdk generation:
INFO generate_sdk: starting image=openapitools/openapi-generator-cli lang=python spec=/Users/nickbohm/Desktop/tinkering/agent-search/openapi.json output=/Users/nickbohm/Desktop/tinkering/agent-search/sdk/python
writing file /local/sdk/python/openapi_client/api/benchmarks_api.py
writing file /local/sdk/python/docs/BenchmarksApi.md
INFO generate_sdk: generation complete

benchmark endpoint verification:
BenchmarksApi.md includes:
- POST /api/benchmarks/runs
- GET /api/benchmarks/runs
- GET /api/benchmarks/runs/{run_id}
- POST /api/benchmarks/runs/{run_id}/cancel
- GET /api/benchmarks/runs/{run_id}/compare
- POST /api/benchmarks/wipe

post-restart runtime checks:
HTTP/1.1 200 OK /api/health -> {"status":"ok"}
HTTP/1.1 200 OK /api/benchmarks/runs -> {"runs":[]}

backend logs:
Uvicorn running on http://0.0.0.0:8000
Application startup complete.

frontend logs:
VITE v5.4.21 ready
Local: http://localhost:5173/

db logs:
database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 47

## Section 47: SDK packaging workspace - distributable boundary

**Single goal:** Create dedicated package workspace for core in-process SDK distribution.

**Why:** This synchronizes generated artifacts and release/CI safeguards so the integrated system remains consistent over time.


**Details:**
- Separate SDK package metadata from backend app packaging.
- Exclude backend-only web/db dependencies from SDK package.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): packaging metadata updates.
- Tooling (uv, poetry, Docker): add package build commands for SDK workspace.

**Files and purpose**

| File | Purpose |
|------|--------|
| `sdk/core/pyproject.toml` | Core SDK package metadata. |
| `sdk/core/README.md` | Package-local long description source. |
| `sdk/core/src/agent_search/__init__.py` | SDK package root. |

**How to test:** Build wheel/sdist and inspect dependency boundary.

**Test results:**
- Completed.

---

**Completion notes:**
- Added a dedicated package workspace at `sdk/core` with standalone build metadata (`hatchling`, src-layout package target) separate from backend app packaging.
- Added package-local documentation in `sdk/core/README.md` with explicit build steps and dependency-boundary expectations.
- Added `sdk/core/src/agent_search/__init__.py` as the package root with version export support for distributable artifacts.
- Built both sdist and wheel from the new workspace and validated `Requires-Dist` entries exclude backend-only web/DB dependencies.
- Restarted all services and verified backend/frontend/db logs and health endpoints after completion.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --tail=120 db backend frontend`
- `cd sdk/core && python3 -m build`
- `cd sdk/core && python3 - <<'PY' ... inspect wheel METADATA Requires-Dist ... PY`
- `docker compose restart`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `curl -sS -o /tmp/frontend_body.txt -w 'frontend_status=%{http_code}\\n' http://localhost:5173 && head -n 5 /tmp/frontend_body.txt`
- `docker compose logs --no-color --tail=120 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 db`

**Useful logs (excerpt):**
```text
sdk/core build:
Successfully built agent_search_core-0.1.0.tar.gz and agent_search_core-0.1.0-py3-none-any.whl

wheel metadata dependency boundary:
requires_dist= ['flashrank>=0.2.10', 'langchain-classic>=1.0.0', 'langchain-community==0.3.31', 'langchain-openai>=0.3.0', 'langchain>=1.2.0', 'pydantic==2.10.6']
excludes_fastapi= True
excludes_uvicorn= True
excludes_sqlalchemy= True
excludes_psycopg= True
excludes_alembic= True
excludes_pgvector= True

post-restart runtime checks:
HTTP/1.1 200 OK /api/health -> {"status":"ok"}
frontend_status=200

backend logs:
Uvicorn running on http://0.0.0.0:8000
Application startup complete.

frontend logs:
VITE v5.4.21 ready
Local: http://localhost:5173/

db logs:
database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 48

## Section 48: PyPI metadata and release workflow - publishable SDK

**Single goal:** Finalize publish metadata and repeatable release workflow for SDK.

**Why:** This synchronizes generated artifacts and release/CI safeguards so the integrated system remains consistent over time.


**Details:**
- Configure package identity/versioning/classifiers.
- Add reproducible release commands and optional workflow automation.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): build/publish tooling as needed.
- Tooling (uv, poetry, Docker): add release helper script/workflow.

**Files and purpose**

| File | Purpose |
|------|--------|
| `scripts/release_sdk.sh` | Local release helper flow. |
| `.github/workflows/release-sdk.yml` | Tagged release workflow. |
| `README.md` | Release/versioning docs. |

**How to test:** Run build/check dry-run (`python -m build`, `twine check`).

**Test results:**
- Completed.

---

**Completion notes:**
- Added publish-ready metadata to `sdk/core/pyproject.toml` (package description, authors, keywords, classifiers, and project URLs).
- Added `scripts/release_sdk.sh` with UTC timestamped logs, reproducible `build` + `twine check`, tag/version consistency guard, and optional PyPI upload (`PUBLISH=1`).
- Added `.github/workflows/release-sdk.yml` for tag-triggered (`agent-search-core-v*`) release automation plus manual dispatch.
- Updated root `README.md` with SDK release/versioning commands and workflow trigger details.
- Restarted services and validated backend/frontend/db logs and health endpoint after changes.

**Commands run:**
- `docker compose down -v --rmi all && docker compose build && docker compose up -d`
- `docker compose ps`
- `./scripts/release_sdk.sh`
- `docker compose restart`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --no-color --tail=120 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 db`

**Useful logs (excerpt):**
```text
release_sdk dry-run:
2026-03-09T20:14:22Z INFO release_sdk: starting sdk_dir=/Users/nickbohm/Desktop/tinkering/agent-search/sdk/core version=0.1.0 publish=0
2026-03-09T20:14:22Z INFO release_sdk: building sdist and wheel
Successfully built agent_search_core-0.1.0.tar.gz and agent_search_core-0.1.0-py3-none-any.whl
2026-03-09T20:14:30Z INFO release_sdk: running twine check
Checking ...agent_search_core-0.1.0-py3-none-any.whl: PASSED
Checking ...agent_search_core-0.1.0.tar.gz: PASSED
2026-03-09T20:14:32Z INFO release_sdk: dry run complete; skipping upload (set PUBLISH=1 to publish)

post-restart runtime checks:
HTTP/1.1 200 OK
{"status":"ok"}

backend logs:
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.

frontend logs:
VITE v5.4.21  ready
Local:   http://localhost:5173/

db logs:
PostgreSQL Database directory appears to contain a database; Skipping initialization
database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 49

## Section 49: CI drift gates - long-term contract safety

**Single goal:** Add CI checks that prevent API/SDK/spec artifact drift after integration.

**Why:** This synchronizes generated artifacts and release/CI safeguards so the integrated system remains consistent over time.

**Details:**
- Enforce OpenAPI parity and generated-client freshness checks.
- Keep migration-safe guardrails for future endpoint/schema changes.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new runtime dependencies.
- Tooling (uv, poetry, Docker): add CI validation steps.

**Files and purpose**

| File | Purpose |
|------|--------|
| `scripts/validate_openapi.sh` | OpenAPI drift gate script. |
| `.github/workflows/ci.yml` | CI checks for spec/client parity. |

**How to test:** Run CI-equivalent checks locally and verify intentional drift fails.

**Test results:**
- Completed.

---

**Completion notes:**
- Added new GitHub Actions workflow `.github/workflows/ci.yml` (push to `main` + pull requests) that runs the OpenAPI/client drift gate.
- Expanded `scripts/validate_openapi.sh` into a full contract drift gate with UTC-timestamped logging for:
  - OpenAPI structural validation via `openapitools/openapi-generator-cli validate`.
  - Runtime-versus-committed OpenAPI parity checks (normalized JSON compare).
  - Generated SDK freshness checks by generating into a temporary copy and diffing against `sdk/python`.
- Added resilience for local development where host `uv` may fail platform resolution by exporting runtime OpenAPI from the running `backend` container when available, with host fallback.
- Updated canonical generated artifacts (`openapi.json`, `sdk/python/.openapi-generator/FILES`) to satisfy the new parity/freshness gate.
- Restarted all containers and verified runtime health and logs after changes.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `curl -sS http://localhost:8000/api/health`
- `./scripts/validate_openapi.sh`
- `docker compose exec -T backend uv run python - <<'PY' > openapi.json ... PY`
- `./scripts/generate_sdk.sh`
- `./scripts/validate_openapi.sh`
- `python3 - <<'PY' ... write openapi.drift-test.json with info.version drift ... PY`
- `./scripts/validate_openapi.sh openapi.drift-test.json` (expected failure)
- `python3 - <<'PY' ... unlink openapi.drift-test.json ... PY`
- `docker compose restart`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `docker compose logs --no-color --tail=120 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 db`

**Useful logs (excerpt):**
```text
validate gate pass:
2026-03-09T20:20:49Z INFO validate_openapi: starting validation spec=/Users/nickbohm/Desktop/tinkering/agent-search/openapi.json
No validation issues detected.
2026-03-09T20:20:53Z INFO validate_openapi: OpenAPI parity check passed spec=/Users/nickbohm/Desktop/tinkering/agent-search/openapi.json
2026-03-09T20:20:55Z INFO validate_openapi: sdk drift check passed sdk=/Users/nickbohm/Desktop/tinkering/agent-search/sdk/python
2026-03-09T20:20:55Z INFO validate_openapi: all checks passed

intentional drift failure:
2026-03-09T20:21:27Z INFO validate_openapi: starting validation spec=/Users/nickbohm/Desktop/tinkering/agent-search/openapi.drift-test.json
2026-03-09T20:21:32Z ERROR validate_openapi: committed OpenAPI differs from runtime export path=/Users/nickbohm/Desktop/tinkering/agent-search/openapi.drift-test.json
@@ -1469,7 +1469,7 @@
-    "version": "0.1.0-drift-test"
+    "version": "0.1.0"

post-restart runtime checks:
HTTP/1.1 200 OK
{"status":"ok"}

backend logs:
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.

frontend logs:
VITE v5.4.21  ready
Local:   http://localhost:5173/

db logs:
database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 50

## Section 50: End-to-end integrated acceptance - full system completion gate

**Single goal:** Validate full integrated system from SDK runtime through benchmark dashboard.

**Why:** This verifies the full integrated stack works end-to-end before observability and documentation hardening.


**Details:**
- Required path: corpus load -> benchmark run create -> completion -> compare endpoint -> dashboard list/detail verification.
- Include negative paths: invalid mode, dataset missing, judge timeout/failure, cancellation.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): use existing docker compose test flows.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tests/e2e/test_benchmark_pipeline.py` | Backend E2E acceptance flow. |
| `src/backend/tests/sdk/test_sdk_run_e2e.py` | SDK E2E sync acceptance. |
| `src/backend/tests/sdk/test_sdk_async_e2e.py` | SDK E2E async acceptance. |
| `src/frontend/src/components/BenchmarkRunList.test.tsx` | Frontend benchmark list acceptance. |
| `src/frontend/src/components/BenchmarkRunDetail.test.tsx` | Frontend benchmark detail acceptance. |
| `test_completed.md` | Final integrated test command/results log. |

**How to test:**
- `docker compose exec backend uv run pytest`
- `docker compose exec frontend npm run test`
- Manual end-to-end verification at `http://localhost:5173`.

**Test results:**
- Completed.

---

**Completion notes:**
- Added backend integrated acceptance suite at `src/backend/tests/e2e/test_benchmark_pipeline.py` covering:
  - corpus load endpoint -> benchmark run create -> run completion -> compare endpoint -> list/detail endpoint checks
  - negative paths for invalid mode request, missing dataset, judge timeout/failure handling, and cancellation behavior.
- Reused existing runtime/benchmark services and API routes, with deterministic monkeypatching for benchmark execution dependencies and quality scoring to keep E2E tests fast and stable.
- Updated backend baseline tests for current route inventory and compatibility fixes that surfaced during full-suite validation:
  - `src/backend/tests/api/test_health.py` route snapshot now includes benchmark endpoints.
  - `src/backend/tests/db/test_wipe.py` now uses isolated `MetaData()` to avoid global metadata collisions.
  - `src/backend/tests/services/test_reranker_service.py` pins provider behavior explicitly and updates OpenAI mock signatures to match current runtime callback kwargs.
  - `src/backend/tests/services/test_vector_store_service.py` now asserts enriched score metadata returned by thresholded search.
- Restarted containers and verified backend/frontend/db logs and endpoint health after implementation.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/e2e/test_benchmark_pipeline.py"`
- `docker compose exec backend sh -lc "uv run --with pytest pytest tests/api/test_health.py tests/db/test_wipe.py tests/services/test_reranker_service.py tests/services/test_vector_store_service.py tests/e2e/test_benchmark_pipeline.py"`
- `docker compose exec backend sh -lc "uv run --with pytest pytest"`
- `docker compose exec frontend npm run test`
- `docker compose restart`
- `docker compose ps`
- `curl -sS -i http://localhost:8000/api/health`
- `curl -sS -I http://localhost:5173`
- `docker compose logs --no-color --tail=140 backend`
- `docker compose logs --no-color --tail=140 frontend`
- `docker compose logs --no-color --tail=140 db`

**Useful logs (excerpt):**
```text
backend tests:
pytest: tests/e2e/test_benchmark_pipeline.py ..... [100%]
pytest: 245 passed, 1 warning in 12.31s

frontend tests:
vitest: Test Files 3 passed (3)
vitest: Tests 12 passed (12)

post-restart checks:
HTTP/1.1 200 OK
{"status":"ok"}

frontend HTTP check:
HTTP/1.1 200 OK

backend logs:
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.

frontend logs:
VITE v5.4.21 ready
Local:   http://localhost:5173/

db logs:
database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 51

## Section 51: Langfuse foundation - SDK/runtime observability configuration

**Single goal:** Add configuration and client bootstrap for Langfuse across SDK runtime and benchmark services.

**Why:** This adds observability after core stability so tracing improves operations without destabilizing functional delivery.


**Details:**
- Define environment-backed Langfuse settings (host, public key, secret key, enabled flag, sampling controls).
- Initialize a shared Langfuse client utility used by SDK runtime and benchmark services.
- Ensure observability can be disabled cleanly without affecting runtime behavior.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): reuse existing `langfuse` dependency in backend.
- Tooling (uv, poetry, Docker): add env var docs and compose env pass-through if needed.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/config.py` | Langfuse configuration fields and defaults. |
| `src/backend/utils/langfuse_tracing.py` | Shared Langfuse client/bootstrap helpers. |
| `.env.example` | Langfuse env variable documentation. |
| `src/backend/tests/utils/test_langfuse_tracing.py` | Langfuse bootstrap/config tests. |

**How to test:** Run Langfuse utility tests with enabled/disabled modes and verify no-op fallback behavior.

**Test results:**
- Completed.

---

**Completion notes:**
- Added `LangfuseSettings` in `src/backend/config.py` with env-backed fields for `LANGFUSE_ENABLED`, host/base URL, keys, environment/release, plus `LANGFUSE_RUNTIME_SAMPLE_RATE` and `LANGFUSE_BENCHMARK_SAMPLE_RATE` sampling controls.
- Added shared sampling helper `should_sample_rate(...)` and scope-based sample-rate resolution for runtime vs benchmark traces.
- Refactored `src/backend/utils/langfuse_tracing.py` to use config-backed bootstrap:
  - shared, cached Langfuse client initializer (`get_langfuse_client(...)`)
  - deterministic enable/disable and sampling gate before callback handler creation
  - clean no-op fallback when disabled/missing credentials/import/init failure
  - explicit startup/sampling/flush logging for runtime visibility.
- Expanded tests:
  - updated `tests/utils/test_langfuse_tracing.py` for config-backed enabled/disabled behavior, sampling scope behavior, shared client bootstrap, and no-op flush fallback paths.
  - added `LangfuseSettings` coverage in `tests/utils/test_benchmark_config.py` for defaults, env overrides, and invalid sampling fallback handling.
- Updated `.env.example` with new Langfuse settings docs:
  - `LANGFUSE_BASE_URL`
  - `LANGFUSE_RUNTIME_SAMPLE_RATE`
  - `LANGFUSE_BENCHMARK_SAMPLE_RATE`.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose restart backend`
- `docker compose exec backend sh -lc 'uv sync --frozen --all-groups'`
- `docker compose exec backend sh -lc 'uv run --with pytest pytest tests/utils/test_langfuse_tracing.py tests/utils/test_benchmark_config.py'`
- `docker compose ps`
- `docker compose logs --no-color --tail=200 backend`
- `docker compose logs --no-color --tail=120 frontend`
- `docker compose logs --no-color --tail=120 db`

**Useful logs (excerpt):**
```text
backend tests:
============================= test session starts ==============================
collected 14 items

tests/utils/test_langfuse_tracing.py .......                             [ 50%]
tests/utils/test_benchmark_config.py .......                             [100%]

============================== 14 passed in 0.15s ==============================

backend runtime:
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.

frontend runtime:
VITE v5.4.21  ready in 288 ms
Local:   http://localhost:5173/

db runtime:
database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 52

## Section 52: Langfuse instrumentation - runtime and benchmark traces

**Single goal:** Instrument SDK runtime stages and benchmark lifecycle with consistent Langfuse traces and scores.

**Why:** This adds observability after core stability so tracing improves operations without destabilizing functional delivery.


**Details:**
- Emit traces/spans for SDK runtime stages (`decompose`, `expand`, `search`, `rerank`, `answer`, `final`).
- Emit benchmark run spans for dataset load, mode execution, question execution, judge scoring, and aggregation.
- Attach run metadata (run_id, mode, question_id, correctness score, latency) to trace attributes.
- Record benchmark correctness/latency outputs as Langfuse scores where appropriate.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): reuse existing `langfuse` dependency.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/runner.py` | Stage-level runtime tracing instrumentation. |
| `src/backend/services/benchmark_runner.py` | Benchmark execution tracing instrumentation. |
| `src/backend/services/benchmark_judge_service.py` | Judge call tracing and score logging. |
| `src/backend/tests/sdk/test_sdk_run_e2e.py` | Verify runtime trace hooks do not break behavior. |
| `src/backend/tests/services/test_benchmark_runner.py` | Verify benchmark trace metadata propagation. |

**How to test:** Run SDK and benchmark tests with Langfuse enabled in test mode and verify expected trace payload hooks are called.

**Test results:**
- Completed.

---

**Completion notes:**
- Extended `src/backend/utils/langfuse_tracing.py` with reusable, no-fail trace/span/score helpers:
  - `start_langfuse_trace(...)`
  - `start_langfuse_span(...)`
  - `record_langfuse_score(...)`
  - `end_langfuse_observation(...)`
  - plus signature-aware kwargs filtering for SDK compatibility across Langfuse client variants.
- Instrumented runtime execution in `src/backend/agent_search/runtime/runner.py`:
  - trace root: `runtime.agent_run`
  - initial context span: `runtime.initial_context`
  - per-stage spans emitted from graph snapshots with stage normalization to `final`
  - runtime summary score: `runtime.sub_question_count`
  - terminal observation closure on both normal and vector-store-timeout short-circuit paths.
- Instrumented benchmark lifecycle in `src/backend/services/benchmark_runner.py`:
  - trace root: `benchmark.run`
  - lifecycle spans: `benchmark.dataset_load`, `benchmark.mode_execution`, `benchmark.question_execution`, `benchmark.aggregation`
  - attached metadata for run/mode/question and emitted latency/correctness scores:
    - `benchmark.correctness`
    - `benchmark.latency_ms`
  - ensured run trace closure in `finally` so failed runs still emit terminal metadata.
- Instrumented judge scoring path in `src/backend/services/benchmark_quality_service.py` (current judge implementation file):
  - trace root: `benchmark.judge`
  - scoring span: `benchmark.judge_scoring`
  - score emission: `benchmark.correctness`
  - metadata propagation for `run_id`, `mode`, and `question_id` when provided by runner.
- Added/updated tests:
  - `src/backend/tests/utils/test_langfuse_tracing.py`
  - `src/backend/tests/sdk/test_sdk_run_e2e.py`
  - `src/backend/tests/services/test_benchmark_runner.py`
  - `src/backend/tests/services/test_benchmark_quality_service.py`

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose restart backend`
- `docker compose exec backend uv run --with pytest python -m pytest tests/utils/test_langfuse_tracing.py tests/sdk/test_sdk_run_e2e.py tests/services/test_benchmark_runner.py tests/services/test_benchmark_quality_service.py`
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`

**Useful logs (excerpt):**
```text
backend tests:
============================= test session starts ==============================
collected 17 items

tests/utils/test_langfuse_tracing.py ........                            [ 47%]
tests/sdk/test_sdk_run_e2e.py ..                                         [ 58%]
tests/services/test_benchmark_runner.py ....                             [ 82%]
tests/services/test_benchmark_quality_service.py ...                     [100%]

============================== 17 passed in 1.73s ==============================

backend runtime:
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.

frontend runtime:
VITE v5.4.21  ready in 238 ms
Local:   http://localhost:5173/

db runtime:
database system is ready to accept connections
```

## Completed - 2026-03-09 - Section 53

## Section 53: Documentation refresh - SDK, benchmark, README, and run-flow assets

**Single goal:** Update all user-facing and developer-facing documentation to reflect the integrated SDK + benchmark + Langfuse system.

**Why:** This aligns all docs and diagrams with implemented behavior so developers and users can reliably operate the system.


**Details:**
- Update top-level `README.md` with SDK usage, benchmark operation, and Langfuse setup.
- Update SDK docs (`sdk/README.md` and package docs) with sync/async usage, error taxonomy, and vectorstore adapter guidance.
- Update architecture docs for runtime boundaries and benchmark pipeline.
- Update frontend visualization artifact `src/frontend/public/run-flow.html` to include benchmark and observability flow.
- Ensure docs reference real commands from Docker Compose/uv workflows used in this repo.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `README.md` | Primary setup and operations guide for SDK + benchmark + Langfuse. |
| `sdk/README.md` | SDK consumer guide and generated-client positioning. |
| `sdk/core/README.md` | Core package usage and release notes guidance. |
| `docs/SYSTEM_ARCHITECTURE.md` | Updated architecture and flow boundaries. |
| `src/frontend/public/run-flow.html` | Updated runtime/benchmark flow visualization. |

**How to test:** Manually execute documented commands end-to-end and verify docs match actual outputs and paths.

**Test results:**
- Completed.

---

**Completion notes:**
- Refreshed `README.md` to include:
  - Runtime API quick usage.
  - In-process SDK contract (`run`, `run_async`, `get_run_status`, `cancel_run`).
  - SDK error taxonomy and vector-store protocol expectations.
  - Benchmark API and benchmark CLI commands that match current backend implementation.
  - Langfuse environment setup and restart/log verification workflow.
- Updated `sdk/README.md` and `sdk/core/README.md` to align with current SDK boundary and release workflow.
- Rewrote `docs/SYSTEM_ARCHITECTURE.md` to show current runtime graph path, benchmark orchestration path, SDK boundary, and Langfuse observability path.
- Extended `src/frontend/public/run-flow.html` with benchmark flow and observability sections while preserving canonical runtime stage mapping.

**Commands run:**
- `docker compose down -v --rmi all`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `curl -sS http://localhost:8000/api/health`
- `curl -sS http://localhost:8000/api/benchmarks/runs`
- `docker compose exec backend uv run python benchmarks/run.py --dataset-id internal_v1 --mode baseline_retrieve_then_answer --dry-run`
- `docker compose exec backend uv run python benchmarks/export.py`
- `docker compose restart backend frontend db`
- `docker compose logs --tail=200 backend`
- `docker compose logs --tail=120 frontend`
- `docker compose logs --tail=120 db`

**Useful logs (excerpt):**
```text
health:
{"status":"ok"}

benchmark list:
{"runs":[]}

benchmark dry-run:
INFO:__main__:Benchmark run cli dry-run completed dataset_id=internal_v1
{"collection_name": "agent_search_internal_data", "dataset_id": "internal_v1", "dry_run": true, "metadata": {}, "model": "gpt-4.1-mini", "modes": ["baseline_retrieve_then_answer"], "question_count": 120, "run_id": null, "selected_question_count": 120, "temperature": 0.0}

benchmark export:
No benchmark runs available to export.

backend runtime:
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.

frontend runtime:
VITE v5.4.21  ready in 157 ms
Local:   http://localhost:5173/

db runtime:
database system is ready to accept connections
```
