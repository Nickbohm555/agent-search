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
