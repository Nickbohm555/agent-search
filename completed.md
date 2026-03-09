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
