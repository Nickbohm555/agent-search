# IMPLEMENTATION_PLAN

## Audit Snapshot (2026-03-04)
- Sources reviewed: `specs/*`, `IMPLEMENTATION_PLAN.md`, `src/backend/*`, `src/frontend/*`.
- `src/lib/*` is not present in this repository.
- Shared utility roots currently are:
  - backend: `src/backend/utils/*`
  - frontend: `src/frontend/src/utils/*`
- Current implementation remains scaffold-only:
  - Backend endpoints implemented: `GET /api/health`, `GET /api/search-skeleton`, `GET /api/agents/runtime`, `POST /api/agents/run`.
  - Frontend implemented: static scaffold view only.
  - Observability implemented: env parsing + startup handle placeholder only.

## Completed
- [x] Scaffold stack wiring is present (`docker-compose.yml`, Dockerfiles, FastAPI app, Vite app).
- [x] Health endpoint contract exists with smoke test (`src/backend/tests/api/test_health.py`).
- [x] Frontend baseline render test exists (`src/frontend/src/App.test.tsx`).

## Prioritized Remaining Work (Spec-Aligned)

- [ ] P0. Add scaffold smoke tests for existing API endpoints (baseline contract coverage)
  - Gaps confirmed by code search: only `/api/health` has smoke coverage.
  - Required verification outcomes:
    - Backend smoke test: `GET /api/search-skeleton` returns HTTP 200 with `{"status":"scaffold","message":"search pipeline not implemented yet"}`.
    - Backend smoke test: `GET /api/agents/runtime` returns HTTP 200 with non-empty `name` and non-empty semantic-ish `version`.
    - Backend smoke test: `POST /api/agents/run` with valid query returns HTTP 200 with non-empty `agent_name` and non-empty `output`.

- [ ] P0. Implement Langfuse SDK setup (`specs/langfuse-sdk-setup.md`)
  - Gaps confirmed by code search: no Langfuse SDK dependency; `initialize_langfuse_tracing()` returns placeholder handle only.
  - Required verification outcomes:
    - Backend smoke test: with `LANGFUSE_ENABLED=true` + valid keys, app startup yields usable `app.state.langfuse` handle for creating observations.
    - Backend smoke test: with `LANGFUSE_ENABLED=false` or missing keys, app startup succeeds and handle is graceful no-op.
    - Backend smoke/integration test: tracing-capable path can create a trace/span through initialized handle without runtime error when enabled.

- [ ] P0. Instrument agent-run boundary tracing (`specs/agent-run-tracing.md`)
  - Gaps confirmed by code search: `run_runtime_agent()` has no tracing instrumentation.
  - Required verification outcomes:
    - Backend smoke/integration test: when tracing enabled, `POST /api/agents/run` records query input, agent identity, and output in one run trace/span.
    - Backend smoke test: when tracing disabled, endpoint response is unchanged from scaffold behavior and tracing emits nothing.
    - Backend smoke/integration test: consecutive runs produce distinct traces/spans.

- [ ] P0. Implement data loading and vectorization for internal corpus (`specs/data-loading-vectorization.md`)
  - Gaps confirmed by code search: no loader API/service/model; no chunk/embed/persist pipeline.
  - Required verification outcomes:
    - Backend smoke test: load/vectorize trigger for at least one internal source returns observable outcome (`success`/`error`) plus count metadata.
    - Backend integration test: successful load produces persisted vector-store records tied to source documents.
    - Backend integration test: retrieval over internal store returns results originating from loaded corpus for relevant query.

- [ ] P0. Implement query decomposition (`specs/query-decomposition.md`)
  - Gaps confirmed by code search: no decomposition component/state contract exists.
  - Required verification outcomes:
    - Backend smoke test: complex query yields ordered list with at least one focused sub-query.
    - Backend smoke test: each produced sub-query is answerable by one tool domain (`internal` or `web`) rather than requiring both inherently.
    - Backend smoke/integration test: produced sub-queries are exposed to downstream pipeline state/events.

- [ ] P0. Implement exclusive tool selection per subquery (`specs/tool-selection-per-subquery.md`)
  - Gaps confirmed by code search: no tool-assignment stage/schema exists.
  - Required verification outcomes:
    - Backend smoke test: every sub-query receives exactly one assignment (`internal_rag` or `web_search`).
    - Backend smoke test: no sub-query receives both assignments.
    - Backend smoke/integration test: assignments are available to retrieval/orchestration state (and stream projection when enabled).

