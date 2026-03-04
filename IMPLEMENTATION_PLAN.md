# IMPLEMENTATION_PLAN

## Status Snapshot (2026-03-04)
- Project remains scaffold-only after code/spec comparison.
- Confirmed implemented behavior in `src/*`:
  - `GET /api/health` returns `{ "status": "ok" }`.
  - `GET /api/search-skeleton` returns scaffold status/message.
  - `GET /api/agents/runtime` returns scaffold agent metadata.
  - `POST /api/agents/run` returns scaffold runtime output.
  - Startup sets `app.state.langfuse` via placeholder initializer (no real SDK client/tracer).
  - Alembic baseline migration exists with no domain schema objects.
  - Frontend renders static scaffold-only UI.
- Confirmed test coverage:
  - Backend: only `/api/health` smoke test exists.
  - Frontend: only scaffold heading render test exists.
- `src/lib/*` is currently absent.

## Completed
- [x] Backend scaffold routes/services/schemas for health/search skeleton/agent runtime.
- [x] Frontend scaffold app with TypeScript + Vite.
- [x] DB/Alembic baseline scaffold and compose wiring.

## Remaining (Prioritized)

- [ ] P0 - Add smoke tests for already-exposed scaffold endpoints (incomplete)
  - Gap confirmed by code search: missing tests for `/api/search-skeleton`, `/api/agents/runtime`, `/api/agents/run`.
  - Verification requirements (outcomes):
    - `GET /api/search-skeleton` returns `200`, `status="scaffold"`, and non-empty `message`.
    - `GET /api/agents/runtime` returns `200` with non-empty `name` and `version`.
    - `POST /api/agents/run` with valid `query` returns `200` with non-empty `agent_name` and `output`.
    - Edge case: empty `query` is rejected with request-validation 4xx.

- [ ] P0 - Langfuse SDK setup (`specs/langfuse-sdk-setup.md`) (incomplete)
  - Gap confirmed: no Langfuse dependency in `pyproject.toml`; initializer returns placeholder objects only.
  - Verification requirements (outcomes):
    - With `LANGFUSE_ENABLED=true` and valid keys, app startup succeeds and exposes a usable Langfuse handle on app state.
    - With disabled flag or missing credentials, app startup still succeeds with no-op behavior.
    - A tracing-capable request path can create an observation via that handle without runtime errors.

- [ ] P0 - Trace every agent run at execution boundary (`specs/agent-run-tracing.md`) (incomplete)
  - Gap confirmed: `run_runtime_agent()` has no trace/span instrumentation.
  - Verification requirements (outcomes):
    - With tracing enabled, `POST /api/agents/run` creates an observation containing query, agent identity, and output.
    - With tracing disabled, endpoint response behavior remains unchanged and succeeds without tracing side effects.
    - Edge case: consecutive runs create distinct observations.

- [ ] P0 - Query decomposition (`specs/query-decomposition.md`) (incomplete)
  - Gap confirmed: no decomposition component/state exists.
  - Verification requirements (outcomes):
    - Complex query yields at least one focused sub-query.
    - Each sub-query is reasonably answerable by a single tool domain.
    - Sub-queries are exposed to downstream orchestration/state and stream projection.

- [ ] P0 - Tool selection per sub-query (`specs/tool-selection-per-subquery.md`) (incomplete)
  - Gap confirmed: no assignment logic for `internal` vs `web`.
  - Verification requirements (outcomes):
    - Every sub-query receives exactly one tool assignment.
    - Edge case: no sub-query is assigned both tools.
    - Assignments are available to retrieval/orchestration and stream projection.

- [ ] P0 - Internal data loading + vectorization (`specs/data-loading-vectorization.md`) (incomplete)
  - Gap confirmed: no ingestion pipeline/API, no corpus schema, embeddings util is placeholder.
  - Verification requirements (outcomes):
    - Supported source load can be triggered and completes successfully.
    - After successful load, internal retrieval returns relevant results from loaded docs.
    - Load outcome is observable with success/failure and doc/chunk counts for UI status.

