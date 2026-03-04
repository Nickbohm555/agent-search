# IMPLEMENTATION_PLAN

## Audit Snapshot (2026-03-04)
- Scope sources reviewed: `specs/*`, existing `IMPLEMENTATION_PLAN.md`, `src/*`.
- Confirmed implementation is scaffold-only:
  - Backend: `GET /api/health`, `GET /api/search-skeleton`, `GET /api/agents/runtime`, `POST /api/agents/run`.
  - Frontend: static scaffold page only.
  - Observability: Langfuse env parsing + startup handle placeholder only (no SDK client, no trace emission).
- `src/lib/*` does not exist in this repo; shared utilities currently live in `src/backend/utils/*` and `src/frontend/src/utils/*`.

## Completed
- [x] Scaffold stack and service topology are in place (`docker-compose.yml`, backend/frontend Dockerfiles, FastAPI + Vite app skeleton).
- [x] Health endpoint exists with smoke test coverage (`src/backend/tests/api/test_health.py`).
- [x] Baseline frontend render test exists (`src/frontend/src/App.test.tsx`).

## Prioritized Remaining Work (Plan Mode)

- [ ] P0. Add missing scaffold smoke coverage for existing API contract (stabilize baseline before feature work)
  - Spec alignment: project testing rules (`AGENTS.md` #32-36, #50).
  - Verification outcomes:
    - Backend smoke test verifies `GET /api/search-skeleton` returns scaffold status/message contract.
    - Backend smoke test verifies `GET /api/agents/runtime` returns non-empty `name` and semantic `version` string.
    - Backend smoke test verifies `POST /api/agents/run` returns `agent_name` and non-empty `output` for valid query.

- [ ] P0. Langfuse SDK setup (`specs/langfuse-sdk-setup.md`)
  - Current gap confirmed by code search: no Langfuse SDK dependency, no real client/tracer construction.
  - Verification outcomes (from acceptance criteria):
    - Backend smoke: with `LANGFUSE_ENABLED=true` and valid keys, app startup provides usable Langfuse handle on app state.
    - Backend smoke: with `LANGFUSE_ENABLED=false` or missing keys, app startup succeeds and tracing handle behaves as no-op.
    - Backend smoke/integration: a tracing path can create a trace/span via initialized handle without runtime error when enabled.

- [ ] P0. Agent run tracing at execution boundary (`specs/agent-run-tracing.md`)
  - Current gap confirmed by code search: `run_runtime_agent` has no instrumentation.
  - Verification outcomes (from acceptance criteria):
    - Backend smoke/integration: tracing-enabled `POST /api/agents/run` creates one trace/span containing query input, agent identity, and output.
    - Backend smoke: tracing-disabled `POST /api/agents/run` returns current behavior and creates no trace.
    - Backend smoke/integration: multiple consecutive runs create distinct traces/spans.

- [ ] P0. Data loading and vectorization (`specs/data-loading-vectorization.md`)
  - Current gap confirmed by code search: no loader endpoint/service/model for source ingestion/chunk/embed/store.
  - Verification outcomes (from acceptance criteria):
    - Backend smoke: load/vectorize trigger for at least one supported internal source returns clear observable outcome (`success`/`error`) with counts.
    - Backend smoke/integration: after successful load, vector store contains retrievable records tied to loaded corpus.
    - Backend smoke/integration: internal retrieval returns relevant content originating from loaded documents.

- [ ] P0. Query decomposition (`specs/query-decomposition.md`)
  - Current gap confirmed by code search: no decomposition component or schema/state contract.
  - Verification outcomes (from acceptance criteria):
    - Backend smoke: complex query produces ordered list with at least one focused sub-query.
    - Backend smoke: each sub-query is single-tool-answerable (internal-only or web-only, not inherently both).
    - Backend smoke/integration: produced sub-queries are available to downstream pipeline state and stream projection.

- [ ] P0. Tool selection per subquery (`specs/tool-selection-per-subquery.md`)
  - Current gap confirmed by code search: no selector implementation or assignment schema.
  - Verification outcomes (from acceptance criteria):
    - Backend smoke: every sub-query gets exactly one allowed assignment (`internal_rag` or `web_search`).
    - Backend smoke: no sub-query is assigned both tools.
    - Backend smoke/integration: assignments are exposed to retrieval/orchestration state (and stream projection if enabled).

- [ ] P0. Web tools: `web.search` + `web.open_url` (`specs/web-search-onyx-style.md`)
  - Current gap confirmed by code search: no web tool interfaces or implementations.
  - Verification outcomes (from acceptance criteria):
    - Backend smoke: `web.search` returns links/snippets metadata only (no full-page body payload).
    - Backend smoke: `web.open_url` returns main/full page content for requested URL.
    - Backend smoke/integration: agent retrieval path can perform search-then-open with observable opened URL record.

- [ ] P1. Per-subquery retrieval execution (`specs/per-subquery-retrieval.md`)
  - Current gap confirmed by code search: no retrieval executor consuming tool assignments.
  - Verification outcomes (from acceptance criteria):
    - Backend smoke: given sub-query + assignment, system executes correct retrieval path and returns consumable retrieval artifacts.
    - Backend smoke/integration: internal retrieval path returns only vector-store-backed internal content.
    - Backend smoke/integration: web retrieval path follows `search` then `open_url` behavior.

- [ ] P1. Retrieval validation loop (`specs/retrieval-validation.md`)
  - Current gap confirmed by code search: no sufficiency evaluation/loop state.
  - Verification outcomes (from acceptance criteria):
    - Backend smoke: each retrieval result is evaluated for sufficiency.
    - Backend smoke: insufficient results trigger at least one follow-up action (more retrieval or deeper read).
    - Backend smoke/integration: loop terminates via sufficiency or explicit stopping condition, producing final validation output state.

- [ ] P1. Answer synthesis (`specs/answer-synthesis.md`)
  - Current gap confirmed by code search: no synthesis step consuming validated subquery outputs.
  - Verification outcomes (from acceptance criteria):
    - Backend smoke: given original query + validated sub-query outputs, system returns one final synthesized answer.
    - Backend smoke: synthesis uses validated outputs only (no direct retrieval calls in synthesis component).
    - Backend smoke/rubric: final answer is coherent and addresses original query.

- [ ] P1. LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`)
  - Current gap confirmed by code search: only `LangGraphAgentScaffold` placeholder exists; no executable graph.
  - Verification outcomes (from acceptance criteria):
    - Backend smoke/integration: graph executes full flow in intended order: decomposition -> selection -> retrieval -> validation loop -> synthesis.
    - Backend smoke/integration: logical steps are represented as graph nodes and executed through a deep-agent path.
    - Backend smoke/integration: graph state/projection is available for streaming heartbeat consumers.

- [ ] P2. Streaming agent heartbeat (`specs/streaming-agent-heartbeat.md`)
  - Current gap confirmed by code search: no SSE/WebSocket endpoint or event protocol.
  - Verification outcomes (from acceptance criteria):
    - Backend integration: during query run, stream emits sub-query updates as generated.
    - Backend integration: stream emits enough progress state for live UI heartbeat (active step + completion/final answer).
    - Backend integration: typical run reliably reaches terminal event visible to connected client.

- [ ] P2. Demo UI TypeScript experience (`specs/demo-ui-typescript.md`)
  - Current gap confirmed by code search: no load controls, no query run workflow, no streaming consumer UI.
  - Verification outcomes (from acceptance criteria):
    - Frontend interaction test: user can trigger load/vectorize action and observe clear success or error outcome.
    - Frontend interaction test: running query displays streamed sub-queries in near real time.
    - Frontend interaction test: UI shows progress heartbeat and final synthesized answer on completion.

- [ ] P2. MCP exposure (`specs/mcp-exposure.md`)
  - Current gap confirmed by code search: no MCP server/tool wrapper present.
  - Verification outcomes (from acceptance criteria):
    - Integration/smoke: MCP client can submit query and receive final synthesized answer.
    - Integration/smoke: MCP path delegates to same orchestration pipeline as API run.
    - Integration/smoke: invocation contract remains stable across repeated calls.

## Cross-Cutting Delivery Rules (Keep Updated)
- [ ] For each first backend behavior, add at least one deterministic `@pytest.mark.smoke` outcome test first.
- [ ] For each first frontend UI behavior, add at least one deterministic render/interaction test first.
- [ ] Keep tests outcome-focused (what users/system observe), not implementation-detail assertions.
- [ ] Any DB schema change must include an Alembic migration in the same change set.
