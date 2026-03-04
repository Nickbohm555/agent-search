# IMPLEMENTATION_PLAN

## Status Snapshot (2026-03-04)
- Repository state remains scaffold-only after comparing `specs/*` with `src/*`.
- `src/lib/*` does not exist (confirmed via `rg --files src/lib`).
- Existing working scaffold behavior confirmed:
  - `GET /api/health` returns `{"status":"ok"}`.
  - `GET /api/search-skeleton` returns scaffold status/message.
  - `GET /api/agents/runtime` returns scaffold agent identity.
  - `POST /api/agents/run` returns scaffold agent output.
  - Startup sets `app.state.langfuse` from placeholder initializer.
  - Alembic baseline exists with no domain tables.
  - Frontend renders static scaffold shell only.
- Existing tests confirmed:
  - Backend: `src/backend/tests/api/test_health.py` only.
  - Frontend: `src/frontend/src/App.test.tsx` heading render only.

## Completed
- [x] Scaffold FastAPI app with baseline routers, services, and schemas.
- [x] Scaffold runtime agent factory/wrapper and placeholder LangGraph agent object.
- [x] Scaffold observability config loader and startup wiring for Langfuse handle.
- [x] Scaffold React/TypeScript/Vite frontend shell with API base config helper.
- [x] Scaffold Docker Compose + Postgres + Alembic + pgvector infrastructure.

## Remaining Work (Prioritized)

- [ ] P0 - Add smoke coverage for existing scaffold endpoints
  - Scope gap confirmed in code search: only `/api/health` has tests.
  - Verification requirements (outcome-focused):
    - `GET /api/search-skeleton` returns `200` with `status="scaffold"` and non-empty `message`.
    - `GET /api/agents/runtime` returns `200` with non-empty `name` and `version`.
    - `POST /api/agents/run` with valid payload returns `200` with non-empty `agent_name` and `output`.
    - `POST /api/agents/run` rejects empty `query` with request-validation 4xx.

- [ ] P0 - Implement Langfuse SDK initialization (`specs/langfuse-sdk-setup.md`)
  - Scope gap confirmed: no Langfuse SDK dependency; initializer returns placeholder handle only.
  - Verification requirements (outcome-focused):
    - With `LANGFUSE_ENABLED=true` and valid credentials, startup succeeds and app state exposes a usable tracing handle.
    - With `LANGFUSE_ENABLED=false` or missing credentials, startup still succeeds with graceful no-op behavior.
    - A tracing-capable request path can create an observation via the initialized handle without runtime errors.

- [ ] P0 - Instrument agent-run tracing (`specs/agent-run-tracing.md`)
  - Scope gap confirmed: `run_runtime_agent()` executes with no trace/span creation.
  - Verification requirements (outcome-focused):
    - With tracing enabled, each `POST /api/agents/run` creates a trace/span containing query input, agent identity, and output.
    - With tracing disabled, endpoint response contract remains unchanged and successful.
    - Consecutive agent runs create distinct traces/spans.

- [ ] P0 - Implement query decomposition (`specs/query-decomposition.md`)
  - Scope gap confirmed: no decomposition component/state in backend.
  - Verification requirements (outcome-focused):
    - Complex query produces at least one focused sub-query.
    - Each sub-query is suitable for a single retrieval domain (internal or web, not both simultaneously).
    - Produced sub-queries are available to downstream orchestration and stream projection.

- [ ] P0 - Implement per-subquery tool selection (`specs/tool-selection-per-subquery.md`)
  - Scope gap confirmed: no assignment layer mapping sub-query -> `internal|web`.
  - Verification requirements (outcome-focused):
    - Every sub-query receives exactly one assignment (`internal` or `web`).
    - No sub-query is assigned both tools.
    - Assignments are passed to retrieval/orchestration and available for stream visibility.

- [ ] P0 - Implement internal data loading/vectorization (`specs/data-loading-vectorization.md`)
  - Scope gap confirmed: no ingestion endpoint/service, no corpus tables, embeddings util still scaffold comment.
  - Verification requirements (outcome-focused):
    - At least one supported source can be loaded/vectorized via API/backend trigger.
    - After successful load, internal retrieval returns results from loaded documents for relevant queries.
    - Load outcome is observable with success/failure plus document/chunk counts.
    - Any schema additions ship with matching Alembic migration.

