# IMPLEMENTATION_PLAN

## Findings (2026-03-04)
- `specs/*` define a full RAG/agent pipeline; `src/*` is still scaffold-only.
- Confirmed implemented behavior is limited to:
  - `GET /api/health` returning `{"status":"ok"}`.
  - placeholder runtime agent response at `POST /api/agents/run`.
  - placeholder search scaffold endpoint at `GET /api/search-skeleton`.
- `src/lib/*` does not exist; shared utility areas currently present are `src/backend/utils/*` and `src/frontend/src/utils/*`.
- Existing observability code loads Langfuse env config and stores a startup handle, but no Langfuse SDK client dependency or real trace emission exists.

## Completed
- [x] Scaffold stack and service wiring (Docker Compose + FastAPI + React/TS + Postgres + Alembic + pgvector).
- [x] Health endpoint and smoke test baseline.

## Prioritized Remaining Work (Spec-Aligned)

- [ ] P0. Langfuse SDK setup (`specs/langfuse-sdk-setup.md`)
  - Implementation target: add Langfuse SDK dependency, initialize real/no-op handle at startup, expose usable tracing handle on `app.state`.
  - Required verification (outcome tests):
    - Backend smoke: app starts with `LANGFUSE_ENABLED=true` + valid keys and exposes enabled handle usable by request path.
    - Backend smoke: app starts with `LANGFUSE_ENABLED=false` (or missing keys) and tracing handle behaves as no-op without runtime errors.
    - Backend smoke: an agent run can call tracing handle methods successfully when enabled.

- [ ] P0. Agent run tracing instrumentation (`specs/agent-run-tracing.md`)
  - Implementation target: instrument agent execution boundary so every runtime agent run is traced when enabled.
  - Required verification (outcome tests):
    - Backend smoke: posting to `/api/agents/run` with tracing enabled emits one trace/span containing query input, agent identity, and output.
    - Backend smoke: with tracing disabled, `/api/agents/run` response matches non-traced behavior and emits no traces.
    - Backend smoke: two consecutive runs emit two distinct trace/span records.

- [ ] P0. Query decomposition + exclusive tool selection (`specs/query-decomposition.md`, `specs/tool-selection-per-subquery.md`)
  - Implementation target: produce ordered subqueries and assign exactly one tool (`internal_rag` or `web_search`) per subquery.
  - Required verification (outcome tests):
    - Backend smoke: complex query yields at least one focused subquery in deterministic output contract.
    - Backend smoke: every returned subquery has exactly one tool assignment; none has both tools.
    - Backend smoke: decomposition output and assignments are available in pipeline/stream-visible state payload.

- [ ] P0. Data loading and vectorization (`specs/data-loading-vectorization.md`)
  - Implementation target: trigger load for at least one internal source, chunk/embed/store into vector index for internal retrieval.
  - Required verification (outcome tests):
    - Backend smoke: load endpoint/action returns observable status (success/failure) plus document/chunk counts.
    - Backend smoke: successful load creates retrievable vector-backed records.
    - Backend smoke: relevant internal retrieval after load returns content grounded in loaded corpus.

- [ ] P0. Web tools (Onyx-style search + open_url split) (`specs/web-search-onyx-style.md`)
  - Implementation target: expose web search tool returning links/snippets and open_url tool returning page content.
  - Required verification (outcome tests):
    - Backend smoke: search tool returns links/snippets only (no full page body in search response).
    - Backend smoke: open_url returns full/main page content for provided URL.
    - Backend smoke: retrieval path shows observable search-then-open behavior with opened URL records/events.

- [ ] P1. Per-subquery retrieval executor (`specs/per-subquery-retrieval.md`)
  - Implementation target: dispatch each subquery to assigned tool path and return validation-consumable artifacts.
  - Required verification (outcome tests):
    - Backend smoke: internal assignment routes to internal retrieval and returns vector-store-derived artifacts.
    - Backend smoke: web assignment routes to web retrieval path using search + open_url outputs.
    - Backend smoke: retrieval output shape is consumable by validation component and stable across runs.

- [ ] P1. Retrieval validation loop (`specs/retrieval-validation.md`)
  - Implementation target: evaluate sufficiency per subquery and iterate follow-up retrieval/deepening until sufficient or stop condition.
  - Required verification (outcome tests):
    - Backend smoke: each subquery retrieval receives explicit sufficiency evaluation result.
    - Backend smoke: insufficient result triggers at least one follow-up retrieval/deepen action.
    - Backend smoke: loop terminates deterministically (sufficient or max-iteration/stop condition) and emits final validation state.

- [ ] P1. Answer synthesis (`specs/answer-synthesis.md`)
  - Implementation target: generate one final answer from original query + validated subquery outputs only.
  - Required verification (outcome tests):
    - Backend smoke: synthesis returns one final answer for provided original query + validated subquery inputs.
    - Backend smoke: synthesis step performs no direct retrieval calls; it only consumes validated outputs.
    - Backend smoke: missing/low-confidence validated inputs still return deterministic contract (answer + explicit limitation/fallback state).

- [ ] P1. LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`)
  - Implementation target: wire decomposition, selection, retrieval, validation loop, synthesis as executable LangGraph flow.
  - Required verification (outcome tests):
    - Backend smoke: end-to-end run executes all required logical stages in intended order, including per-subquery validation loop.
    - Backend smoke: deep-agent subgraph/tool execution path is invoked for subquery handling.
    - Backend smoke: graph state/projection exposes progress data consumable by streaming layer.

- [ ] P2. Streaming heartbeat service (`specs/streaming-agent-heartbeat.md`)
  - Implementation target: real-time stream of subqueries/progress/final answer driven by orchestration state.
  - Required verification (outcome tests):
    - Backend smoke: running a query emits streamed subquery events before terminal completion.
    - Backend smoke: stream includes enough progress state for UI to render active step + final answer.
    - Backend smoke: typical run ends with reliable terminal event (no dropped completion state).

- [ ] P2. Demo TypeScript UI for load/run/stream (`specs/demo-ui-typescript.md`)
  - Implementation target: TS UI for triggering load, running query, rendering streamed subqueries/progress/final answer.
  - Required verification (outcome tests):
    - Frontend render/interaction test: user can trigger load and see loading -> success/error outcome.
    - Frontend render/interaction test: during run, streamed subqueries/progress appear in UI before final answer.
    - Frontend render/interaction test: final answer is rendered when stream reports completion.

- [ ] P2. MCP exposure (`specs/mcp-exposure.md`)
  - Implementation target: expose pipeline through MCP-compatible wrapper for client invocation.
  - Required verification (outcome tests):
    - Backend smoke/integration: MCP client can submit query and receive final synthesized answer.
    - Backend smoke/integration: MCP wrapper delegates to same orchestration pipeline as API run path.
    - Backend smoke/integration: repeated MCP calls follow stable invocation/response contract.

## Cross-Cutting Test Policy (Keep Incomplete Until Enforced per Task)
- [ ] Add at least one backend smoke test first for each new backend behavior (`src/backend/tests/api`, `@pytest.mark.smoke`).
- [ ] Add at least one frontend render/interaction test first for each new UI behavior.
- [ ] Keep tests deterministic and outcome-based; avoid assertions on private implementation details or hidden network dependencies.
- [ ] Any DB schema change must include Alembic migration in same change.
