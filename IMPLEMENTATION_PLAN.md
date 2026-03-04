# IMPLEMENTATION_PLAN

## Status Snapshot (2026-03-04)
- Project state is still scaffold-only (confirmed by code inspection in `src/backend/*`, `src/frontend/*`).
- Existing implemented behavior:
  - `GET /api/health` returns `{ "status": "ok" }`.
  - `GET /api/search-skeleton` returns scaffold status/message.
  - `GET /api/agents/runtime` returns scaffold agent metadata.
  - `POST /api/agents/run` returns scaffold text output from runtime agent wrapper.
  - FastAPI startup initializes a Langfuse handle placeholder (`app.state.langfuse`) with no real SDK client.
  - Baseline Alembic migration exists (`0001_scaffold`) with no schema objects.
  - Frontend renders scaffold-only React/TS screen.
- Current tests are minimal:
  - Backend: only `/api/health` smoke test exists.
  - Frontend: only scaffold heading render test exists.
- `src/lib/*` does not exist yet (no shared project library present).

## Completed Tasks
- [x] Scaffold backend app wiring (routers/services/schemas for health, search skeleton, runtime agent scaffold).
- [x] Scaffold frontend TypeScript app wiring (Vite + React + basic render path).
- [x] Add baseline migration scaffold and DB wiring foundation.

## Prioritized Remaining Tasks (Yet To Be Implemented)

- [ ] P0 - Expand scaffold smoke coverage for currently exposed API behavior (incomplete)
  - Specs alignment: validates currently-shipped scaffold contract before adding new features.
  - Gap confirmation:
    - No tests for `/api/search-skeleton`, `/api/agents/runtime`, or `/api/agents/run`.
  - Verification requirements (outcome-based):
    - Smoke test: `GET /api/search-skeleton` returns HTTP 200 with `status="scaffold"` and non-empty `message`.
    - Smoke test: `GET /api/agents/runtime` returns HTTP 200 with non-empty `name` and `version`.
    - Smoke test: `POST /api/agents/run` with valid `query` returns HTTP 200 with non-empty `agent_name` and `output`.
    - Edge smoke test: empty `query` is rejected with schema-validation 4xx.

- [ ] P0 - Langfuse SDK setup (`specs/langfuse-sdk-setup.md`) (incomplete)
  - Gap confirmation:
    - `src/backend/pyproject.toml` has no Langfuse SDK dependency.
    - `initialize_langfuse_tracing()` returns placeholder handle with `client=None` and `tracer=None`.
  - Verification requirements (outcome-based):
    - Startup test: with `LANGFUSE_ENABLED=true` + valid keys, app starts and exposes usable Langfuse handle on `app.state`.
    - Startup test: with tracing disabled or missing credentials, app still starts and provides graceful no-op handle.
    - Request-path test: a tracing-capable request can create an observation via the initialized handle without runtime errors.

- [ ] P0 - Agent run tracing at execution boundary (`specs/agent-run-tracing.md`) (incomplete)
  - Gap confirmation:
    - `run_runtime_agent()` executes the agent without any trace/span instrumentation.
  - Verification requirements (outcome-based):
    - Integration test: posting to `/api/agents/run` with tracing enabled creates one observation containing input query, agent identity, and output.
    - Regression test: with tracing disabled, endpoint response contract remains unchanged and no tracing errors occur.
    - Integration test: consecutive runs create distinct observations.

- [ ] P0 - Query decomposition (`specs/query-decomposition.md`) (incomplete)
  - Gap confirmation:
    - No decomposition component, schema, or pipeline state for ordered sub-queries exists.
  - Verification requirements (outcome-based):
    - Behavior test: complex query produces at least one focused sub-query.
    - Behavior test: each sub-query is independently answerable by a single tool domain.
    - Contract test: generated sub-queries are exposed to downstream orchestration and stream projection.

- [ ] P0 - Tool selection per sub-query (`specs/tool-selection-per-subquery.md`) (incomplete)
  - Gap confirmation:
    - No tool router assigns `internal` vs `web` per sub-query.
  - Verification requirements (outcome-based):
    - Behavior test: every sub-query receives exactly one tool assignment.
    - Guardrail test: no sub-query receives both assignments.
    - Contract test: assignments are exposed for retrieval/orchestration and stream projection.

- [ ] P0 - Data loading and vectorization for internal RAG (`specs/data-loading-vectorization.md`) (incomplete)
  - Gap confirmation:
    - No ingestion API/service, no chunk/embed/persist pipeline, no corpus tables/models, and only placeholder `utils/embeddings.py`.
  - Verification requirements (outcome-based):
    - Smoke/integration test: a supported source load can be triggered successfully.
    - Integration test: after successful load, internal retrieval returns relevant content from loaded documents.
    - Behavior test: load result exposes observable status (success/failure and document/chunk counts).

