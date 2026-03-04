# IMPLEMENTATION_PLAN

## Status Snapshot (2026-03-04)
- Complete: scaffold runtime only (`/api/health`, `/api/search-skeleton`, `/api/agents/runtime`, `/api/agents/run`), basic FastAPI + React wiring, baseline migration file.
- Incomplete: all product specs in `specs/*` beyond scaffold behavior.
- Code-confirmed gaps:
- `src/lib/*` does not exist yet.
- `LangGraphAgentScaffold` is placeholder-only (`compiled: False`).
- No decomposition/selection/retrieval/validation/synthesis pipeline exists.
- No streaming endpoint, no MCP server/wrapper, no web-search tool pair.
- Langfuse is config scaffold only; no SDK dependency/client initialization.
- Current test coverage is only backend health smoke + frontend scaffold render test.

## Completed Items
- [x] Scaffold health endpoint and smoke test.
- [x] Scaffold backend routers/services for search and runtime agent placeholders.
- [x] Scaffold frontend TypeScript app and basic render test.

## Prioritized Remaining Tasks (Yet To Be Implemented)
- [ ] P0. Langfuse SDK setup (`specs/langfuse-sdk-setup.md`) - Incomplete
  - Gap confirmation: `src/backend/pyproject.toml` has no Langfuse dependency; `initialize_langfuse_tracing()` returns placeholder handle only.
  - Verification requirements (outcome-based):
  - Backend startup test: with `LANGFUSE_ENABLED=true` and valid keys, app starts and exposes usable Langfuse handle on `app.state`.
  - Backend startup test: with `LANGFUSE_ENABLED=false` or missing keys, app still starts and exposes graceful no-op handle.
  - Request-path test: tracing-capable path can create trace/span without runtime error when enabled.

- [ ] P0. Agent run tracing at execution boundary (`specs/agent-run-tracing.md`) - Incomplete
  - Gap confirmation: `run_runtime_agent()` has no trace/span instrumentation.
  - Verification requirements (outcome-based):
  - Integration test: posting to `/api/agents/run` with tracing enabled creates an observation containing query, agent name, and output.
  - Regression test: with tracing disabled, endpoint response contract is unchanged and no tracing side effects occur.
  - Integration test: consecutive runs produce distinct observations.

- [ ] P0. Query decomposition (`specs/query-decomposition.md`) - Incomplete
  - Gap confirmation: no decomposition service/schema/state contract for sub-queries.
  - Verification requirements (outcome-based):
  - Behavior test: complex query yields at least one focused sub-query.
  - Behavior test: each sub-query is independently answerable by one tool domain (internal or web).
  - Integration test: produced sub-queries are exposed for downstream orchestration and stream projection.

- [ ] P0. Tool selection per sub-query (exclusive choice) (`specs/tool-selection-per-subquery.md`) - Incomplete
  - Gap confirmation: no component assigning `internal RAG` vs `web search` per sub-query.
  - Verification requirements (outcome-based):
  - Behavior test: each sub-query receives exactly one assignment.
  - Behavior test: no sub-query receives both assignments.
  - Integration test: assignments are available to retrieval/orchestration (and stream projection if emitted).

- [ ] P0. Data loading + vectorization for internal RAG (`specs/data-loading-vectorization.md`) - Incomplete
  - Gap confirmation: no ingest/load API, no chunk/embed/persist flow, no vectorized corpus schema/models.
  - Verification requirements (outcome-based):
  - Smoke test: load/vectorize can be triggered for at least one supported source.
  - Integration test: after successful load, internal retrieval returns content from loaded corpus for relevant queries.
  - Behavior test: load result is observable (success/failure + counts/status payload for UI).

- [ ] P0. Web search tool pair (`specs/web-search-onyx-style.md`) - Incomplete
  - Gap confirmation: no `web.search` and `web.open_url` interfaces.
  - Verification requirements (outcome-based):
  - Smoke test: `web.search` returns links/snippets metadata only (no full-page body).
  - Smoke test: `web.open_url` returns full/main page content for a URL.
  - Integration test: agent can do search -> choose URLs -> open selected pages; opened URLs are observable.
  - Integration test: tool-selection “web” assignment executes via this tool pair.

