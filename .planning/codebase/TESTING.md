# Testing Patterns

**Analysis Date:** 2026-03-12

## Test Framework

**Runner:**
- Backend: `pytest` (configured via dependency usage, not a dedicated `pytest.ini`) in `src/backend/tests/`.
- Frontend: `vitest` via `src/frontend/package.json` and `src/frontend/vite.config.ts`.
- Config: `src/frontend/vite.config.ts` (jsdom environment, setup file at `src/frontend/src/test/setup.ts`).

**Assertion Library:**
- Backend: native `assert` in pytest tests under `src/backend/tests/`.
- Frontend: Testing Library assertions with Vitest and jest-dom in `src/frontend/src/App.test.tsx` and `src/frontend/src/test/setup.ts`.

**Run Commands:**
```bash
docker compose exec backend uv run pytest     # Backend tests
docker compose exec frontend npm run test      # Frontend tests
docker compose exec frontend npm run typecheck # Frontend type check
```

## Test File Organization

**Location:**
- Backend tests are in a separate tree under `src/backend/tests/` with domain folders (`api`, `services`, `sdk`, `contracts`, `db`, `tools`, `utils`).
- Frontend tests are co-located with the component in `src/frontend/src/App.test.tsx`.
- Python generated SDK tests are separate under `sdk/python/test/`.

**Naming:**
- Backend: `test_*.py` naming, such as `src/backend/tests/api/test_health.py`.
- Frontend: `<Component>.test.tsx`, such as `src/frontend/src/App.test.tsx`.
- Generated SDK: `test_*.py` under `sdk/python/test/`.

**Structure:**
```
src/backend/tests/<domain>/test_*.py
src/frontend/src/*.test.tsx
sdk/python/test/test_*.py
```

## Test Structure

**Suite Organization:**
```typescript
describe("App run query flow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows ordered stage rail and progressive status updates while polling", async () => {
    // fetch mocked in sequence
    // render(<App />)
    // user interaction and async assertions
  });
});
```

**Patterns:**
- Backend setup is explicit and local to tests (for example in-memory SQLite in `src/backend/tests/api/test_agent_run.py`).
- Backend behavior tests heavily use monkeypatch to isolate dependencies in `src/backend/tests/services/test_agent_service.py` and `src/backend/tests/sdk/test_sdk_async_e2e.py`.
- Frontend tests model multi-step async API flows by ordered `fetch` mocks in `src/frontend/src/App.test.tsx`.

## Mocking

**Framework:** `pytest` monkeypatch for Python tests; `vi` mock/stub APIs for frontend tests.

**Patterns:**
```typescript
const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ sources: [] }), { status: 200 }));
vi.stubGlobal("fetch", fetchMock);
```

```python
monkeypatch.setattr(agent_service, "run_search_node", fake_run_search_node)
monkeypatch.setattr(runtime_jobs, "_EXECUTOR", _InlineExecutor())
```

**What to Mock:**
- Network and API boundaries (`fetch`) in `src/frontend/src/App.test.tsx`.
- External runtime dependencies (LLM, vector store, async executors, env values) in `src/backend/tests/services/` and `src/backend/tests/sdk/`.

**What NOT to Mock:**
- Core schema contracts are validated against actual OpenAPI objects in `src/backend/tests/api/test_health.py`.
- Public function signatures are tested directly in `src/backend/tests/contracts/test_public_contracts.py`.

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture(autouse=True)
def clear_runtime_jobs():
    with runtime_jobs._JOB_LOCK:
        runtime_jobs._JOBS.clear()
    yield
    with runtime_jobs._JOB_LOCK:
        runtime_jobs._JOBS.clear()
