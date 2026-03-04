# IMPLEMENTATION_PLAN

- Scope: `backend: langchain / langgraph setup, MCP setup, streaming backend, vectorization, doc retrieval, subquestion decomp, agentic design` only.
- Project status reality check: backend already has scaffolded decomposition/tool-selection/retrieval/validation/synthesis endpoints and smoke tests; remaining work is runtime-grade execution and exposure.
- Inputs reviewed: `specs/*`, existing `IMPLEMENTATION_PLAN.md`, `src/backend/*`, `src/frontend/src/lib/*` (no top-level `src/lib/*` exists).

## Highest Priority Incomplete Tasks

- [ ] P0 - Add LangChain/LangGraph runtime boundary and environment wiring (`specs/langchain-runtime-setup.md`).
  - Implementation tasks:
  - Add runtime dependencies (`langchain`, `langgraph`, provider adapter package) in `src/backend/pyproject.toml` and lockfile.
  - Introduce a single runtime integration boundary (service/app-state handle) consumed by agent orchestration; routers remain SDK-agnostic.
  - Add explicit enabled/disabled runtime mode from env with deterministic stub mode for CI/local no-network runs.
  - Verification requirements (derive from spec acceptance criteria):
  - Smoke: with runtime-enabled config and stub provider, backend starts and `/api/agents/run` executes without runtime wiring/import errors.
  - Smoke: with runtime disabled/missing credentials, backend still starts and `/api/agents/run` returns deterministic non-crashing contract (or controlled explicit error contract).
  - Test: enabled and disabled modes are both covered with deterministic stubs/mocks (no hidden external model calls in CI).

- [ ] P0 - Replace scaffold orchestration with executable LangGraph flow using deep-agent subgraph execution (`specs/orchestration-langgraph.md`).
  - Implementation tasks:
  - Build real LangGraph nodes/edges for decomposition, tool selection, retrieval, validation loop, and synthesis.
  - Model per-subquery execution as deep-agent/subgraph behavior and preserve projection of graph state for downstream consumers.
  - Ensure state carries subqueries, assignments, retrieval artifacts, validation outcomes, and synthesis outputs.
  - Verification requirements:
  - Smoke: full decomposition->tool-selection->retrieval->validation->synthesis pipeline executes as LangGraph and returns final answer.
  - Smoke: each logical step executes in intended order; validation loops per subquery until sufficient or stopping condition.
  - Smoke: deep-agent/subgraph participation is observable in returned graph state/timeline.
  - Edge-case: multi-subquery runs preserve index/identity consistency across subqueries, assignments, retrieval results, and validation results.

- [ ] P0 - Implement streaming heartbeat backend endpoint driven by orchestration state (`specs/streaming-agent-heartbeat.md`).
  - Implementation tasks:
  - Add streaming route (SSE or WebSocket) under `src/backend/routers/` with schema contract under `src/backend/schemas/`.
  - Emit incremental events from orchestration: subqueries, active step/progress, validation status transitions, completion payload.
  - Handle client disconnect/cancellation safely.
  - Verification requirements:
  - Smoke: streaming run emits subquery updates while run is in progress (not only terminal payload).
  - Smoke: stream provides enough information for UI heartbeat (current step/progress and final completion payload).
  - Edge-case: disconnecting the client does not crash backend and stream closes cleanly.
  - Contract: event ordering and sequence identifiers are stable/parseable for typical runs.

- [ ] P0 - Expose pipeline through FastMCP-compatible MCP wrapper (`specs/mcp-exposure.md`).
  - Implementation tasks:
  - Add MCP server/tool wrapper that accepts query input and delegates to the same orchestration path as `/api/agents/run`.
  - Define stable request/response contract for client usage; wire through Docker service/runtime path as needed.
  - Keep optional MCP streaming separate unless explicitly implemented.
  - Verification requirements:
  - Smoke: MCP client invocation returns final synthesized answer for a query.
  - Smoke: MCP answer semantics match API pipeline output for equivalent input.
  - Contract: tool name and request/response schema are deterministic and integration-stable for FastMCP client usage.

