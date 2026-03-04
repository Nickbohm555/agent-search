# IMPLEMENTATION_PLAN

## Status Snapshot (2026-03-04)
- Project is still scaffold-only after comparing `specs/*` to `src/*`.
- Confirmed implemented behavior:
  - `GET /api/health` returns `{"status":"ok"}`.
  - `GET /api/search-skeleton` returns scaffold status/message.
  - `GET /api/agents/runtime` returns scaffold agent metadata.
  - `POST /api/agents/run` returns scaffold runtime output.
  - Startup sets `app.state.langfuse` via placeholder initializer (no real Langfuse client/tracer).
  - Alembic baseline migration exists with no domain tables.
  - Frontend renders static scaffold UI only.
- Confirmed tests present:
  - Backend: `tests/api/test_health.py` only.
  - Frontend: `src/App.test.tsx` heading render only.
- `src/lib/*` does not exist in this repo (checked via `rg --files src/lib`).

## Completed
- [x] Scaffold FastAPI app, routers, services, schemas, and runtime-agent placeholders.
- [x] Scaffold React + TypeScript + Vite frontend shell.
- [x] Scaffold Docker Compose + Postgres + Alembic baseline wiring.

## Remaining Work (Prioritized, Outcome-Based)

- [ ] P0 - Add smoke tests for existing scaffold endpoints (incomplete)
  - Gap confirmation: no tests for `/api/search-skeleton`, `/api/agents/runtime`, `/api/agents/run`.
  - Required verification outcomes:
    - `GET /api/search-skeleton` returns `200`, `status="scaffold"`, non-empty `message`.
    - `GET /api/agents/runtime` returns `200` with non-empty `name` and `version`.
    - `POST /api/agents/run` with valid query returns `200` with non-empty `agent_name` and `output`.
    - Empty `query` is rejected with request-validation 4xx.

- [ ] P0 - Langfuse SDK setup (`specs/langfuse-sdk-setup.md`) (incomplete)
  - Gap confirmation: no Langfuse dependency in `pyproject.toml`; initializer is placeholder-only.
  - Required verification outcomes:
    - With `LANGFUSE_ENABLED=true` and valid credentials, app startup succeeds and a usable tracing handle exists on app state.
    - With `LANGFUSE_ENABLED=false` or missing credentials, app startup still succeeds with graceful no-op handle.
    - A tracing-capable path can create an observation through this handle without runtime errors.

- [ ] P0 - Agent run tracing at execution boundary (`specs/agent-run-tracing.md`) (incomplete)
  - Gap confirmation: `run_runtime_agent()` has no tracing instrumentation.
  - Required verification outcomes:
    - With tracing enabled, each `POST /api/agents/run` creates an observation including query input, agent identity, and output.
    - With tracing disabled, endpoint behavior/response remains unchanged and succeeds.
    - Consecutive runs produce distinct observations.

- [ ] P0 - Query decomposition (`specs/query-decomposition.md`) (incomplete)
  - Gap confirmation: no decomposition module/state exposed.
  - Required verification outcomes:
    - Complex query yields at least one focused sub-query.
    - Each produced sub-query is answerable by a single tool domain (`internal` or `web`, not both).
    - Sub-queries are exposed for downstream orchestration and streaming.

- [ ] P0 - Tool selection per sub-query (`specs/tool-selection-per-subquery.md`) (incomplete)
  - Gap confirmation: no `internal` vs `web` assignment logic exists.
  - Required verification outcomes:
    - Every sub-query receives exactly one assignment (`internal` or `web`).
    - No sub-query is assigned both tools.
    - Assignments are available to retrieval/orchestration (and stream projection where needed).

- [ ] P0 - Internal data loading and vectorization (`specs/data-loading-vectorization.md`) (incomplete)
  - Gap confirmation: no ingestion API/workflow, no corpus schema, and embeddings util is placeholder.
  - Required verification outcomes:
    - A supported internal source load can be triggered and completes successfully.
    - After successful load, internal retrieval returns results from loaded documents for relevant queries.
    - Load result is observable with success/failure plus doc/chunk counts for UI status.

