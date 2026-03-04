# IMPLEMENTATION_PLAN

## Findings (2026-03-04)
- Repo is still scaffold-only relative to `specs/*`: health endpoint exists, agent runtime endpoint returns placeholder text, search endpoint is a stub, and no end-to-end RAG pipeline behavior is implemented.
- Existing `IMPLEMENTATION_PLAN.md` was stale: it claimed `/api/agent/plan` and decomposition/tool-selection tests were complete, but those files/routes/tests are not in `src/*`.
- `src/lib/*` does not exist in this repository, so shared-library review was performed on available shared utility areas (`src/backend/utils/*`, `src/frontend/src/utils/*`).

## Completed Baseline
- [x] Containerized scaffold stack (FastAPI + React/Vite + Postgres/pgvector + Alembic) is wired and boots.
- [x] Basic backend smoke coverage exists only for `GET /api/health`.

## Prioritized Remaining Tasks (Spec-Aligned)
- [ ] P0. Implement Langfuse SDK setup (`specs/langfuse-sdk-setup.md`).
  Verification requirements: with `LANGFUSE_ENABLED=true` and valid keys, app startup exposes a usable Langfuse handle on app state; with `LANGFUSE_ENABLED=false` or missing keys, app startup still succeeds with graceful no-op handle; an agent-run request can use the initialized handle without runtime error when enabled.

- [ ] P0. Implement agent-run tracing at execution boundary (`specs/agent-run-tracing.md`).
  Verification requirements: when tracing enabled, each `POST /api/agents/run` call creates a distinct trace/span containing run input query, agent identity, and run output; when tracing disabled, endpoint response remains unchanged and no traces are emitted; consecutive runs produce distinct observations.

- [ ] P0. Implement query decomposition + exclusive per-subquery tool selection contract (`specs/query-decomposition.md`, `specs/tool-selection-per-subquery.md`).
  Verification requirements: complex input query yields ordered, focused subqueries; each subquery gets exactly one assignment (`internal_rag` or `web_search`) with no dual assignment; decomposition and assignments are available to downstream pipeline state/stream consumers.

- [ ] P0. Implement data loading/vectorization for internal documents (`specs/data-loading-vectorization.md`).
  Verification requirements: load action can be triggered for at least one supported source and returns observable outcome (success/failure + counts); successful load populates vector store artifacts; subsequent internal retrieval can return relevant chunks from loaded corpus.

- [ ] P0. Implement web tools in Onyx-style split (`specs/web-search-onyx-style.md`).
  Verification requirements: `web.search`-equivalent returns links/snippets only (no full content); `web.open_url`-equivalent returns page content for selected URL; retrieval path can demonstrate search-then-open behavior with observable opened URLs/events.

- [ ] P1. Implement per-subquery retrieval executor (`specs/per-subquery-retrieval.md`).
  Verification requirements: given subquery + tool assignment, retrieval dispatches to correct path and returns consumable artifacts for validation; internal path returns only vector-store sourced content; web path uses search + open_url interaction.

- [ ] P1. Implement retrieval validation loop (`specs/retrieval-validation.md`).
  Verification requirements: each retrieval result is evaluated for sufficiency; insufficient results trigger at least one follow-up action (more retrieval or deeper read); loop stops deterministically (sufficient or stop condition) and emits observable status transitions for downstream streaming.

- [ ] P1. Implement answer synthesis from validated outputs only (`specs/answer-synthesis.md`).
  Verification requirements: synthesis consumes original query plus validated per-subquery outputs and returns one coherent final answer; synthesis step performs no direct retrieval; missing/low-confidence validated inputs still produce deterministic output contract.

- [ ] P1. Implement LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`).
  Verification requirements: graph includes decomposition, tool selection, retrieval, validation, and synthesis nodes; execution order reflects intended flow including per-subquery validation loop; graph state projection is available for streaming integration.

- [ ] P2. Implement streaming heartbeat service (`specs/streaming-agent-heartbeat.md`).
  Verification requirements: running a query yields real-time stream events that include subqueries and progress milestones; stream messages are sufficient for UI to render live state and final answer; typical run demonstrates reliable event delivery without dropped terminal state.

- [ ] P2. Implement TypeScript demo UI for load/run/stream (`specs/demo-ui-typescript.md`).
  Verification requirements: user can trigger load/vectorize and see success/error status; running a query shows streamed subqueries/progress and final answer; frontend remains TypeScript and includes at least one render/interaction test covering run/stream behavior.

- [ ] P2. Implement MCP wrapper exposure (`specs/mcp-exposure.md`).
  Verification requirements: MCP client can submit query and receive final answer end-to-end; MCP wrapper delegates to orchestration pipeline and returns synthesized output; contract is stable enough for repeatable client invocation tests.

## Required Test Buildout Policy for First Implementations
- [ ] For each new backend behavior above, add at least one backend smoke test first (`tests/api`, `@pytest.mark.smoke`) that verifies observable API outcome.
- [ ] For each new frontend UI behavior above, add at least one render/interaction test first that verifies user-visible behavior.
- [ ] Keep tests deterministic and outcome-based (no assertions on internal call graphs or hidden network dependencies).