- [ ] P0. Implement web tools (`specs/web-search-onyx-style.md`)
  - Gaps confirmed by code search: no `web.search` and no `web.open_url` tool interfaces/handlers.
  - Required verification outcomes:
    - Backend smoke test: search tool returns link/snippet metadata only (no full page body content).
    - Backend smoke test: open-url tool returns main/full page content for a URL.
    - Backend smoke/integration test: retrieval flow can execute search-then-open and expose opened URL sequence for observability/streaming.

- [ ] P1. Implement per-subquery retrieval executor (`specs/per-subquery-retrieval.md`)
  - Gaps confirmed by code search: no execution stage that consumes subquery + tool assignment.
  - Required verification outcomes:
    - Backend smoke test: given sub-query + assignment, correct retrieval path executes and returns consumable artifacts.
    - Backend integration test: internal path returns internal-store content only.
    - Backend integration test: web path follows search + open_url pattern.

- [ ] P1. Implement retrieval validation loop (`specs/retrieval-validation.md`)
  - Gaps confirmed by code search: no sufficiency evaluation or retry/deepen loop.
  - Required verification outcomes:
    - Backend smoke test: each subquery retrieval output is evaluated for sufficiency.
    - Backend smoke test: insufficient output triggers at least one follow-up retrieval/deepen action.
    - Backend integration test: loop terminates by sufficiency or stopping condition and emits final validation state.

- [ ] P1. Implement answer synthesis (`specs/answer-synthesis.md`)
  - Gaps confirmed by code search: no synthesis component consuming validated subquery outputs.
  - Required verification outcomes:
    - Backend smoke test: given original query + validated subquery outputs, synthesis returns one final answer.
    - Backend smoke test: synthesis consumes validated outputs only (no direct retrieval inside synthesis step).
    - Backend rubric test: final answer is coherent and addresses the original query.

- [ ] P1. Implement LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`)
  - Gaps confirmed by code search: `LangGraphAgentScaffold` returns placeholder dict only; no executable graph.
  - Required verification outcomes:
    - Backend integration test: flow executes decomposition -> selection -> retrieval -> validation loop -> synthesis in intended order.
    - Backend integration test: each logical step exists as a graph node/stage and runs in pipeline execution.
    - Backend integration test: graph state/projection is exposed for streaming heartbeat consumers.

- [ ] P2. Implement streaming heartbeat service (`specs/streaming-agent-heartbeat.md`)
  - Gaps confirmed by code search: no SSE/WebSocket endpoint and no stream event contract.
  - Required verification outcomes:
    - Backend integration test: running a query emits streamed sub-query updates during execution.
    - Backend integration test: stream events include enough progress state for UI heartbeat (active stage + completion/final answer).
    - Backend integration test: stream reaches reliable terminal event for typical run.

- [ ] P2. Implement demo TypeScript UI workflow (`specs/demo-ui-typescript.md`)
  - Gaps confirmed by code search: UI has no load action, query-run flow, stream subscription, or final answer rendering.
  - Required verification outcomes:
    - Frontend interaction test: user can trigger load/vectorize action and sees deterministic success/error state.
    - Frontend interaction test: running a query displays streamed sub-queries in near real time.
    - Frontend interaction test: UI shows live progress heartbeat and final synthesized answer.

- [ ] P2. Expose pipeline via MCP wrapper (`specs/mcp-exposure.md`)
  - Gaps confirmed by code search: no MCP server/tool adapter present.
  - Required verification outcomes:
    - Integration test: MCP client sends query and receives synthesized final answer.
    - Integration test: MCP wrapper delegates to same orchestration pipeline as API path.
    - Integration test: invocation contract is stable across repeated calls.

## Cross-Cutting Rules (Keep Updated)
- [ ] For each first backend behavior in a task above, add at least one deterministic `@pytest.mark.smoke` test before or with implementation.
- [ ] For each first frontend UI behavior in a task above, add at least one deterministic render/interaction test before or with implementation.
- [ ] Keep tests outcome-focused (behavioral contracts), not implementation-detail assertions.
- [ ] Keep test runs deterministic; avoid hidden network dependencies in CI.
- [ ] Any DB schema change must include an Alembic migration in the same change.
