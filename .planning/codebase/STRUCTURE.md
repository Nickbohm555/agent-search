# Codebase Structure

**Analysis Date:** 2026-03-12

## Directory Layout

```text
agent-search/
├── src/
│   ├── backend/                 # FastAPI app, runtime pipeline, services, schemas, DB models/migrations
│   └── frontend/                # React/Vite UI and typed API client
├── sdk/
│   ├── core/                    # In-process Python SDK (runtime-compatible library)
│   ├── python/                  # Generated OpenAPI Python client package
│   └── examples/                # SDK usage examples
├── docs/                        # Consolidated documentation artifact(s)
├── scripts/                     # Utility scripts for docs/runtime support
├── docker-compose.yml           # Local service topology (db/backend/frontend/chrome)
└── openapi.json                 # API contract consumed by generated clients
```

## Directory Purposes

**`src/backend`:**
- Purpose: Backend API surface and core runtime business logic.
- Contains: FastAPI app (`main.py`), routers (`routers/`), runtime engine (`agent_search/runtime/`), domain services (`services/`), schemas (`schemas/`), DB layer (`db.py`, `models.py`, `alembic/`).
- Key files: `src/backend/main.py`, `src/backend/routers/agent.py`, `src/backend/routers/internal_data.py`, `src/backend/services/agent_service.py`, `src/backend/agent_search/public_api.py`.

**`src/frontend`:**
- Purpose: Operational UI for internal data loading and async run inspection.
- Contains: React app shell (`src/App.tsx`), network/client contract layer (`src/utils/api.ts`), env config (`src/utils/config.ts`), styles/tests.
- Key files: `src/frontend/src/main.tsx`, `src/frontend/src/App.tsx`, `src/frontend/src/utils/api.ts`.

**`sdk/core`:**
- Purpose: Runtime SDK package for direct Python integration without HTTP transport.
- Contains: Mirrored runtime/service/schema modules under `sdk/core/src/`.
- Key files: `sdk/core/src/agent_search/public_api.py`, `sdk/core/src/agent_search/runtime/runner.py`, `sdk/core/src/schemas/agent.py`.

**`sdk/python`:**
- Purpose: OpenAPI-generated Python transport client against backend HTTP API.
- Contains: Generated APIs/models/config under `sdk/python/openapi_client/` and tests under `sdk/python/test/`.
- Key files: `sdk/python/openapi_client/api/agents_api.py`, `sdk/python/openapi_client/api/internal_data_api.py`.

**`src/backend/tests` and `src/frontend/src/test`:**
- Purpose: Contract, unit, and behavior tests for backend runtime and frontend rendering/client behavior.
- Contains: API tests, service tests, runtime node tests, frontend test setup.
- Key files: `src/backend/tests/api/test_agent_run.py`, `src/backend/tests/sdk/test_sdk_run_e2e.py`, `src/frontend/src/App.test.tsx`.

## Key File Locations

**Entry Points:**
- `src/backend/main.py`: FastAPI app bootstrap and router registration.
- `src/frontend/src/main.tsx`: React root mount.
- `src/backend/agent_search/public_api.py`: SDK entry surface used by backend router delegation.

**Configuration:**
- `docker-compose.yml`: Service orchestration and runtime commands.
- `src/backend/config.py`: Langfuse and runtime config helpers.
- `src/backend/pyproject.toml`: Backend dependency and runtime metadata.
- `src/frontend/package.json`: Frontend scripts/dependencies.
- `src/frontend/src/utils/config.ts`: Frontend API base URL env binding.

**Core Logic:**
- `src/backend/services/agent_service.py`: Graph orchestration and stage/state assembly.
- `src/backend/agent_search/runtime/nodes/`: Stage-specific runtime nodes.
- `src/backend/services/internal_data_service.py`: Wiki ingestion to vector store + metadata persistence.
- `src/backend/services/vector_store_service.py`: PGVector access and retrieval helper functions.

**Testing:**
- `src/backend/tests/api/`: HTTP endpoint contract tests.
- `src/backend/tests/services/`: Service-layer behavior tests.
- `src/backend/tests/sdk/`: Runtime node/protocol/e2e tests.
- `src/frontend/src/App.test.tsx`: UI behavior smoke coverage.

## Naming Conventions

**Files:**
- Python modules use `snake_case.py` (example: `src/backend/services/internal_data_jobs.py`).
- React component files use `PascalCase.tsx` for top-level UI components (example: `src/frontend/src/App.tsx`).
- Utility/config TS files use `camelCase` or lowercase names (example: `src/frontend/src/utils/api.ts`, `src/frontend/src/utils/config.ts`).
- Generated client package keeps OpenAPI naming patterns (example: `sdk/python/openapi_client/models/runtime_agent_run_async_status_response.py`).

**Directories:**
- Backend domains are grouped by responsibility (`routers`, `services`, `schemas`, `agent_search/runtime`).
- Runtime stage implementations are grouped by node type in `src/backend/agent_search/runtime/nodes/`.
- SDK packaging is separated by distribution mode (`sdk/core` vs `sdk/python`).

## Where to Add New Code

**New Backend API capability:**
- Primary code: `src/backend/routers/` for endpoint surface and `src/backend/services/` for domain logic.
- Runtime-specific flow changes: `src/backend/services/agent_service.py` and relevant files in `src/backend/agent_search/runtime/nodes/`.
- Tests: `src/backend/tests/api/` and `src/backend/tests/services/` (plus `src/backend/tests/sdk/` for runtime node behavior).

**New Frontend capability:**
- Implementation: `src/frontend/src/App.tsx` for current single-screen UX, or extract to new `src/frontend/src/components/` module if creating reusable panels.
- API integration: `src/frontend/src/utils/api.ts`.
- Tests: `src/frontend/src/App.test.tsx` or additional files under `src/frontend/src/test/`.

**New runtime node/module:**
- Implementation: `src/backend/agent_search/runtime/nodes/`.
- Orchestration wiring: `src/backend/services/agent_service.py`.
- Contract updates: `src/backend/schemas/agent.py`.
- Tests: `src/backend/tests/sdk/`.

**New persistence/retrieval utilities:**
- Shared DB helpers: `src/backend/common/db/`.
- ORM/table changes: `src/backend/models.py` + `src/backend/alembic/versions/`.
- Vector operations: `src/backend/services/vector_store_service.py`.

**SDK contract/client updates:**
- In-process SDK updates: `sdk/core/src/`.
- HTTP client regeneration target: `sdk/python/openapi_client/` using `openapi.json` as source contract.

## Special Directories

**`src/backend/alembic/`:**
- Purpose: Database migration environment and migration revisions.
- Generated: Partially generated (revision scaffolds) and manually edited.
- Committed: Yes.

**`sdk/python/openapi_client/`:**
- Purpose: Generated Python client for backend API endpoints and models.
- Generated: Yes.
- Committed: Yes.

**`sdk/core/dist/`:**
- Purpose: Built distribution artifacts (wheel) for core SDK.
- Generated: Yes.
- Committed: Yes.

**`docs/`:**
- Purpose: Human-readable consolidated architecture/runtime documentation output.
- Generated: Mixed (contains generated/assembled docs output).
- Committed: Yes.

---

*Structure analysis: 2026-03-12*