- [ ] P0 - Web search tool pair (`specs/web-search-onyx-style.md`) (incomplete)
  - Gap confirmation:
    - No `web.search` + `web.open_url` tool interfaces exist.
  - Verification requirements (outcome-based):
    - Tool contract test: search tool returns links/snippets metadata only (no full page body).
    - Tool contract test: open_url tool returns main/full content for requested URL.
    - Integration test: retrieval path can perform search -> select URLs -> open selected pages, with opened URLs observable.
    - Integration test: sub-queries assigned to `web` execute through this tool pair.

- [ ] P1 - Per-subquery retrieval executor (`specs/per-subquery-retrieval.md`) (incomplete)
  - Gap confirmation:
    - No retrieval executor that consumes `(sub-query, tool assignment)`.
  - Verification requirements (outcome-based):
    - Integration test: internal assignment executes internal retrieval and returns retrievable content.
    - Integration test: web assignment executes search/open flow and returns retrievable content.
    - Guardrail test: internal retrieval returns only content from loaded internal data store.
    - Contract test: retrieval output shape is consumable by validation stage.

- [ ] P1 - Retrieval validation loop (`specs/retrieval-validation.md`) (incomplete)
  - Gap confirmation:
    - No sufficiency evaluator, no retry/deepen actions, no deterministic stop policy.
  - Verification requirements (outcome-based):
    - Behavior test: each retrieval result gets sufficiency evaluation.
    - Behavior test: insufficient retrieval triggers at least one follow-up action.
    - Reliability test: loop terminates via either sufficient result or explicit stopping condition.
    - Contract test: validation result/state is exposed for synthesis and stream heartbeat.

- [ ] P1 - Answer synthesis (`specs/answer-synthesis.md`) (incomplete)
  - Gap confirmation:
    - No synthesis component that combines validated sub-query outputs into one final response.
  - Verification requirements (outcome-based):
    - Behavior test: original query + validated sub-query outputs produce one final answer.
    - Quality test: final answer is coherent and addresses original query (fixture/rubric based).
    - Guardrail test: synthesis consumes validated outputs only (no direct retrieval in this step).

- [ ] P1 - LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`) (incomplete)
  - Gap confirmation:
    - `LangGraphAgentScaffold.build()` returns placeholder dict with `compiled: False`; no graph nodes/edges/loop/state.
  - Verification requirements (outcome-based):
    - Integration test: full decomposition -> selection -> retrieval -> validation -> synthesis flow executes as LangGraph.
    - Integration test: required stages run in intended order including validation loop behavior.
    - Structural/behavior test: deep-agent composition is present for subquery/tool execution path.
    - Contract test: graph state/projection is available for streaming consumers.

- [ ] P2 - Streaming agent heartbeat (`specs/streaming-agent-heartbeat.md`) (incomplete)
  - Gap confirmation:
    - No SSE/WebSocket streaming endpoint, event schema, or orchestration-to-stream event bridge.
  - Verification requirements (outcome-based):
    - Integration test: running a query emits streamed updates including sub-queries as generated.
    - Integration test: stream contains enough progress events for live UI heartbeat and completion.
    - Reliability test: typical run produces ordered observable progress ending in completion/final payload.

- [ ] P2 - Demo UI TypeScript experience (`specs/demo-ui-typescript.md`) (incomplete)
  - Gap confirmation:
    - Current frontend is static scaffold only; no load trigger, no run action, no stream consumption, no final answer view.
  - Verification requirements (outcome-based):
    - Frontend interaction test: user can trigger load/vectorize and sees loading + success/error outcome.
    - Frontend interaction test: user can submit query and see streamed sub-queries in near real-time.
    - Frontend interaction test: heartbeat progress and final answer are rendered.
    - Build checks: frontend tests + `typecheck` + build remain green.

- [ ] P2 - MCP exposure (`specs/mcp-exposure.md`) (incomplete)
  - Gap confirmation:
    - No MCP server/wrapper/tool definition exists in repository.
  - Verification requirements (outcome-based):
    - End-to-end integration test: MCP client invocation with query returns final synthesized answer.
    - Integration test: MCP path delegates to same orchestration pipeline as HTTP run path.
    - Contract test: repeated invocations preserve response schema and success behavior.

## Cross-Cutting Delivery Rules (Track as Incomplete Until Enforced by Tests)
- [ ] First backend behavior in each new area includes deterministic smoke/integration coverage.
- [ ] First frontend behavior in each new area includes deterministic render/interaction coverage.
- [ ] Tests validate externally observable outcomes (not implementation internals).
- [ ] CI-facing tests avoid hidden external-network dependencies (mock/fake providers).
- [ ] Every schema mutation ships with Alembic migration in `src/backend/alembic/versions/`.
- [ ] Observability vendor wiring remains isolated to startup/services (`src/backend/observability/*`), not router-level SDK coupling.