- [ ] P0 - Web search tool pair (`specs/web-search-onyx-style.md`) (incomplete)
  - Gap confirmation: no `web.search`/`web.open_url` tool interfaces implemented.
  - Required verification outcomes:
    - `web.search` returns links/snippets metadata only (no full page body).
    - `web.open_url` returns main/full page content for a URL.
    - Search then open behavior is observable (including which URLs were opened).
    - Sub-queries assigned to `web` use this tool pair.

- [ ] P1 - Per-subquery retrieval executor (`specs/per-subquery-retrieval.md`) (incomplete)
  - Gap confirmation: no executor that consumes `(subquery, assigned_tool)`.
  - Required verification outcomes:
    - `internal` assignment runs internal retrieval and returns retrievable content.
    - `web` assignment runs web retrieval and returns retrievable content.
    - Internal retrieval returns content from loaded internal store only.
    - Retrieval output contract is consumable by validation step.

- [ ] P1 - Retrieval validation loop (`specs/retrieval-validation.md`) (incomplete)
  - Gap confirmation: no sufficiency evaluator, no retry/deepen loop, no stop policy.
  - Required verification outcomes:
    - Each sub-query retrieval result is evaluated for sufficiency.
    - Insufficient results trigger at least one follow-up action (more retrieval/deeper read).
    - Loop stops deterministically via sufficiency or explicit stopping condition.
    - Validation result/status is exposed for synthesis and streaming.

- [ ] P1 - Answer synthesis (`specs/answer-synthesis.md`) (incomplete)
  - Gap confirmation: no synthesis component exists.
  - Required verification outcomes:
    - Original query plus validated sub-query results produce one final answer.
    - Final answer coherently addresses the original query (fixture/rubric assertion).
    - Synthesis consumes validated outputs only (no direct retrieval in synthesis step).

- [ ] P1 - LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`) (incomplete)
  - Gap confirmation: `LangGraphAgentScaffold.build()` returns placeholder with `compiled=False`; no executable graph pipeline.
  - Required verification outcomes:
    - End-to-end decomposition -> selection -> retrieval -> validation -> synthesis runs as a LangGraph graph.
    - Logical stage order is preserved, including validation loop behavior.
    - Deep-agent composition exists in subquery/tool execution path.
    - Graph state/projection is consumable by streaming layer.

- [ ] P2 - Streaming heartbeat service (`specs/streaming-agent-heartbeat.md`) (incomplete)
  - Gap confirmation: no streaming endpoint/protocol/event bridge exists.
  - Required verification outcomes:
    - Running a query emits stream updates including generated sub-queries.
    - Stream provides enough progress events for live heartbeat and completion.
    - Event ordering remains coherent through final completion payload.

- [ ] P2 - Demo UI TypeScript flow (`specs/demo-ui-typescript.md`) (incomplete)
  - Gap confirmation: no load trigger, run flow, stream consumption, progress timeline, or final answer view.
  - Required verification outcomes:
    - User can trigger load/vectorize from UI and sees clear loading/success/error outcomes.
    - Running query shows streamed sub-queries in real time or near real time.
    - UI shows heartbeat progress and final answer from stream.
    - Frontend render/interaction tests pass, plus typecheck and build checks pass.

- [ ] P2 - MCP exposure (`specs/mcp-exposure.md`) (incomplete)
  - Gap confirmation: no MCP server/wrapper/invocation contract in repo.
  - Required verification outcomes:
    - MCP client can submit a query and receive final synthesized answer.
    - MCP path delegates to the same LangGraph pipeline used by HTTP runtime path.
    - Repeated MCP calls preserve a stable response contract.

## Cross-Cutting Quality Gates (All Incomplete)
- [ ] For each new backend behavior, add deterministic smoke/integration tests first.
- [ ] For each new frontend behavior, add deterministic render/interaction tests first.
- [ ] Tests verify externally observable outcomes (not internal implementation details).
- [ ] CI test plan avoids hidden external-network dependencies (use fakes/mocks).
- [ ] Every DB schema change ships with Alembic migration in `src/backend/alembic/versions/`.
- [ ] Observability vendor wiring stays isolated in startup/services (`src/backend/observability/*`), not routers.
