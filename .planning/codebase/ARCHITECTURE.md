# Architecture

**Analysis Date:** 2026-03-12

## Pattern Overview

**Overall:** Layered modular monolith with a graph-style runtime pipeline and API-first boundaries.

**Key Characteristics:**
- HTTP boundary is a single FastAPI app in `src/backend/main.py` with route modules in `src/backend/routers/`.
- Runtime orchestration is an internal graph pipeline split into typed node modules under `src/backend/agent_search/runtime/nodes/`.
- Frontend is a single React app in `src/frontend/src/App.tsx` that talks only to backend REST endpoints through `src/frontend/src/utils/api.ts`.
- SDK code is split into in-process runtime (`sdk/core/src/`) and generated HTTP client (`sdk/python/openapi_client/`), creating both direct-library and network boundaries.

## Layers

**UI Layer (React client):**
- Purpose: Render ingestion/run controls and visualize per-stage runtime outputs.
- Location: `src/frontend/src/`.
- Contains: App state machine, polling loops, response validation, timeline/readout UI.
- Depends on: Browser fetch API, backend JSON contracts, type guards in `src/frontend/src/utils/api.ts`.
- Used by: End users via `src/frontend/src/main.tsx`.

**HTTP API Layer (FastAPI routers):**
- Purpose: Expose runtime and internal-data operations as REST endpoints.
- Location: `src/backend/main.py`, `src/backend/routers/agent.py`, `src/backend/routers/internal_data.py`.
- Contains: Request parsing, response shaping, dependency construction, HTTP error mapping.
- Depends on: Schemas in `src/backend/schemas/`, service/runtime modules in `src/backend/services/` and `src/backend/agent_search/`.
- Used by: Frontend (`src/frontend/src/utils/api.ts`) and generated Python API client (`sdk/python/openapi_client/api/`).

**Runtime Orchestration Layer (Agent graph):**
- Purpose: Execute decompose -> expand -> search -> rerank -> answer -> synthesize pipeline.
- Location: `src/backend/services/agent_service.py`, `src/backend/agent_search/runtime/runner.py`, `src/backend/agent_search/runtime/jobs.py`, `src/backend/agent_search/runtime/nodes/`.
- Contains: Graph state transforms, fan-out/fan-in concurrency, stage snapshots, async job tracking.
- Depends on: Retrieval and LLM services in `src/backend/services/`, schemas in `src/backend/schemas/agent.py`, tracing in `src/backend/utils/langfuse_tracing.py`.
- Used by: Router delegates in `src/backend/routers/agent.py` and SDK entry points in `src/backend/agent_search/public_api.py`.

**Data Access + Retrieval Layer:**
- Purpose: Persist internal documents/chunks and perform vector search.
- Location: `src/backend/db.py`, `src/backend/models.py`, `src/backend/services/vector_store_service.py`, `src/backend/common/db/wipe.py`.
- Contains: SQLAlchemy session setup, table models, PGVector integration, retrieval helpers, wipe operations.
- Depends on: Postgres/pgvector via `docker-compose.yml`, embeddings in `src/backend/utils/embeddings.py`.
- Used by: Internal data load path (`src/backend/services/internal_data_service.py`) and runtime search node path (`src/backend/services/agent_service.py`).

**Ingestion + Job Layer:**
- Purpose: Load wiki content into vector store and track async load progress.
- Location: `src/backend/services/internal_data_service.py`, `src/backend/services/internal_data_jobs.py`, `src/backend/services/wiki_ingestion_service.py`.
- Contains: Source discovery, chunking, vector insert, DB metadata insert, background job status store.
- Depends on: Vector store service, DB session factory, schema contracts.
- Used by: Internal data router in `src/backend/routers/internal_data.py` and frontend load/wipe UX.

**SDK Distribution Layer:**
- Purpose: Provide reusable runtime API and external HTTP client package.
- Location: `sdk/core/src/` and `sdk/python/openapi_client/`.
- Contains: Core runtime-compatible modules (`sdk/core/src/agent_search/public_api.py`) and generated REST client (`sdk/python/openapi_client/api/agents_api.py`).
- Depends on: Shared API schema shape from backend and runtime/service logic mirrored from backend.
- Used by: External Python consumers and local backend wrappers.

