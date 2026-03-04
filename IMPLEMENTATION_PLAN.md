# IMPLEMENTATION_PLAN

## Scope
- Scoped target: `backend: langchain / langgraph setup, MCP setup, streaming backend, vectorization, doc retrieval, subquestion decomposition, agentic design` only.
- Sources reviewed this run: `specs/*`, `src/backend/*`, `src/frontend/src/lib/*`, existing `IMPLEMENTATION_PLAN.md`.
- Note: top-level `src/lib/*` does not exist in this repo; shared UI library code is under `src/frontend/src/lib/*`.
- Project state constraint: scaffold-first; prefer tests alongside first implementation.

## Current Scoped Status (Confirmed via Code Search)
- [x] Query decomposition exists in backend (`utils/query_decomposition.py`) and is exercised through `/api/agents/run` smoke tests.
- [x] Per-subquery tool assignment (internal vs web) exists (`utils/tool_selection.py`) with outcome coverage in API smoke tests.
- [x] Vectorization + internal retrieval baseline exists (`services/internal_data_service.py`, `models.py`, Alembic `0002_internal_data_tables.py`) with smoke coverage.
- [x] Web retrieval search+open_url baseline exists (`services/web_service.py`, `/api/web/*`) with smoke coverage.
- [x] Validation loop and synthesis baseline exist and are covered by smoke tests.
- [x] LangGraph-shaped orchestration scaffold exists (`agents/langgraph_agent.py`) with graph-state timeline tests.
- [ ] Real streaming backend endpoint is missing (no SSE/WebSocket route; only non-stream `/api/agents/run` response).
- [ ] MCP exposure is missing (no MCP server/wrapper/tool contract implementation found).
- [ ] Explicit LangChain runtime setup is missing (no `langchain` dependency/wiring; added spec: `specs/langchain-runtime-setup.md`).
- [ ] Agentic execution is scaffolded but not implemented as true LangGraph runtime/deep-agent execution with runtime state/event hooks.

## Prioritized Scoped Tasks (Highest Priority Incomplete First)
- [ ] P0 - Implement LangChain runtime setup boundary (`specs/langchain-runtime-setup.md`)
- Verification requirements:
- Add smoke test: with runtime enabled config, backend startup succeeds and `/api/agents/run` executes without runtime wiring errors.
- Add smoke test: with runtime disabled/missing config, backend startup still succeeds and run path returns deterministic non-crashing contract.
- Add deterministic unit/smoke test: enabled-mode execution uses stubs/mocks only (no hidden external model/network dependency).

- [ ] P0 - Replace LangGraph scaffold projection with executable LangGraph flow + deep-agent structure (`specs/orchestration-langgraph.md`)
- Verification requirements:
- Add smoke test: decomposition -> tool_selection -> retrieval -> validation -> synthesis execute in intended order for a mixed query.
- Add smoke test: per-subquery validation loop retries until sufficient or stop condition and surfaces final status per subquery.
- Add smoke test: graph state projection remains consumable by downstream streaming service (step/state payloads observable during run).
- Add edge-case test: multi-subquery run preserves deterministic output shape (no missing subquery/tool/result alignment).

- [ ] P0 - Add streaming backend heartbeat contract and endpoint (`specs/streaming-agent-heartbeat.md`)
- Verification requirements:
- Add smoke test: running a query through stream endpoint emits sub-query events before completion.
- Add smoke test: stream emits sufficient progress events for UI heartbeat (current step/status transitions + completion payload).
- Add smoke test: interrupted/disconnected stream closes cleanly and does not crash backend worker.
- Add deterministic contract test: streamed events are ordered and parseable with stable event schema.

- [ ] P0 - Implement MCP wrapper for pipeline invocation (FastMCP-compatible) (`specs/mcp-exposure.md`)
- Verification requirements:
- Add smoke test: MCP client invocation sends query and receives final synthesized answer.
- Add smoke test: MCP wrapper delegates to backend orchestration path and returns same final-answer contract as API run.
- Add contract test: invocation shape/tool name is stable for client integration (deterministic request/response schema).
- Add optional smoke test (if streaming exposed via MCP): progress/sub-query updates are observable over MCP transport.

- [ ] P1 - Harden vector store implementation to pgvector-backed retrieval path (`specs/data-loading-vectorization.md`, `specs/per-subquery-retrieval.md`)
- Verification requirements:
- Add smoke test: load endpoint writes chunked vectors into DB-backed store and returns observable load counts.
- Add smoke test: after load, relevant internal subquery retrieves loaded document content only from internal store.
- Add edge-case test: retrieval with empty/unrelated corpus returns deterministic empty-or-low-signal result contract without crashing.
- Add migration verification: schema/index changes required for vector ops ship with Alembic migration in same change.

- [ ] P1 - Strengthen decomposition quality and observability for downstream orchestration (`specs/query-decomposition.md`)
- Verification requirements:
- Add smoke test: complex mixed-domain query yields >=1 focused subquery and avoids mixed internal+web intent in a single subquery.
- Add smoke test: produced subqueries are exposed in run response and stream payloads for downstream consumption.
- Add edge-case test: duplicate/connector-heavy phrasing does not create duplicate empty subqueries.

- [ ] P1 - Tighten per-subquery retrieval + validation observability for agentic control (`specs/per-subquery-retrieval.md`, `specs/retrieval-validation.md`)
- Verification requirements:
- Add smoke test: internal assignment uses internal retrieval path; web assignment uses search+open_url path.
- Add smoke test: insufficient retrieval triggers at least one follow-up action and ends with explicit stop/validated status.
- Add deterministic test: validation outcomes are observable in timeline/event payloads for each subquery.

## Scoped Tasks Already Considered Complete (No New Work This Run)
- [x] Baseline internal data load/retrieve endpoints and deterministic local embedding scaffold are implemented with smoke tests.
- [x] Baseline web search/open_url tool endpoints exist with smoke tests.
- [x] Baseline synthesis consumes validated outputs and is covered by smoke tests.
- [x] Langfuse startup + agent-run tracing baseline exists (outside this scoped plan except as integration context).

## Notes For Next Implementation Loop
- First implementation slice should be P0 LangChain runtime boundary + executable LangGraph integration because streaming and MCP depend on orchestration state/event hooks.
- Keep routers thin; place runtime/model/tracing orchestration in backend services/agents per repository conventions.
- Preserve deterministic test posture: mock model/tool/network dependencies in CI-facing tests.
