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
