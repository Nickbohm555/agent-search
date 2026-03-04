# IMPLEMENTATION_PLAN

- Scope: `backend: langchain / langgraph setup, MCP setup, streaming backend, vectorization, doc retrieval, subquestion decomp, agentic design` only.
- Project status: scaffold-only, with deterministic backend stubs and smoke tests already present for baseline pipeline steps.
- Inputs reviewed this run: `specs/*`, existing `IMPLEMENTATION_PLAN.md`, `src/backend/*`, `src/frontend/src/lib/*` (no repository-level `src/lib/*` exists).

## Highest Priority Incomplete (Scoped)

- [ ] P0 - Add real LangChain runtime boundary with graceful enabled/disabled modes (`specs/langchain-runtime-setup.md`).
  - Implementation tasks:
  - Add runtime deps in backend (`langchain`, `langgraph`, provider adapter) and update `uv.lock`.
  - Create one runtime integration boundary (service/app-state handle) that orchestration consumes; routers stay SDK-agnostic.
  - Add env-driven runtime mode with deterministic stub path for tests/no-network CI.
  - Verification requirements:
  - Smoke: runtime-enabled config starts backend and `/api/agents/run` executes through runtime path without wiring/import failures.
  - Smoke: runtime disabled or missing credentials still allows startup and returns deterministic non-crashing run contract (or explicit controlled error contract).
  - Tests: both modes covered with deterministic stubs/mocks and zero hidden external model calls.

- [ ] P0 - Replace LangGraph projection scaffold with executable LangGraph graph using deep-agent subgraph pattern (`specs/orchestration-langgraph.md`).
  - Implementation tasks:
  - Implement LangGraph nodes/edges for decomposition, tool selection, per-subquery retrieval, validation loop, and synthesis.
  - Model subquery execution as deep-agent/subgraph behavior and preserve graph-state projection for downstream consumers.
  - Keep state payloads consistent: subqueries, assignments, retrieval outputs, validation outputs, synthesis output.
  - Verification requirements:
  - Smoke: full decomposition -> tool selection -> retrieval -> validation -> synthesis run completes and returns final answer.
  - Smoke: each logical step appears and executes in intended order; validation loops per subquery until sufficient or stop condition.
  - Smoke: deep-agent/subgraph presence is observable in graph metadata/timeline.
  - Edge-case: multi-subquery runs preserve identity/order alignment across subqueries, assignments, retrieval, and validation records.

- [ ] P0 - Add backend streaming heartbeat endpoint powered by orchestration events (`specs/streaming-agent-heartbeat.md`).
  - Implementation tasks:
  - Add streaming API route (SSE or WebSocket) under `src/backend/routers/` and event schema under `src/backend/schemas/`.
  - Emit incremental events for subqueries, active step/progress, validation updates, and completion payload.
  - Handle cancellation/disconnect cleanly.
  - Verification requirements:
  - Smoke: run emits subquery/progress events before completion event (not completion-only).
  - Smoke: stream payload is sufficient for UI heartbeat: current step/progress plus final answer payload.
  - Edge-case: client disconnect does not crash worker/request handling and stream terminates cleanly.
  - Contract: ordered events with stable sequence fields are parseable in tests.

- [ ] P0 - Expose pipeline via FastMCP-compatible wrapper and transport (`specs/mcp-exposure.md`).
  - Implementation tasks:
  - Add MCP server/tool entrypoint that accepts query input and delegates to same orchestration used by `/api/agents/run`.
  - Define stable MCP request/response contract for FastMCP client use; wire runtime entrypoint for Dockerized usage.
  - Keep streaming-over-MCP optional unless explicitly added.
  - Verification requirements:
  - Smoke: FastMCP-style client invocation returns synthesized answer for provided query.
  - Smoke: MCP output semantics match `/api/agents/run` output for equivalent query input.
  - Contract: tool name and input/output schema are deterministic and stable for repeated client calls.

