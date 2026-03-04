# IMPLEMENTATION_PLAN

## Audit Snapshot (2026-03-04)
- Reviewed: `specs/*`, existing plan, `src/backend/*`, `src/frontend/*`, `docker-compose.yml`.
- Confirmed scaffold-only implementation:
  - `LangGraphAgentScaffold.build()` returns placeholder (`compiled: False`).
  - No decomposition/tool-selection/retrieval/validation/synthesis pipeline exists.
  - No streaming endpoint, MCP wrapper, or web-search tool layer exists.
  - Langfuse setup is scaffold-only (`initialize_langfuse_tracing()` placeholder; no SDK dependency).
- `src/lib/*` does not exist; shared utility roots currently are:
  - `src/backend/utils/*`
  - `src/frontend/src/utils/*`

## Completed
- [x] Compose + FastAPI + Vite scaffold is wired and starts.
- [x] `GET /api/health` contract exists with deterministic backend smoke test.
- [x] Frontend scaffold render test exists.

## Prioritized Remaining Tasks
- [ ] P0 - Langfuse SDK setup (`specs/langfuse-sdk-setup.md`) - Status: Incomplete
  - Gap confirmation: no Langfuse SDK in `src/backend/pyproject.toml`; startup stores placeholder handle only.
  - Verification requirements (from acceptance criteria):
    - Startup test: with `LANGFUSE_ENABLED=true` and valid keys, app starts and exposes usable Langfuse handle on app state.
    - Startup test: with `LANGFUSE_ENABLED=false` or missing keys, app starts cleanly with graceful no-op handle.
    - Request-path test: a tracing-capable request can create a trace/span through initialized handle without runtime errors when enabled.

- [ ] P0 - Agent run tracing at execution boundary (`specs/agent-run-tracing.md`) - Status: Incomplete
  - Gap confirmation: `src/backend/services/agent_service.py` executes agent run with no trace/span instrumentation.
  - Verification requirements (from acceptance criteria):
    - Integration test: when tracing enabled, `POST /api/agents/run` creates trace/span containing query, agent identity, and response.
    - Behavior test: when tracing disabled, endpoint response contract remains unchanged and no trace is created.
    - Integration test: consecutive runs produce distinct traces/spans.

- [ ] P0 - Data loading and vectorization for internal RAG (`specs/data-loading-vectorization.md`) - Status: Incomplete
  - Gap confirmation: no ingest API/service, no vectorized corpus tables/models, no chunk/embed/persist flow.
  - Verification requirements (from acceptance criteria):
    - Smoke test: user/API can trigger loading/vectorization for at least one supported source.
    - Integration test: successful load makes internal retrieval return results from loaded documents for relevant queries.
    - Behavior test: load outcome is observable with clear success/failure status plus count metadata (doc/chunk counts).

- [ ] P0 - Query decomposition (`specs/query-decomposition.md`) - Status: Incomplete
  - Gap confirmation: no decomposition component or pipeline state contract for sub-queries.
  - Verification requirements (from acceptance criteria):
    - Behavior test: complex query produces at least one focused sub-query.
    - Behavior test: each sub-query is answerable by one tool domain alone (internal or web).
    - Integration test: sub-queries are exposed to downstream pipeline and stream projection.

- [ ] P0 - Tool selection per sub-query (exclusive) (`specs/tool-selection-per-subquery.md`) - Status: Incomplete
  - Gap confirmation: no assignment stage/schema for `internal RAG` vs `web search`.
  - Verification requirements (from acceptance criteria):
    - Behavior test: each sub-query receives exactly one tool assignment.
    - Behavior test: no sub-query is assigned both tools.
    - Integration test: assignments are available to retrieval/orchestration and stream projection.

- [ ] P0 - Web search tools (Onyx pattern) (`specs/web-search-onyx-style.md`) - Status: Incomplete
  - Gap confirmation: no `web.search` and `web.open_url` interfaces/implementations.
  - Verification requirements (from acceptance criteria):
    - Smoke test: search tool returns links/snippets metadata only (no full page body).
    - Smoke test: open_url tool returns full/main page content for URL.
    - Integration test: agent can perform search then open selected URLs; opened URLs are observable for logging/streaming.
    - Integration test: tool-selection “web” assignment can execute through these tools.