- [ ] P0 - Web search tool pair (`specs/web-search-onyx-style.md`) (incomplete)
  - Gap confirmed: no `web.search`/`web.open_url` tool interfaces.
  - Verification requirements (outcomes):
    - `web.search` returns links/snippets metadata only (no full page body).
    - `web.open_url` returns main/full page content for a URL.
    - Search->select->open behavior is observable (including opened URLs).
    - Sub-queries routed to `web` execute through this tool pair.

- [ ] P1 - Per-subquery retrieval executor (`specs/per-subquery-retrieval.md`) (incomplete)
  - Gap confirmed: no executor consuming `(subquery, assigned_tool)`.
  - Verification requirements (outcomes):
    - `internal` assignment runs internal retrieval and returns retrievable content.
    - `web` assignment runs web retrieval and returns retrievable content.
    - Edge case: internal path returns only content from loaded internal store.
    - Retrieval output contract is consumable by validation stage.

- [ ] P1 - Retrieval validation loop (`specs/retrieval-validation.md`) (incomplete)
  - Gap confirmed: no sufficiency evaluator, no follow-up loop, no stop policy.
  - Verification requirements (outcomes):
    - Each retrieval result is evaluated for sufficiency.
    - Insufficient result triggers at least one follow-up action.
    - Loop terminates deterministically by sufficiency or explicit stopping condition.
    - Validation status/result is exposed for synthesis and streaming.

- [ ] P1 - Answer synthesis (`specs/answer-synthesis.md`) (incomplete)
  - Gap confirmed: no synthesis stage combining validated outputs.
  - Verification requirements (outcomes):
    - Original query + validated sub-query results produce one final answer.
    - Final answer coherently addresses original query (fixture/rubric assertion).
    - Edge case: synthesis consumes validated outputs only (no direct retrieval in this step).

- [ ] P1 - LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`) (incomplete)
  - Gap confirmed: graph builder is placeholder (`compiled: False`), no runnable pipeline graph.
  - Verification requirements (outcomes):
    - End-to-end decomposition->selection->retrieval->validation->synthesis runs as LangGraph.
    - Intended stage order is preserved, including validation loop behavior.
    - Deep-agent composition is present in subquery/tool execution path.
    - Graph state/projection is consumable by streaming layer.

- [ ] P2 - Streaming heartbeat service (`specs/streaming-agent-heartbeat.md`) (incomplete)
  - Gap confirmed: no streaming endpoint/protocol/event bridge exists.
  - Verification requirements (outcomes):
    - Query run emits stream updates including generated sub-queries.
    - Stream includes enough progress events for live UI heartbeat and completion.
    - Edge case: event ordering remains coherent through terminal completion/final payload.

- [ ] P2 - Demo UI TypeScript flow (`specs/demo-ui-typescript.md`) (incomplete)
  - Gap confirmed: frontend lacks load trigger, run flow, stream consumption, progress timeline, final answer rendering.
  - Verification requirements (outcomes):
    - UI can trigger load/vectorize and shows loading then success/error outcome.
    - Running a query shows streamed sub-queries in real time/near-real time.
    - UI renders heartbeat progress and final answer from stream.
    - Frontend tests, typecheck, and build checks pass.

- [ ] P2 - MCP exposure (`specs/mcp-exposure.md`) (incomplete)
  - Gap confirmed: no MCP server/wrapper/invocation contract in repository.
  - Verification requirements (outcomes):
    - MCP client can submit query and receive final synthesized answer.
    - MCP path delegates to same LangGraph pipeline as HTTP run path.
    - Edge case: repeated MCP invocations preserve response contract stability.

## Cross-Cutting Quality Gates (Still Incomplete)
- [ ] For each newly introduced backend behavior, add deterministic smoke/integration tests first.
- [ ] For each newly introduced frontend behavior, add deterministic render/interaction tests first.
- [ ] Tests assert externally observable outcomes rather than implementation internals.
- [ ] CI test suite avoids hidden external-network dependencies (use fakes/mocks).
- [ ] Every backend schema mutation ships with an Alembic migration in `src/backend/alembic/versions/`.
- [ ] Observability vendor wiring remains isolated to startup/services (`src/backend/observability/*`), not routers.