## Data Flow

**Run Query Flow (async path used by UI):**

1. UI submits query with `startAgentRun()` in `src/frontend/src/utils/api.ts` from form logic in `src/frontend/src/App.tsx`.
2. Backend receives `POST /api/agents/run-async` in `src/backend/routers/agent.py`, builds model/vector dependencies, and delegates to `src/backend/agent_search/public_api.py`.
3. SDK public API queues runtime job through `start_agent_run_job()` in `src/backend/agent_search/runtime/jobs.py`.
4. Background worker executes graph orchestration in `run_parallel_graph_runner()` in `src/backend/services/agent_service.py` using node modules from `src/backend/agent_search/runtime/nodes/`.
5. Job snapshots are persisted in-memory in `_JOBS` within `src/backend/agent_search/runtime/jobs.py`; frontend polls `/api/agents/run-status/{job_id}` via `getAgentRunStatus()` in `src/frontend/src/utils/api.ts`.
6. Final response is assembled as `RuntimeAgentRunResponse` from `src/backend/schemas/agent.py` and rendered in the final synthesis panels of `src/frontend/src/App.tsx`.

**Internal Data Load Flow (async path used by UI):**

1. UI starts load with `startInternalDataLoad()` in `src/frontend/src/utils/api.ts`.
2. Router `POST /api/internal-data/load-async` in `src/backend/routers/internal_data.py` calls `start_internal_data_job()` in `src/backend/services/internal_data_jobs.py`.
3. Worker invokes `load_internal_data()` in `src/backend/services/internal_data_service.py`.
4. Wiki content is resolved/chunked (`src/backend/services/wiki_ingestion_service.py`), embedded and stored through `add_documents_to_store()` in `src/backend/services/vector_store_service.py`, and metadata rows are inserted into `internal_documents` table via SQLAlchemy.
5. Frontend polls `/api/internal-data/load-status/{job_id}` and updates progress state in `src/frontend/src/App.tsx`.

**State Management:**
- Frontend state is component-local React state in `src/frontend/src/App.tsx` with manual polling timers.
- Backend async state is process-memory dictionaries (`_JOBS`, `_CANCEL_FLAGS`) in `src/backend/services/internal_data_jobs.py` and `src/backend/agent_search/runtime/jobs.py`.
- Durable data state is Postgres tables (`internal_documents`, `internal_document_chunks`) in `src/backend/models.py` plus vector collections managed by PGVector integration in `src/backend/services/vector_store_service.py`.

## Key Abstractions

**Typed Runtime Contract:**
- Purpose: Keep node/service handoffs stable.
- Examples: `src/backend/schemas/agent.py`, `src/backend/schemas/internal_data.py`.
- Pattern: Pydantic schema-first contract between router, runtime, and frontend validators.

**Vector Store Compatibility Boundary:**
- Purpose: Isolate runtime from concrete vector DB implementations.
- Examples: `src/backend/agent_search/vectorstore/protocol.py`, `src/backend/agent_search/vectorstore/langchain_adapter.py`.
- Pattern: Protocol + adapter boundary (`similarity_search` contract).

**Graph Node Execution Units:**
- Purpose: Keep each runtime stage independently testable and composable.
- Examples: `src/backend/agent_search/runtime/nodes/decompose.py`, `src/backend/agent_search/runtime/nodes/search.py`, `src/backend/agent_search/runtime/nodes/synthesize.py`.
- Pattern: Pure-ish node function + apply-to-state transform orchestrated in `src/backend/services/agent_service.py`.

**API Client Contract Mirror:**
- Purpose: Keep external consumers decoupled from backend implementation internals.
- Examples: `sdk/python/openapi_client/api/agents_api.py`, `src/frontend/src/utils/api.ts`.
- Pattern: Generated Python client + manual TS client with runtime shape validation.

## Entry Points

**Backend App Entrypoint:**
- Location: `src/backend/main.py`.
- Triggers: Uvicorn startup via `docker-compose.yml`.
- Responsibilities: Configure logging/CORS, register routers, expose health route.