- [ ] P1 - Per-subquery retrieval executor (`specs/per-subquery-retrieval.md`) - Status: Incomplete
  - Gap confirmation: no executor consumes `(sub-query, assigned tool)` and returns retrieval artifacts.
  - Verification requirements (from acceptance criteria):
    - Integration test: given sub-query + assignment, corresponding retrieval path runs and returns consumable content.
    - Behavior test: internal path returns content from loaded/vectorized internal store only.
    - Behavior test: web path follows search + open_url pattern.
    - Integration test: retrieval output shape is consumable by validation step.

- [ ] P1 - Retrieval validation loop (`specs/retrieval-validation.md`) - Status: Incomplete
  - Gap confirmation: no sufficiency-evaluation loop or follow-up retrieval/deepen behavior.
  - Verification requirements (from acceptance criteria):
    - Behavior test: each sub-query retrieval result is evaluated for sufficiency.
    - Behavior test: insufficient result triggers at least one follow-up action.
    - Integration test: loop terminates by sufficiency or stopping condition and emits validation outcome for synthesis.
    - Integration test: validation state is observable for streaming projection.

- [ ] P1 - Answer synthesis (`specs/answer-synthesis.md`) - Status: Incomplete
  - Gap confirmation: no synthesis component consuming validated sub-query outputs.
  - Verification requirements (from acceptance criteria):
    - Behavior test: original query + validated sub-query outputs yields a single final answer.
    - Behavior test: synthesis consumes validated outputs only (no direct retrieval from synthesis component).
    - Rubric test: final answer coherently addresses the original query.

- [ ] P1 - LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`) - Status: Incomplete
  - Gap confirmation: current agent graph is scaffold placeholder only.
  - Verification requirements (from acceptance criteria):
    - Integration test: full flow runs as LangGraph graph (decomposition -> selection -> retrieval -> validation loop -> synthesis).
    - Integration test: each logical step is represented as graph node/stage and executes in intended order.
    - Integration test: deep-agent structure is used for subquery/tool execution.
    - Integration test: graph state (or projection) is available for streaming heartbeat.

- [ ] P2 - Streaming agent heartbeat (`specs/streaming-agent-heartbeat.md`) - Status: Incomplete
  - Gap confirmation: no SSE/WebSocket (or equivalent) endpoint and no stream event contract.
  - Verification requirements (from acceptance criteria):
    - Integration test: running a query emits streamed updates including sub-queries as generated.
    - Integration test: stream payloads contain enough progress info for live UI heartbeat (step/progress/final answer).
    - Reliability test: typical run provides observable progress updates and terminal completion event.

- [ ] P2 - Demo TypeScript UI (`specs/demo-ui-typescript.md`) - Status: Incomplete
  - Gap confirmation: current UI is static scaffold; no load action, run flow, stream consumption, or answer display.
  - Verification requirements (from acceptance criteria):
    - Frontend interaction test: user can trigger load/vectorize and sees clear success/error outcome.
    - Frontend interaction test: when query runs, sub-queries appear as streamed updates in near real-time.
    - Frontend interaction test: heartbeat progress and final answer are displayed.
    - Quality checks: TypeScript-based app continues to pass frontend test, typecheck, and build.

- [ ] P2 - MCP exposure (`specs/mcp-exposure.md`) - Status: Incomplete
  - Gap confirmation: no MCP server/tool wrapper exists in backend.
  - Verification requirements (from acceptance criteria):
    - Integration test: MCP client invocation with query returns final synthesized answer.
    - Integration test: MCP path delegates to same LangGraph orchestration pipeline.
    - Stability test: repeated invocations preserve contract shape and end-to-end success.

- [ ] P2 - Add missing smoke tests for existing scaffold endpoints (non-spec hardening) - Status: Incomplete
  - Gap confirmation: only `/api/health` has smoke coverage today.
  - Verification requirements:
    - Smoke test: `GET /api/search-skeleton` returns scaffold contract.
    - Smoke test: `GET /api/agents/runtime` returns non-empty `name` and `version`.
    - Smoke test: `POST /api/agents/run` valid payload returns non-empty `agent_name` and `output`.
    - Edge smoke test: empty query is schema-rejected (4xx).

## Delivery Rules (Apply To Every Task)
- [ ] Add at least one deterministic smoke test with each first backend behavior.
- [ ] Add at least one deterministic render/interaction test with each first frontend UI behavior.
- [ ] Keep tests outcome-focused (verify what works, not implementation internals).
- [ ] Keep tests deterministic and CI-safe (no hidden network dependencies).
- [ ] Ship Alembic migration with every schema change.
- [ ] Keep tracing wiring isolated to startup/services (`src/backend/observability/*`), not directly in routers.