- [ ] P1. Per-subquery retrieval executor (`specs/per-subquery-retrieval.md`) - Incomplete
  - Gap confirmation: no retrieval executor consuming `(sub-query, tool assignment)`.
  - Verification requirements (outcome-based):
  - Integration test: assigned internal/web path executes and returns retrievable content.
  - Behavior test: internal retrieval returns only from loaded internal store.
  - Behavior test: web retrieval follows search + open_url pattern.
  - Contract test: retrieval output is consumable by validation stage.

- [ ] P1. Retrieval validation loop (`specs/retrieval-validation.md`) - Incomplete
  - Gap confirmation: no sufficiency check or retry/deepen loop.
  - Verification requirements (outcome-based):
  - Behavior test: each retrieval result is evaluated for sufficiency.
  - Behavior test: insufficient result triggers follow-up retrieval/deepen action.
  - Integration test: loop ends with either sufficient result or deterministic stop condition.
  - Contract test: validation outcome is emitted for synthesis (and stream-visible state if enabled).

- [ ] P1. Answer synthesis (`specs/answer-synthesis.md`) - Incomplete
  - Gap confirmation: no synthesis component consuming validated sub-query outputs.
  - Verification requirements (outcome-based):
  - Behavior test: original query + validated sub-query outputs produce one final answer.
  - Guardrail test: synthesis uses validated outputs only (no direct retrieval side path).
  - Quality test: final answer coherently addresses original query (rubric/assertion fixture).

- [ ] P1. LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`) - Incomplete
  - Gap confirmation: runtime graph is scaffold placeholder only.
  - Verification requirements (outcome-based):
  - Integration test: end-to-end flow runs as LangGraph from decomposition through synthesis.
  - Integration test: required stages execute in intended order, including per-subquery validation loop.
  - Structural test: deep-agent composition is present for subquery/tool execution path.
  - Integration test: graph state/projection is available for streaming consumer.

- [ ] P2. Streaming agent heartbeat (`specs/streaming-agent-heartbeat.md`) - Incomplete
  - Gap confirmation: no SSE/WebSocket endpoint or event contract.
  - Verification requirements (outcome-based):
  - Integration test: query run emits streamed updates including sub-queries as they are generated.
  - Integration test: stream includes enough progress state for live UI heartbeat and terminal completion.
  - Reliability test: typical run shows ordered, observable progress and completion.

- [ ] P2. Demo UI (TypeScript) (`specs/demo-ui-typescript.md`) - Incomplete
  - Gap confirmation: current UI is static scaffold; no load trigger, run flow, streaming view, or final answer rendering.
  - Verification requirements (outcome-based):
  - Frontend interaction test: user triggers load/vectorize and sees clear success/error state.
  - Frontend interaction test: running query renders streamed sub-queries in near real time.
  - Frontend interaction test: progress heartbeat and final answer are rendered.
  - Build-quality checks: tests + typecheck + build remain green.

- [ ] P2. MCP exposure (`specs/mcp-exposure.md`) - Incomplete
  - Gap confirmation: no MCP server/tool wrapper in codebase.
  - Verification requirements (outcome-based):
  - Integration test: MCP client sends query and receives final synthesized answer.
  - Integration test: MCP invocation delegates to same orchestration pipeline.
  - Contract stability test: repeated invocations preserve response schema and success behavior.

- [ ] P2. Scaffold endpoint smoke coverage expansion (project hardening) - Incomplete
  - Gap confirmation: only `/api/health` has smoke coverage.
  - Verification requirements (outcome-based):
  - Smoke test: `GET /api/search-skeleton` returns expected scaffold contract.
  - Smoke test: `GET /api/agents/runtime` returns non-empty `name` and `version`.
  - Smoke test: `POST /api/agents/run` valid query returns non-empty `agent_name` and `output`.
  - Edge smoke test: invalid/empty query returns schema-validation 4xx.

## Cross-Cutting Delivery Rules
- [ ] Each first backend behavior ships with at least one deterministic smoke/integration test.
- [ ] Each first frontend behavior ships with at least one deterministic render/interaction test.
- [ ] Tests validate externally observable outcomes, not implementation internals.
- [ ] No hidden network dependency in CI tests; external integrations must be mocked/faked deterministically.
- [ ] Any DB schema change includes Alembic migration in `src/backend/alembic/versions/`.
- [ ] Tracing integration remains isolated to startup/services (`src/backend/observability/*`), not router-level vendor coupling.
