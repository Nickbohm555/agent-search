# IMPLEMENTATION_PLAN

## Audit Snapshot (2026-03-04)
- `specs/*` define a full pipeline; implementation in `src/*` is scaffold-first.
- Confirmed implemented behavior in code:
  - `GET /api/health` returns `{"status":"ok"}`.
  - `GET /api/agents/runtime` returns scaffold agent metadata.
  - `POST /api/agents/run` returns scaffold agent output.
  - `GET /api/search-skeleton` returns placeholder search status.
- `src/lib/*` is not present in this repo; current shared utility locations are `src/backend/utils/*` and `src/frontend/src/utils/*`.
- Langfuse wiring is partial: env loading and startup handle exist, but no Langfuse SDK dependency or real trace emission.

## Completed
- [x] Scaffold stack exists (Docker Compose + FastAPI + React/TypeScript/Vite + Postgres + Alembic + pgvector).
- [x] Health endpoint implemented with smoke coverage (`src/backend/tests/api/test_health.py`).
- [x] Baseline frontend scaffold render test exists (`src/frontend/src/App.test.tsx`).

## Prioritized Remaining Tasks

- [ ] P0. Langfuse SDK setup (`specs/langfuse-sdk-setup.md`)
  - Verification outcomes:
    - Backend smoke: app starts with `LANGFUSE_ENABLED=true` and valid keys, exposing a usable Langfuse handle from app state.
    - Backend smoke: app starts with `LANGFUSE_ENABLED=false` (or missing keys) and tracing calls are graceful no-op.
    - Backend smoke: a traced request path can create a trace/span with no runtime error when enabled.

- [ ] P0. Agent run tracing at execution boundary (`specs/agent-run-tracing.md`)
  - Verification outcomes:
    - Backend smoke: `POST /api/agents/run` with tracing enabled records one run trace/span containing query input, agent identity, and output.
    - Backend smoke: same endpoint with tracing disabled preserves response behavior and emits no trace.
    - Backend smoke: consecutive runs create distinct observations.

- [ ] P0. Query decomposition (`specs/query-decomposition.md`)
  - Verification outcomes:
    - Backend smoke: complex query yields an ordered list with at least one focused sub-query.
    - Backend smoke: produced sub-queries are emitted in pipeline state consumable by downstream components/streaming.
    - Backend smoke: decomposition output is deterministic for fixed test input (stable contract shape).

- [ ] P0. Tool selection per subquery (`specs/tool-selection-per-subquery.md`)
  - Verification outcomes:
    - Backend smoke: every sub-query receives exactly one assignment from allowed set (`internal_rag` or `web_search`).
    - Backend smoke: no sub-query is assigned both tools.
    - Backend smoke: assignments are available to retrieval/orchestration state.

- [ ] P0. Web search tools: `search` + `open_url` (`specs/web-search-onyx-style.md`)
  - Verification outcomes:
    - Backend smoke: `web.search` returns links/snippets metadata only (no full page body).
    - Backend smoke: `web.open_url` returns page main/full content for a provided URL.
    - Backend smoke: retrieval flow can perform search-then-open with observable opened URL records.

- [ ] P0. Data loading and vectorization (`specs/data-loading-vectorization.md`)
  - Verification outcomes:
    - Backend smoke: load/vectorize action for at least one internal source returns observable status (`success`/`error`) and counts.
    - Backend smoke: successful load creates retrievable vector-backed records.
    - Backend smoke: relevant internal retrieval returns content from loaded corpus.

- [ ] P1. Per-subquery retrieval executor (`specs/per-subquery-retrieval.md`)
  - Verification outcomes:
    - Backend smoke: `internal_rag` assignments route to vector-store retrieval only.
    - Backend smoke: `web_search` assignments route to web search + open_url path.
    - Backend smoke: retrieval artifact contract is consumable by validation/synthesis steps.

- [ ] P1. Retrieval validation loop (`specs/retrieval-validation.md`)
  - Verification outcomes:
    - Backend smoke: each sub-query retrieval result is evaluated for sufficiency.
    - Backend smoke: insufficient results trigger at least one follow-up action (broaden retrieval or deeper read).
    - Backend smoke: loop terminates by sufficiency or explicit stop condition, with final state exposed.

- [ ] P1. Answer synthesis (`specs/answer-synthesis.md`)
  - Verification outcomes:
    - Backend smoke: synthesis returns one final answer for original query plus validated sub-query outputs.
    - Backend smoke: synthesis does not perform direct retrieval; it consumes validated outputs only.
    - Backend smoke: low-confidence/missing validated inputs still produce deterministic response contract with explicit limitation.

- [ ] P1. LangGraph orchestration with deep agents (`specs/orchestration-langgraph.md`)
  - Verification outcomes:
    - Backend smoke: end-to-end run executes decomposition -> selection -> retrieval -> validation loop -> synthesis in intended order.
    - Backend smoke: deep-agent path is used for sub-query handling/tool execution.
    - Backend smoke: graph state/projection exposes progress updates consumable by streaming/MCP layers.

- [ ] P2. Streaming agent heartbeat (`specs/streaming-agent-heartbeat.md`)
  - Verification outcomes:
    - Backend smoke: query run emits streamed sub-query events before completion.
    - Backend smoke: stream includes progress signals sufficient for UI heartbeat (active step + final completion).
    - Backend smoke: terminal completion event is reliable in typical run.

- [ ] P2. Demo UI in TypeScript (`specs/demo-ui-typescript.md`)
  - Verification outcomes:
    - Frontend interaction test: user can trigger data load and observe loading then success/error outcome.
    - Frontend interaction test: running a query renders streamed sub-queries/progress before final answer.
    - Frontend interaction test: final answer appears on stream completion.

- [ ] P2. MCP exposure (`specs/mcp-exposure.md`)
  - Verification outcomes:
    - Backend integration/smoke: MCP client submits query and receives final synthesized answer.
    - Backend integration/smoke: MCP wrapper delegates to same orchestration path as API run.
    - Backend integration/smoke: repeated MCP invocations follow stable request/response contract.

## Cross-Cutting Quality Gates
- [ ] For each new backend behavior, add at least one `@pytest.mark.smoke` API outcome test first.
- [ ] For each new frontend behavior, add at least one render/interaction test first.
- [ ] Keep tests deterministic and outcome-based; avoid assertions on internal implementation details.
- [ ] Include Alembic migration in same change as any DB schema change.
