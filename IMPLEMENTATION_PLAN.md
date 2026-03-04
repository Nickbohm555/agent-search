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

- [ ] P0 - Replace projection scaffold with executable LangGraph orchestration using deep-agent pattern (`specs/orchestration-langgraph.md`).
  - Tasks:
  - Implement executable graph nodes/edges for decomposition -> tool selection -> retrieval -> validation loop -> synthesis.
  - Represent per-subquery execution via deep-agent subgraph/agent node(s).
  - Preserve graph state/timeline projection needed by downstream streaming and clients.
  - Verification (outcomes):
  - End-to-end `/api/agents/run` completes full graph path from decomposition through synthesis.
  - Each logical step executes in intended order, with validation loop behavior per subquery until sufficient or stop condition.
  - Deep-agent usage is observable in graph metadata/timeline payload.
  - Multi-subquery runs preserve subquery identity/order across assignments, retrieval outputs, and validation outputs.

- [ ] P0 - Add streaming backend heartbeat endpoint sourced from orchestration events (`specs/streaming-agent-heartbeat.md`).
  - Tasks:
  - Add streaming route (SSE or WebSocket) in `src/backend/routers/` and supporting stream schema contract in `src/backend/schemas/`.
  - Emit real-time events for subqueries, current step/progress, validation updates, and completion/final answer.
  - Handle disconnect/cancellation cleanly.
  - Verification (outcomes):
  - During a run, client receives progressive events (including subqueries) before completion event.
  - Event payload provides enough data for UI heartbeat (live step/progress + final answer).
  - Disconnect terminates stream cleanly without crashing backend execution path.
  - Event ordering/sequence fields remain deterministic and parseable across repeated runs.

- [ ] P0 - Expose orchestrated pipeline via FastMCP-compatible wrapper (`specs/mcp-exposure.md`).
  - Tasks:
  - Add MCP server/tool wrapper that accepts query input and delegates to shared orchestration path used by `/api/agents/run`.
  - Define stable MCP input/output schema for FastMCP client usage in Dockerized runtime.
  - Keep MCP streaming optional unless implemented in same increment.
  - Verification (outcomes):
  - FastMCP-style client invocation returns synthesized answer for a query.
  - MCP call delegates to orchestration path and returns equivalent answer semantics as `/api/agents/run`.
  - MCP tool contract (name + schema) is deterministic/stable across repeated calls.

- [ ] P1 - Migrate internal vectorization/retrieval to pgvector-native storage and similarity querying (`specs/data-loading-vectorization.md`, `specs/per-subquery-retrieval.md`).
  - Tasks:
  - Add Alembic migration for vector column/index changes in `src/backend/alembic/versions/`.
  - Persist embeddings as pgvector-compatible values at load time.
  - Move similarity ranking from Python JSON cosine loop to DB query path.
  - Keep deterministic embedding mode for CI tests.
  - Verification (outcomes):
  - Load API reports observable success/failure with doc/chunk counts and writes retrievable vectors.
  - Internal retrieval returns relevant chunks from loaded corpus through DB-backed vector similarity.
  - Empty/unrelated corpus yields deterministic empty/low-signal results without crashes.
  - `alembic upgrade head` creates expected structures and retrieval still works post-migration.

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

- [x] Confirmed no backend streaming route exists today (no SSE/WebSocket router under `src/backend/routers/`).
- [x] Confirmed no MCP/FastMCP wrapper exists today (`rg -n "mcp|fastmcp" src/backend`).
- [x] Confirmed runtime dependencies do not yet include `langchain`/`langgraph` in `src/backend/pyproject.toml`.
- [x] Confirmed orchestration is currently a scaffold projection, not executable LangGraph runtime graph (`src/backend/agents/langgraph_agent.py`).
- [x] Confirmed internal retrieval uses `embedding_json` + Python scoring instead of pgvector DB similarity (`src/backend/models.py`, `src/backend/services/internal_data_service.py`).