- [ ] P1 - Move vectorization/retrieval to pgvector-native storage and DB similarity search (`specs/data-loading-vectorization.md`, `specs/per-subquery-retrieval.md`).
  - Implementation tasks:
  - Add vector column/index schema changes with Alembic migration in same change.
  - Persist embeddings in pgvector format at load time; execute similarity ranking in DB (not Python JSON cosine pass).
  - Keep deterministic embedding mode for CI/test environments.
  - Verification requirements:
  - Smoke: load endpoint reports observable load outcomes (success + doc/chunk counts) and stores retrievable vectors.
  - Smoke: internal retrieval after load returns relevant chunks from loaded corpus.
  - Edge-case: empty/unrelated corpus returns deterministic empty-or-low-signal results without crashes.
  - Migration: `alembic upgrade head` produces required vector structures and retrieval remains functional after migration.

- [ ] P1 - Improve subquestion decomposition quality and consistency across agentic surfaces (`specs/query-decomposition.md`).
  - Implementation tasks:
  - Improve decomposition for complex mixed-intent prompts while keeping deterministic tests feasible.
  - Ensure subqueries propagate consistently to run response, graph state, stream events, and MCP metadata (if exposed).
  - Verification requirements:
  - Smoke: complex mixed-domain query yields focused single-path subqueries (each answerable by one retrieval path).
  - Smoke: subqueries are visible in all enabled downstream surfaces (run response, stream, MCP metadata if implemented).
  - Edge-case: duplicate-heavy phrasing does not create duplicate/empty subqueries.

- [ ] P1 - Expand per-subquery retrieval/validation observability for agentic control loops (`specs/per-subquery-retrieval.md`, `specs/retrieval-validation.md`).
  - Implementation tasks:
  - Preserve strict retrieval-path fidelity per assignment (`internal` only internal store; `web` follows search+open_url flow).
  - Expose retry/follow-up validation actions as explicit per-subquery state for stream/MCP and timeline consumers.
  - Verification requirements:
  - Smoke: internal-assigned subquery returns internal evidence without requiring web artifacts.
  - Smoke: web-assigned subquery performs search -> open_url with observable opened URL/page content outputs.
  - Smoke: insufficient evidence triggers at least one follow-up action and ends with explicit stop reason.
  - Contract: per-subquery validation status, attempt count, and follow-up actions are visible in response/timeline/events.

## Scoped Items Already Complete (Baseline Scaffold)

- [x] Baseline decomposition output exists and is smoke-tested (`specs/query-decomposition.md`).
- [x] Baseline one-tool-per-subquery assignment exists and is smoke-tested (`specs/tool-selection-per-subquery.md`).
- [x] Baseline web tools (`search` + `open_url`) exist and are smoke-tested (`specs/web-search-onyx-style.md`).
- [x] Baseline per-subquery retrieval and validation loop exist and are smoke-tested (`specs/per-subquery-retrieval.md`, `specs/retrieval-validation.md`).
- [x] Baseline synthesis output exists and is smoke-tested (`specs/answer-synthesis.md`).
- [x] Baseline internal load/retrieve endpoints with observable counts exist (currently JSON embeddings + Python scoring, not pgvector-native retrieval).
- [x] Langfuse SDK scaffolding and agent-run tracing baseline exist (`specs/langfuse-sdk-setup.md`, `specs/agent-run-tracing.md`).

## Gap Confirmation (Code Search)

- Missing runtime deps for LangChain/LangGraph in [pyproject.toml](/Users/nickbohm/Desktop/Tinkering/agent-search/src/backend/pyproject.toml).
- Current graph implementation in [langgraph_agent.py](/Users/nickbohm/Desktop/Tinkering/agent-search/src/backend/agents/langgraph_agent.py) is a deterministic projection scaffold, not an executable LangGraph runtime graph.
- No streaming endpoint in backend routers for agent run heartbeat (no SSE/WebSocket route under [routers](/Users/nickbohm/Desktop/Tinkering/agent-search/src/backend/routers)).
- No MCP/FastMCP wrapper found in backend source (`rg -n "mcp|fastmcp"` in `src/backend`).
- Internal chunk vectors in [models.py](/Users/nickbohm/Desktop/Tinkering/agent-search/src/backend/models.py) and [internal_data_service.py](/Users/nickbohm/Desktop/Tinkering/agent-search/src/backend/services/internal_data_service.py) use `embedding_json` and in-Python similarity scoring rather than pgvector DB similarity queries.
