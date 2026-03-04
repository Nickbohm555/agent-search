# IMPLEMENTATION_PLAN

## Audit Snapshot (2026-03-04)
- Reviewed: `specs/*`, current `IMPLEMENTATION_PLAN.md`, `src/backend/*`, `src/frontend/*`, `docker-compose.yml`.
- Confirmed scaffold-only state; no business pipeline implementation is present.
- `src/lib/*` is not present in this repository.
- Effective shared utility roots currently in use:
  - Backend shared helpers: `src/backend/utils/*`
  - Frontend shared helpers: `src/frontend/src/utils/*`

## Completed
- [x] Scaffold stack wiring exists (Compose services, FastAPI app, Vite app, baseline Alembic).
- [x] Health endpoint contract exists with deterministic smoke test (`GET /api/health`).
- [x] Frontend baseline scaffold render test exists.

## Prioritized Remaining Work

- [ ] P0 - Expand smoke coverage for existing scaffold endpoints (`/api/search-skeleton`, `/api/agents/runtime`, `/api/agents/run`)
  - Status: Incomplete.
  - Why missing (code-confirmed): only `/api/health` has API smoke coverage.
  - Verification requirements:
    - Add smoke test: `GET /api/search-skeleton` returns `200` with `status="scaffold"` and scaffold message.
    - Add smoke test: `GET /api/agents/runtime` returns `200` with non-empty `name` and `version`.
    - Add smoke test: `POST /api/agents/run` with valid query returns `200` with non-empty `agent_name` and `output`.
    - Add edge smoke test: `POST /api/agents/run` with empty query is rejected by schema validation (4xx).

- [ ] P0 - Langfuse SDK setup (`specs/langfuse-sdk-setup.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): no Langfuse dependency in backend `pyproject.toml`; `initialize_langfuse_tracing()` returns placeholder handle.
  - Verification requirements:
    - Smoke test: with `LANGFUSE_ENABLED=true` and valid keys, startup initializes a usable tracing handle on `app.state.langfuse`.
    - Smoke test: with `LANGFUSE_ENABLED=false` or missing keys, startup succeeds with graceful no-op handle.
    - Integration/smoke test: tracing-capable request path can create a trace/span through initialized handle without runtime error when enabled.

- [ ] P0 - Agent-run tracing boundary (`specs/agent-run-tracing.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): `run_runtime_agent()` has no tracing instrumentation.
  - Verification requirements:
    - Integration test: tracing enabled + `POST /api/agents/run` records run input, agent identity, and output for that run.
    - Smoke test: tracing disabled path returns same response contract and produces no tracing side effects.
    - Integration test: consecutive run requests produce distinct traces/spans.

- [ ] P0 - Data loading and vectorization (`specs/data-loading-vectorization.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): no ingestion API/service, no chunk/embed/persist pipeline, no corpus models/tables.
  - Verification requirements:
    - Smoke test: load/vectorize trigger for at least one source returns observable status (`success`/`error`) plus count metadata.
    - Integration test: successful load persists retrievable vectorized records tied to source docs.
    - Integration test: internal retrieval over relevant query returns content from loaded corpus.
    - Edge test: failed load reports clear failure outcome without partial-success ambiguity.

- [ ] P0 - Query decomposition (`specs/query-decomposition.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): no decomposition component or state contract.
  - Verification requirements:
    - Smoke test: complex query produces ordered list containing at least one focused sub-query.
    - Behavior test: each sub-query is independently answerable by one tool domain (internal or web, not inherently both).
    - Integration test: produced sub-queries are exposed to downstream orchestration/stream state.

