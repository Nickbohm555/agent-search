# IMPLEMENTATION_PLAN

- Scope: `backend: langchain / langgraph setup, MCP setup, streaming backend, vectorization, doc retrieval, subquestion decomp, agentic design` only.
- Status baseline: scaffold-only implementation exists for decomposition, tool assignment, retrieval, validation, synthesis, and tracing with deterministic tests.
- Inputs reviewed: `specs/*` (scoped docs), `src/backend/*`, `src/frontend/src/lib/*` (no repository-level `src/lib/*` exists).

## Highest Priority Remaining (Scoped)

- [x] P0 - Implement LangChain runtime boundary with graceful enabled/disabled behavior (`specs/langchain-runtime-setup.md`).
  - Tasks:
  - Added runtime dependencies (`langchain`, `langgraph`, `langchain-openai`) in backend project config and lockfile.
  - Added a single runtime integration boundary (`services/runtime_service.py`) initialized on app startup and consumed by orchestration through factory injection; routers remain provider-SDK agnostic.
  - Added env-driven runtime modes with deterministic local `stub` mode for CI and graceful disabled/misconfigured fallback behavior.
  - Verification (outcomes):
  - Startup succeeds with runtime enabled stub configuration and `/api/agents/run` executes through runtime path without wiring/import errors.
  - Startup succeeds when provider credentials/config are absent and run path deterministically falls back without crashing.
  - Added deterministic smoke tests for enabled (`stub`) and misconfigured (`langchain_openai` without key) modes; no external model calls in CI.

- [x] P0 - Replace projection scaffold with executable LangGraph orchestration using deep-agent pattern (`specs/orchestration-langgraph.md`).
  - Tasks:
  - Implemented executable LangGraph orchestration invocation for `/api/agents/run` (decomposition -> tool selection -> subquery execution -> synthesis).
  - Represented per-subquery execution via deep-agent LangGraph subgraph (`SubQueryExecutionAgent`) for retrieval -> validation.
  - Preserved and expanded graph state/timeline projection for downstream streaming/client consumers (includes execution mode and deep-agent details).
  - Verification (outcomes):
  - `docker compose exec backend uv run pytest` passes; orchestration smoke verifies graph metadata (`execution=langgraph_invoke`), ordered timeline, and per-subquery retrieval/validation counts.
  - Validation loop behavior per subquery remains intact (including deterministic insufficient internal case at 2 attempts).
  - Deep-agent usage is observable in graph metadata (`deep_agents.kind=langgraph-subgraph`) and timeline details (`deep_agent=subquery_execution_agent`).
  - Multi-subquery runs preserve subquery identity/order across assignments, retrieval outputs, and validation outputs.

- [x] P0 - Add streaming backend heartbeat endpoint sourced from orchestration events (`specs/streaming-agent-heartbeat.md`).
  - Tasks:
  - Added SSE streaming route `POST /api/agents/run/stream` in `src/backend/routers/agent.py`.
  - Reused orchestration output (`graph_state.timeline`) to emit deterministic heartbeat events plus `sub_queries`, `tool_assignments`, `retrieval_result`, `validation_result`, and `completed`.
  - Added stream event builder in `src/backend/services/agent_service.py` so stream payloads and ordering are stable and parseable.
  - Added smoke coverage for stream event progression and early client disconnect behavior (`src/backend/tests/api/test_streaming_agent_heartbeat.py`).
  - Verification (outcomes):
  - `docker compose exec backend uv run pytest` passes with new streaming smoke tests (`30 passed`).
  - Stream emits progressive events before completion and includes subqueries, timeline-derived heartbeats, retrieval/validation updates, and final answer payload.
  - Event ordering is deterministic with monotonic sequence values.
  - Early client disconnect test passes without backend errors.

- [x] P0 - Expose orchestrated pipeline via FastMCP-compatible wrapper (`specs/mcp-exposure.md`).
  - Tasks:
  - Added MCP JSON-RPC wrapper endpoint `POST /mcp` with MCP-compatible methods: `initialize`, `tools/list`, and `tools/call`.
  - Added stable MCP tool contract `agent.run` with deterministic `inputSchema` and deterministic server protocol metadata.
  - Wired `tools/call` delegation to shared orchestration path by invoking `run_runtime_agent` (same path used by `/api/agents/run`) with app runtime/tracing handles.
  - Added deterministic backend smoke coverage for MCP initialization/tool listing contract and tool-call delegation equivalence.
  - Verification (outcomes):
  - `POST /mcp` `tools/call` with tool `agent.run` returns synthesized text content for a query and includes structured pipeline output payload.
  - For the same query, MCP `tools/call` returns `structuredContent` equivalent to `/api/agents/run` response semantics (same orchestration data).
  - MCP tool contract remains deterministic: tool name `agent.run` with fixed JSON schema (`query` non-empty string, no additional properties).
  - Validation run after fresh environment reset succeeded:
    - `docker compose down -v --rmi all`
    - `docker compose build`
    - `docker compose up -d`
    - `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
    - `docker compose exec backend uv run pytest` -> `32 passed`
    - `docker compose exec frontend npm run test` -> `25 passed`
    - `docker compose exec frontend npm run typecheck` -> pass

- [x] P1 - Migrate internal vectorization/retrieval to pgvector-native storage and similarity querying (`specs/data-loading-vectorization.md`, `specs/per-subquery-retrieval.md`).
  - Tasks:
  - Added Alembic migration `0003_pgvector_embed` to enable `vector` extension, add `embedding_vector vector(16)`, backfill from legacy JSON, create ivfflat cosine index, and remove `embedding_json`.
  - Updated ORM model to store chunk embeddings in pgvector-compatible `embedding_vector` (with SQLite JSON variant for deterministic smoke tests).
  - Updated load path to persist embeddings to `embedding_vector`.
  - Updated retrieval path to use DB-side cosine similarity ordering when running on PostgreSQL and preserved deterministic SQLite fallback scoring for test determinism.
  - Added smoke coverage for empty corpus retrieval and unrelated-query low-signal behavior.
  - Verification (outcomes):
  - Fresh reset/build/start completed:
    - `docker compose down -v --rmi all`
    - `docker compose build`
    - `docker compose up -d`
  - Health + required tests passed:
    - `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
    - `docker compose exec backend uv run pytest` -> `34 passed`
    - `docker compose exec frontend npm run test` -> `25 passed`
    - `docker compose exec frontend npm run typecheck` -> pass
  - Postgres structures verified:
    - `docker compose exec db psql -U agent_user -d agent_search -c "\\dx"` shows `vector` extension installed.
    - `docker compose exec db psql -U agent_user -d agent_search -c "\\d internal_document_chunks"` shows `embedding_vector vector(16)` + ivfflat index `ix_internal_document_chunks_embedding_vector_ivfflat`.
    - `docker compose exec backend uv run alembic current` -> `0003_pgvector_embed (head)`.
  - Live API retrieval verified against Postgres-backed store after load (`/api/internal-data/load` then `/api/internal-data/retrieve`) with retrievable vector-scored results.