- [ ] P1 - Migrate internal vectorization/retrieval to pgvector-native storage and similarity querying (`specs/data-loading-vectorization.md`, `specs/per-subquery-retrieval.md`).
  - Implementation tasks:
  - Add schema changes for vector column/index and keep existing content metadata; ship Alembic migration in same change.
  - Update load path to persist vector embeddings in pgvector-backed form and retrieval path to query similarity in DB.
  - Maintain deterministic test mode for embeddings so CI remains network-free.
  - Verification requirements:
  - Smoke: load endpoint vectorizes and stores chunks in DB-backed vector store and returns observable outcome counts.
  - Smoke: after load, internal-assigned subquery retrieval returns relevant chunk(s) from loaded corpus.
  - Edge-case: empty or unrelated corpus yields deterministic empty/low-signal retrieval contract without crashing.
  - Migration: Alembic upgrade creates required vector structures and retrieval still functions post-migration.

- [ ] P1 - Strengthen subquestion decomposition quality and propagation (`specs/query-decomposition.md`).
  - Implementation tasks:
  - Improve decomposition for complex mixed-intent prompts (while preserving deterministic testability).
  - Ensure decomposed subqueries propagate consistently to run response, graph state, streaming events, and MCP response metadata if exposed.
  - Verification requirements:
  - Smoke: complex mixed-domain query yields focused subqueries where each is answerable by one retrieval path.
  - Smoke: subqueries are visible to downstream pipeline consumers (run response + streaming events; MCP metadata if implemented).
  - Edge-case: connector-heavy or duplicated phrasing does not emit duplicate/empty subqueries.

- [ ] P1 - Expand per-subquery retrieval/validation observability for agentic control surfaces (`specs/per-subquery-retrieval.md`, `specs/retrieval-validation.md`).
  - Implementation tasks:
  - Preserve strict retrieval-path fidelity by tool assignment (`internal` uses internal store only; `web` uses search+open_url behavior).
  - Surface validation retries/follow-up actions as explicit per-subquery state/events for stream/MCP consumers.
  - Verification requirements:
  - Smoke: internal-assigned subquery returns internal corpus evidence and does not require web fields to satisfy retrieval.
  - Smoke: web-assigned subquery follows search->open_url behavior with observable opened URL/page outputs.
  - Smoke: insufficient evidence triggers at least one follow-up action then terminates with explicit stop reason.
  - Contract: per-subquery validation status, attempts, and follow-up actions are observable in timeline/event payloads.

## Scoped Items Confirmed Complete

- [x] Baseline decomposition exists and has smoke coverage (`specs/query-decomposition.md` baseline outcomes).
- [x] Baseline one-tool-per-subquery assignment exists and has smoke coverage (`specs/tool-selection-per-subquery.md`).
- [x] Baseline web tools (`search` + `open_url`) exist and have smoke coverage (`specs/web-search-onyx-style.md`).
- [x] Baseline per-subquery retrieval and validation loop behavior exist and have smoke coverage (`specs/per-subquery-retrieval.md`, `specs/retrieval-validation.md`).
- [x] Baseline synthesis step exists and has smoke coverage (`specs/answer-synthesis.md`).
- [x] Baseline internal load/retrieve endpoints with observable counts exist (current storage is JSON embedding text, not pgvector-native retrieval).
- [x] Langfuse setup and agent-run tracing baselines exist as adjacent infrastructure (`specs/langfuse-sdk-setup.md`, `specs/agent-run-tracing.md`).

## Gap Confirmation Notes (Code Search)

- LangChain/LangGraph runtime dependencies are not present in `src/backend/pyproject.toml`.
- Current `src/backend/agents/langgraph_agent.py` is a deterministic scaffold/projection, not executable LangGraph runtime wiring.
- No streaming run endpoint exists in backend routers (no SSE/WebSocket route for `/api/agents/*`).
- No MCP/FastMCP server wrapper is present in backend source.
- Internal chunk vectors are persisted as `embedding_json` text and scored in Python rather than pgvector DB similarity queries.