- [ ] P0 - Exclusive tool selection per sub-query (`specs/tool-selection-per-subquery.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): no per-subquery assignment stage/schema.
  - Verification requirements:
    - Smoke test: every sub-query receives exactly one assignment (`internal_rag` or `web_search`).
    - Behavior test: no sub-query is assigned both tools.
    - Integration test: assignments are consumable by retrieval/orchestration state and stream projection.

- [ ] P0 - Web search tools (Onyx-style) (`specs/web-search-onyx-style.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): no `web.search`/`web.open_url` tool interfaces.
  - Verification requirements:
    - Smoke test: search tool returns links/snippets metadata only (no full page body).
    - Smoke test: open-url tool returns page main/full content for provided URL.
    - Integration test: retrieval flow can perform search then open selected URLs; opened URL sequence is observable for logs/streaming.

- [ ] P1 - Per-subquery retrieval executor (`specs/per-subquery-retrieval.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): no executor that consumes subquery + tool assignment.
  - Verification requirements:
    - Smoke test: given sub-query + assignment, correct retrieval path executes and returns consumable artifacts.
    - Integration test: internal path returns only internal-store derived content.
    - Integration test: web path follows search + open_url pattern.

- [ ] P1 - Retrieval validation loop (`specs/retrieval-validation.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): no sufficiency evaluator or retry/deepen loop.
  - Verification requirements:
    - Smoke test: each subquery retrieval output is evaluated for sufficiency.
    - Behavior test: insufficient result triggers at least one follow-up retrieval/deepen action.
    - Integration test: loop terminates by sufficiency or stopping condition and emits final validation state.

- [ ] P1 - Answer synthesis (`specs/answer-synthesis.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): no synthesis component consuming validated subquery outputs.
  - Verification requirements:
    - Smoke test: original query + validated subquery outputs produces one final answer.
    - Behavior test: synthesis consumes validated outputs only (no direct retrieval in synthesis step).
    - Rubric test: final answer is coherent and addresses original query.

- [ ] P1 - LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): `LangGraphAgentScaffold` remains a placeholder dict with `compiled: False`.
  - Verification requirements:
    - Integration test: execution follows decomposition -> selection -> retrieval -> validation loop -> synthesis.
    - Integration test: each logical step is represented and executed as graph node/stage.
    - Integration test: graph state/projection is exposed for streaming heartbeat consumers.

- [ ] P2 - Streaming agent heartbeat (`specs/streaming-agent-heartbeat.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): no SSE/WebSocket endpoint or stream event contract.
  - Verification requirements:
    - Integration test: running query emits streamed sub-query updates during execution.
    - Integration test: events include sufficient progress state (active stage + completion/final answer).
    - Integration test: stream emits reliable terminal event in typical run.

- [ ] P2 - Demo TypeScript UI workflow (`specs/demo-ui-typescript.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): UI is static scaffold; no load action, query-run flow, stream subscription, or final answer panel.
  - Verification requirements:
    - Frontend interaction test: user can trigger data load/vectorize and sees deterministic success/error state.
    - Frontend interaction test: running query displays streamed sub-queries in near real time.
    - Frontend interaction test: UI shows heartbeat progress and final synthesized answer.
    - Frontend quality gate: TypeScript build/typecheck passes for new UI flow.

- [ ] P2 - MCP exposure wrapper (`specs/mcp-exposure.md`)
  - Status: Incomplete.
  - Why missing (code-confirmed): no MCP server/tool adapter in backend.
  - Verification requirements:
    - Integration test: MCP client sends query and receives synthesized final answer.
    - Integration test: MCP path delegates to same orchestration pipeline as HTTP path.
    - Stability test: repeated invocations preserve contract shape and success behavior.

## Cross-Cutting Delivery Rules
- [ ] For each new backend behavior, add at least one deterministic `@pytest.mark.smoke` test first or in same change.
- [ ] For each new frontend UI behavior, add at least one deterministic render/interaction test first or in same change.
- [ ] Keep tests outcome-focused (verify WHAT behavior is delivered, not HOW internals are implemented).
- [ ] Keep tests deterministic and CI-safe (no hidden external network dependencies).
- [ ] Every DB schema change must ship with an Alembic migration in the same change.
- [ ] Keep tracing integration isolated to startup/services (`src/backend/observability/*`), not directly coupled in router code.