```

**Location:**
- Fixtures are mostly inline in individual test files (for example `src/backend/tests/sdk/test_sdk_async_e2e.py`) rather than centralized in `conftest.py`.

## Coverage

**Requirements:** Not enforced at repository CI level for main backend/frontend app flows.

**View Coverage:**
```bash
# Not detected for src/backend or src/frontend CI workflow.
# Generated SDK has coverage examples in sdk/python/.github/workflows/python.yml.
```

## Test Types

**Unit Tests:**
- Strong backend unit coverage around service and node logic in `src/backend/tests/services/` and `src/backend/tests/sdk/`.

**Integration Tests:**
- API integration tests with FastAPI `TestClient` in `src/backend/tests/api/`.
- Contract tests for public API signatures in `src/backend/tests/contracts/test_public_contracts.py`.

**E2E Tests:**
- Frontend has component-level interaction tests that simulate end-to-end user flows in `src/frontend/src/App.test.tsx`.
- Full browser E2E framework is not detected in repository config.

## Common Patterns

**Async Testing:**
```typescript
await waitFor(() => {
  expect(screen.getByText("Run status: Completed.")).toBeInTheDocument();
});
```

```python
start_response = public_api.run_async(...)
status_response = public_api.get_run_status(start_response.job_id)
assert status_response.status == "success"
```

**Error Testing:**
```python
with caplog.at_level(logging.WARNING):
    config = agent_service.build_runtime_timeout_config_from_env()
assert "Invalid timeout env value" in caplog.text
```

## Testing Posture

- Backend runtime behavior is tested deeply with many scenario tests, with concentration in `src/backend/tests/services/test_agent_service.py`.
- Frontend behavior is validated in a single large scenario file `src/frontend/src/App.test.tsx`, which provides breadth but creates a single maintenance hotspot.
- API contract stability is explicitly protected through route/schema and signature snapshots in `src/backend/tests/api/test_health.py` and `src/backend/tests/contracts/test_public_contracts.py`.
- Generated SDK has its own independent test track in `sdk/python/test/`, reducing confidence coupling between app and generated client.

## Lint and Type Coverage

- Frontend TypeScript strict mode is enabled in `src/frontend/tsconfig.json` and a `typecheck` script exists in `src/frontend/package.json`.
- Frontend lint coverage is limited: no explicit ESLint config file or lint script is detected in `src/frontend/package.json`.
- Backend app type/lint gates are limited: `src/backend/pyproject.toml` does not define mypy/ruff/flake8 tooling.
- Generated SDK has stronger static typing configuration in `sdk/python/pyproject.toml` (mypy configuration and strictness plan), but this does not cover `src/backend`.
- Main CI workflow in `.github/workflows/ci.yml` currently validates OpenAPI drift and does not run backend/frontend tests, lint, or type checks.

## Complexity Hotspots

- `src/backend/tests/services/test_agent_service.py` (large, broad behavior matrix).
- `src/backend/services/agent_service.py` (central orchestration and timeout/fallback handling).
- `src/frontend/src/App.test.tsx` and `src/frontend/src/App.tsx` (single-file concentration for UI behavior and flow testing).
- `src/frontend/src/utils/api.ts` (extensive runtime payload validation logic in one module).

## Duplication and Risk Patterns

- Backend runtime code is mirrored into SDK core modules, so test changes may need to validate both paths (`src/backend/...` and `sdk/core/src/...`).
- Global in-memory job state in `src/backend/agent_search/runtime/jobs.py` and `src/backend/services/internal_data_jobs.py` requires careful isolation; tests explicitly clear shared dictionaries to avoid cross-test leakage.
- Broad exception fallback paths in runtime services can turn defects into degraded-success behavior, requiring explicit negative-path assertions in tests.

## Maintainability Observations

- Consolidate cross-cutting fixtures into `conftest.py` under `src/backend/tests/` to reduce repeated setup patterns.
- Split oversized scenario suites (`src/backend/tests/services/test_agent_service.py`, `src/frontend/src/App.test.tsx`) into focused files by capability.
- Add CI jobs in `.github/workflows/ci.yml` for backend tests, frontend tests, and frontend typecheck to keep quality gates enforceable.
- Add app-level lint/type gates for backend Python code to improve static feedback before runtime.

---

*Testing analysis: 2026-03-12*