## Build Tradeoffs

- Chosen + why:
  - Kept a deterministic SQLite fallback scoring path in `retrieve_internal_data` while moving PostgreSQL retrieval to DB-side pgvector cosine ordering. This preserves fast, isolated smoke tests without requiring Postgres for every test fixture.
- Alternatives considered:
  - Migrate all tests to Postgres-backed fixtures only (higher fidelity, slower and heavier test setup).
  - Force Postgres-only retrieval path and drop SQLite fixture support (would break existing deterministic in-memory test flow).
- References for the human:
  - Code locations: `src/backend/services/internal_data_service.py`, `src/backend/models.py`, `src/backend/alembic/versions/0003_pgvector_internal_embeddings.py`, `src/backend/tests/api/test_internal_data_loading.py`.
- HUMAN-ONLY NOTES:
  - Loop run commit message should reference pgvector migration and retrieval path update.
  - Key symbols: `InternalDocumentChunk.embedding_vector`, `retrieve_internal_data`, Alembic revision `0003_pgvector_embed`.

- [ ] P1 - Improve subquestion decomposition robustness for agentic routing (`specs/query-decomposition.md`, `specs/tool-selection-per-subquery.md`).
  - Tasks:
  - Improve decomposition quality for complex/mixed-intent prompts while preserving deterministic behavior in tests.
  - Ensure each produced subquery remains single-path answerable (internal OR web, not both).
  - Keep subqueries consistently exposed in run response, graph state, stream events, and MCP metadata (if enabled).
  - Verification (outcomes):
  - Complex queries produce focused subqueries with no mixed-domain single subquery.
  - Every subquery maps to exactly one tool assignment.
  - Duplicate-heavy phrasing does not produce duplicate/empty subqueries.
  - Subqueries are visible to downstream consumers (run payload and enabled stream/MCP surfaces).

- [ ] P1 - Expand retrieval-validation observability and control-loop outputs (`specs/per-subquery-retrieval.md`, `specs/retrieval-validation.md`, `specs/answer-synthesis.md`).
  - Tasks:
  - Preserve strict path fidelity: internal-assigned subqueries use internal store only; web-assigned subqueries use search+open_url flow.
  - Expose validation attempt/follow-up metadata as explicit per-subquery outputs for stream/MCP/timeline consumers.
  - Ensure synthesis consumes validated outputs only.
  - Verification (outcomes):
  - Internal-assigned subquery retrieval returns internal evidence from loaded store.
  - Web-assigned subquery executes search -> open_url with opened page evidence.
  - Insufficient evidence triggers at least one follow-up action and stops with explicit reason.
  - Final answer reflects validated results only (insufficient subqueries remain flagged as insufficient evidence).

## Completed Baseline (Scoped)

- [x] Scaffold decomposition, one-tool-per-subquery assignment, retrieval, validation loop, and synthesis are implemented and smoke-tested.
- [x] Internal data load/retrieve endpoints exist with observable load counts and deterministic retrieval behavior.
- [x] Langfuse SDK scaffold and agent-run tracing baseline exist with enabled/disabled smoke coverage.
- [x] LangChain runtime boundary is wired through startup/app state and orchestration with deterministic enabled/disabled smoke coverage.

## Gap Confirmation (Code Search Evidence)

- [x] Confirmed backend streaming route now exists at `POST /api/agents/run/stream` with SSE `text/event-stream` output.
- [x] Confirmed MCP wrapper now exists at `POST /mcp` with JSON-RPC methods (`initialize`, `tools/list`, `tools/call`) and shared orchestration delegation.
- [x] Confirmed runtime dependencies include `langchain`/`langgraph`/`langchain-openai` in `src/backend/pyproject.toml`.
- [x] Confirmed orchestration now executes via compiled LangGraph runtime graphs (top-level orchestration + subquery deep-agent subgraph) in `src/backend/agents/langgraph_agent.py`.
- [x] Confirmed internal retrieval uses `embedding_json` + Python scoring instead of pgvector DB similarity (`src/backend/models.py`, `src/backend/services/internal_data_service.py`).