- [ ] P0 - Implement web tool pair (`specs/web-search-onyx-style.md`)
  - Scope gap confirmed: no `web.search` or `web.open_url` tool interfaces/services.
  - Verification requirements (outcome-focused):
    - Search tool returns link/snippet metadata only (no full-page body).
    - URL-open tool returns full/main page content for requested URL.
    - Agent/tool execution exposes observable search-then-open behavior (including opened URLs).
    - Web-assigned sub-queries can execute through this tool pair.

- [ ] P1 - Implement per-subquery retrieval executor (`specs/per-subquery-retrieval.md`)
  - Scope gap confirmed: no executor consuming `(subquery, assigned_tool)`.
  - Verification requirements (outcome-focused):
    - `internal` assignment runs internal retrieval and returns retrievable corpus content.
    - `web` assignment runs web retrieval through search+open_url and returns retrievable web content.
    - Internal path returns results sourced only from loaded/vectorized internal store.
    - Retrieval output contract is usable by validation stage.

- [ ] P1 - Implement retrieval validation loop (`specs/retrieval-validation.md`)
  - Scope gap confirmed: no sufficiency evaluator, no retry/deepen loop, no stop policy.
  - Verification requirements (outcome-focused):
    - Each retrieval result is evaluated for sufficiency.
    - Insufficient result triggers at least one follow-up action (additional retrieval or deeper read).
    - Loop stops deterministically via sufficiency or explicit stopping rule.
    - Validation status/result is available for synthesis and streaming.

- [ ] P1 - Implement answer synthesis (`specs/answer-synthesis.md`)
  - Scope gap confirmed: no synthesis component.
  - Verification requirements (outcome-focused):
    - Original query + validated sub-query outputs produce one final answer.
    - Final answer addresses the original query coherently (fixture/rubric assertion).
    - Synthesis stage consumes validated outputs only (no direct retrieval performed here).

- [ ] P1 - Implement LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`)
  - Scope gap confirmed: LangGraph scaffold returns `compiled=False` placeholder graph dict.
  - Verification requirements (outcome-focused):
    - End-to-end flow decomposition -> selection -> retrieval -> validation -> synthesis executes as a LangGraph graph.
    - Logical order is enforced, including per-subquery validation loop behavior.
    - Deep-agent composition is present for subquery/tool execution path.
    - Graph state or projection is consumable by streaming layer.

- [ ] P2 - Implement streaming heartbeat backend (`specs/streaming-agent-heartbeat.md`)
  - Scope gap confirmed: no streaming endpoint/protocol/event bridge.
  - Verification requirements (outcome-focused):
    - Query runs emit stream updates including generated sub-queries.
    - Stream events are sufficient for live progress/heartbeat and completion display.
    - Event ordering remains coherent through final payload.

- [ ] P2 - Implement demo UI flow in TypeScript (`specs/demo-ui-typescript.md`)
  - Scope gap confirmed: UI lacks load trigger/status, query run flow, streaming subscription, progress timeline, final answer rendering.
  - Verification requirements (outcome-focused):
    - UI can trigger load/vectorize and shows clear loading/success/error outcomes.
    - Query run shows streamed sub-queries in real-time or near real-time.
    - UI shows heartbeat progress and final synthesized answer.
    - TypeScript render/interaction tests cover these user-visible outcomes.

- [ ] P2 - Implement MCP exposure (`specs/mcp-exposure.md`)
  - Scope gap confirmed: no MCP server/tool wrapper/transport contract present.
  - Verification requirements (outcome-focused):
    - MCP client can submit query and receive final synthesized answer.
    - MCP path delegates to same orchestration pipeline used by runtime API.
    - Repeated MCP calls preserve stable invocation/response contract.

## Cross-Cutting Quality Gates (Apply to every new task)
- [ ] Add backend smoke/integration coverage for each new externally visible behavior.
- [ ] Add frontend render/interaction coverage for each new UI behavior.
- [ ] Keep tests deterministic and outcome-based; avoid assertions on internal implementation details.
- [ ] Avoid hidden network dependencies in CI test paths (use controlled fakes/mocks where needed).
- [ ] Deliver Alembic migration in same change for every schema change.
- [ ] Keep observability vendor integration isolated to startup/services, not routers.
- [ ] Before commit for implementation runs: pass health check + backend tests + frontend tests + frontend typecheck.
