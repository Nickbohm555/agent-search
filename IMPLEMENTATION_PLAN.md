# IMPLEMENTATION_PLAN

- Scope: `backend: langchain / langgraph setup, MCP setup, streaming backend, vectorization, doc retrieval, subquestion decomp, agentic design` only.
- Inputs reviewed: `specs/*`, existing `IMPLEMENTATION_PLAN.md`, `src/backend/*`, `src/frontend/src/lib/*` (no top-level `src/lib/*` exists in this repo).

## Highest Priority Incomplete Tasks

- [ ] P0 - Add LangChain runtime boundary and configuration wiring (`specs/langchain-runtime-setup.md`).
  - Implementation scope:
    - Add LangChain/LangGraph runtime dependencies and a single backend runtime integration boundary (service/app-state) consumed by agent orchestration.
    - Keep routers SDK-agnostic; runtime boundary must degrade gracefully when disabled/misconfigured.
    - Add deterministic stub mode for CI so agent runs do not require external model/network access.
  - Verification requirements (outcome-focused):
    - Smoke: with runtime enabled config, backend startup succeeds and `/api/agents/run` completes without runtime wiring errors.
    - Smoke: with runtime disabled/missing config, backend still starts and `/api/agents/run` returns a deterministic non-crashing contract (or explicit controlled error contract).
    - Test: enabled/disabled modes are covered using stubs/mocks only (no hidden external model calls in CI).

- [ ] P0 - Replace scaffold orchestration with executable LangGraph flow and deep-agent execution (`specs/orchestration-langgraph.md`).
  - Implementation scope:
    - Execute pipeline as real LangGraph nodes/edges for decomposition -> tool selection -> retrieval -> validation -> synthesis.
    - Model subquery handling as deep-agent/subgraph execution.
    - Preserve graph-state projection/events for downstream streaming and MCP consumers.
  - Verification requirements (outcome-focused):
    - Smoke: full pipeline runs as LangGraph graph for mixed-domain query and returns final answer.
    - Smoke: logical steps execute in intended order; validation loops per subquery until sufficient or stopping condition.
    - Smoke: deep-agent execution is observable in graph state/timeline payloads.
    - Edge-case: multi-subquery run preserves aligned output shapes (subqueries/tool assignments/retrieval/validation remain index-consistent).

- [ ] P0 - Implement streaming heartbeat endpoint driven by orchestration state (`specs/streaming-agent-heartbeat.md`).
  - Implementation scope:
    - Add backend streaming delivery (SSE or WebSocket) for run progress.
    - Emit subqueries and progress/step updates from orchestration events, including completion payload.
    - Ensure clean cancellation/disconnect handling.
  - Verification requirements (outcome-focused):
    - Smoke: running a query through stream endpoint emits subquery updates while run is in progress (not only at end).
    - Smoke: stream provides enough events for UI heartbeat (current step/progress plus final answer/completion event).
    - Edge-case: client disconnect/interruption closes stream cleanly and does not crash backend processing.
    - Contract: event schema is parseable and event ordering is stable for typical runs.

- [ ] P0 - Expose pipeline through MCP wrapper compatible with FastMCP client usage (`specs/mcp-exposure.md`).
  - Implementation scope:
    - Add MCP server/tool wrapper to invoke pipeline query->final-answer flow.
    - Delegate directly to same orchestration path used by API run.
    - Keep invocation contract stable; streaming via MCP optional unless explicitly wired.
  - Verification requirements (outcome-focused):
    - Smoke: MCP client call with query returns synthesized final answer.
    - Smoke: MCP response contract matches API run final-answer semantics for equivalent input.
    - Contract: tool name and request/response shape are deterministic for client integration.
    - Optional smoke (if implemented): MCP transport surfaces progress events for in-flight runs.

- [ ] P1 - Upgrade internal vectorization/retrieval to pgvector-backed storage and search (`specs/data-loading-vectorization.md`, `specs/per-subquery-retrieval.md`).
  - Implementation scope:
    - Replace JSON embedding storage/retrieval path with pgvector column/indexed similarity queries.
    - Keep load endpoint outcome observability (document/chunk counts).
    - Ensure retrieval continues to return internal-store-only evidence for internal assignments.
  - Verification requirements (outcome-focused):
    - Smoke: data load writes vectorized chunks to DB-backed vector store and returns observable load counts.
    - Smoke: after load, internal-assigned subquery retrieves relevant loaded content.
    - Edge-case: empty/unrelated corpus yields deterministic empty-or-low-signal retrieval contract without crashing.
    - Migration check: required schema/index changes ship with Alembic migration in same change.

- [ ] P1 - Strengthen decomposition outcomes for agentic routing quality (`specs/query-decomposition.md`).
  - Implementation scope:
    - Improve decomposition quality for complex prompts while preserving deterministic behavior in tests.
    - Ensure produced subqueries are available to orchestration state and streaming payloads.
  - Verification requirements (outcome-focused):
    - Smoke: complex query yields >=1 focused subquery and avoids mixed internal+web intent inside a single subquery.
    - Smoke: produced subqueries are exposed in run response and stream events.
    - Edge-case: connector-heavy/duplicate phrasing does not produce duplicate or empty subqueries.

- [ ] P1 - Expand per-subquery retrieval+validation observability for agentic control (`specs/per-subquery-retrieval.md`, `specs/retrieval-validation.md`).
  - Implementation scope:
    - Ensure retrieval path fidelity by assignment (internal -> internal store, web -> search+open_url).
    - Surface validation-loop transitions as observable state/events per subquery.
  - Verification requirements (outcome-focused):
    - Smoke: internal assignment uses internal retrieval only; web assignment uses search+open_url behavior.
    - Smoke: insufficient evidence triggers at least one follow-up action and then stops with explicit terminal status.
    - Contract: validation outcomes and follow-up actions are visible per subquery in timeline/event payloads.

## Scoped Items Confirmed Complete (No New Task)

- [x] Baseline decomposition utility exists and is exercised by smoke tests (`specs/query-decomposition.md` baseline).
- [x] Baseline one-tool-per-subquery assignment exists and is smoke tested (`specs/tool-selection-per-subquery.md`).
- [x] Baseline web tools (`search` + `open_url`) exist and are smoke tested (`specs/web-search-onyx-style.md`).
- [x] Baseline retrieval-validation loop behavior is implemented and smoke tested (`specs/retrieval-validation.md` baseline).
- [x] Baseline synthesis step is implemented and smoke tested (`specs/answer-synthesis.md` baseline).
- [x] Baseline internal load/retrieve endpoints exist with deterministic tests; currently uses JSON embeddings (not pgvector-native yet).
- [x] Langfuse SDK setup and agent-run tracing baseline are present as adjacent context (`specs/langfuse-sdk-setup.md`, `specs/agent-run-tracing.md`).

## Gap Confirmation Notes (Code Search)

- Streaming backend route not found: no `/api/agents/stream` (or equivalent SSE/WebSocket endpoint) in `src/backend/routers/*`.
- MCP server/wrapper not found: no MCP/FastMCP implementation in backend source.
- LangChain/LangGraph runtime dependency wiring absent: `pyproject.toml` does not include `langchain`/`langgraph`; current `agents/langgraph_agent.py` is a scaffold/projection, not real LangGraph runtime execution.
- pgvector-native storage/querying absent: chunk embeddings currently stored in `embedding_json` text with Python cosine scoring.