**Frontend App Entrypoint:**
- Location: `src/frontend/src/main.tsx`.
- Triggers: Vite dev/build bootstrap.
- Responsibilities: Mount root React app.

**Async Runtime Job Entrypoint:**
- Location: `src/backend/agent_search/runtime/jobs.py` (`start_agent_run_job`).
- Triggers: `/api/agents/run-async`.
- Responsibilities: Queue background execution, expose stage/result polling surface.

**Internal Data Job Entrypoint:**
- Location: `src/backend/services/internal_data_jobs.py` (`start_internal_data_job`).
- Triggers: `/api/internal-data/load-async`.
- Responsibilities: Queue background ingest, track progress/cancel lifecycle.

## Error Handling

**Strategy:** Convert internal exceptions to typed SDK/HTTP errors while preserving stable response envelopes.

**Patterns:**
- Router-level HTTP mapping with `HTTPException` in `src/backend/routers/agent.py` and `src/backend/routers/internal_data.py`.
- SDK-level exception normalization in `_map_sdk_error()` inside `src/backend/agent_search/public_api.py`.
- Frontend-level typed `ApiResult<T>` and malformed payload guards in `src/frontend/src/utils/api.ts`.
- Async job status transitions to `success/error/cancelled` in in-memory job stores (`src/backend/agent_search/runtime/jobs.py`, `src/backend/services/internal_data_jobs.py`).

## Cross-Cutting Concerns

**Logging:** Structured stage/job logs across backend modules (`src/backend/main.py`, `src/backend/services/agent_service.py`, `src/backend/tools/retriever_tool.py`).
**Validation:** Pydantic request/response models in `src/backend/schemas/` and client-side runtime validation in `src/frontend/src/utils/api.ts`.
**Authentication:** Not implemented; API routes are open and CORS allows all origins in `src/backend/main.py`.

## System Boundaries and Integration Points

**Frontend <-> Backend boundary:**
- REST-only integration through `/api/agents/*` and `/api/internal-data/*` endpoints implemented in `src/backend/routers/`.
- No direct DB or SDK-core access from frontend; all access goes through `src/frontend/src/utils/api.ts`.

**Backend <-> Database boundary:**
- SQLAlchemy session boundary in `src/backend/db.py`.
- Relational metadata boundary in `src/backend/models.py`.
- Vector retrieval/storage boundary in `src/backend/services/vector_store_service.py`.

**Backend <-> External services boundary:**
- LLM provider via `langchain_openai.ChatOpenAI` in `src/backend/routers/agent.py` and runtime services.
- Wiki ingestion boundary in `src/backend/services/wiki_ingestion_service.py`.
- Optional tracing boundary via Langfuse settings/callbacks in `src/backend/config.py` and `src/backend/utils/langfuse_tracing.py`.

**Library SDK <-> HTTP SDK boundary:**
- In-process SDK API in `sdk/core/src/agent_search/public_api.py`.
- Generated OpenAPI transport client in `sdk/python/openapi_client/api/`.
- Backend HTTP contract source in `openapi.json`.

## Ownership and Coupling Hotspots

**Runtime duplication hotspot:**
- `src/backend/agent_search/` and `sdk/core/src/agent_search/` contain mirrored modules with near-identical contracts and behavior.
- Coupling impact: high change-amplification risk when runtime logic or schemas evolve.

**Orchestrator mega-module hotspot:**
- `src/backend/services/agent_service.py` owns orchestration, node invocation, state mutation, callbacks, and timeout logic.
- Coupling impact: high fan-in from routers/jobs/runtime wrapper and high fan-out to many services/nodes.

**In-memory job state hotspot:**
- Job registries in `src/backend/agent_search/runtime/jobs.py` and `src/backend/services/internal_data_jobs.py` are process-local.
- Coupling impact: lifecycle behavior is tightly coupled to single-process runtime assumptions.

**Contract drift hotspot (backend vs clients):**
- Backend schemas in `src/backend/schemas/` are separately represented in TS runtime guards (`src/frontend/src/utils/api.ts`) and generated Python models (`sdk/python/openapi_client/models/`).
- Coupling impact: schema changes require synchronized updates across three code surfaces.

---

*Architecture analysis: 2026-03-12*
