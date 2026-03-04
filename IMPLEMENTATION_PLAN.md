# IMPLEMENTATION_PLAN

## Status Snapshot (2026-03-04)
- Repository state remains scaffold-only after comparing `specs/*` with `src/*`.
- `src/lib/*` does not exist (confirmed via `rg --files src/lib`).
- Existing working scaffold behavior confirmed:
  - `GET /api/health` returns `{"status":"ok"}`.
  - `GET /api/search-skeleton` returns scaffold status/message.
  - `GET /api/agents/runtime` returns scaffold agent identity.
  - `POST /api/agents/run` returns scaffold agent output.
  - Startup sets `app.state.langfuse` via credential-aware Langfuse initializer.
  - Alembic baseline exists with no domain tables.
  - Frontend renders static scaffold shell only.
- Existing tests confirmed:
  - Backend: smoke tests now cover `health`, `search-skeleton`, `agents/runtime`, and `agents/run` (including empty-query validation).
  - Frontend: `src/frontend/src/App.test.tsx` heading render only.
- Newly implemented this iteration:
  - Added agent-run tracing at the execution boundary so enabled Langfuse handles receive `agent.run` span creation with query input, agent identity metadata, and run output.
  - Routed `request.app.state.langfuse` into the agent service to keep instrumentation centralized in service execution rather than router logic.
  - Added backend smoke tests for enabled trace creation, disabled no-trace behavior, and distinct spans for consecutive runs.

## Completed
- [x] Scaffold FastAPI app with baseline routers, services, and schemas.
- [x] Scaffold runtime agent factory/wrapper and placeholder LangGraph agent object.
- [x] Scaffold observability config loader and startup wiring for Langfuse handle.
- [x] Scaffold React/TypeScript/Vite frontend shell with API base config helper.
- [x] Scaffold Docker Compose + Postgres + Alembic + pgvector infrastructure.
- [x] P0 - Add smoke coverage for existing scaffold endpoints
  - Added outcome-focused smoke tests for `GET /api/search-skeleton`, `GET /api/agents/runtime`, `POST /api/agents/run`, and empty-query validation behavior.
- [x] P0 - Implement Langfuse SDK initialization (`specs/langfuse-sdk-setup.md`)
  - Added `langfuse==2.60.1` to backend dependencies.
  - Replaced placeholder initializer with environment/credential-aware Langfuse client setup.
  - Startup remains resilient when disabled or misconfigured by returning a no-op tracing handle.
  - Added smoke tests covering enabled startup wiring and disabled graceful behavior.
- [x] P0 - Instrument agent-run tracing (`specs/agent-run-tracing.md`)
  - Added tracing instrumentation in `run_runtime_agent()` so all runtime-agent executions pass through a single trace boundary.
  - Trace/span payload now includes query input, agent name metadata, and output response for each run when tracing is enabled.
  - Added smoke coverage to verify enabled tracing payload, disabled graceful behavior, and distinct spans across consecutive runs.

## Remaining Work (Prioritized)

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

## BLOCKED (2026-03-04)
- Blocker: Missing Docker daemon access in this execution environment (cannot connect to `/Users/nickbohm/.docker/run/docker.sock`), which prevents required compose-based verification commands.
  - Failed commands:
    - `docker compose ps` -> `permission denied while trying to connect to the Docker daemon socket ... connect: operation not permitted`
    - `docker compose up -d` -> same daemon socket permission error.
    - `docker compose exec backend uv run pytest` -> same daemon socket permission error.
    - `docker compose exec frontend npm run test` -> same daemon socket permission error.
    - `docker compose exec frontend npm run typecheck` -> same daemon socket permission error.
    - `curl -sS http://localhost:8000/api/health` -> `curl: (7) Couldn't connect to server`.
- Secondary local-environment blockers when attempting non-Docker fallback:
  - Failed commands:
    - `(repo root) python3 -m pytest src/backend/tests/api/test_agent_run_tracing.py` initially failed due runtime annotation compatibility (`Any | None`) under local Python 3.9.
    - `(src/frontend) npm run test -- --run` -> `sh: vitest: command not found`
    - `(src/frontend) npm run typecheck` -> `sh: tsc: command not found`
  - Supplemental successful fallback checks (non-authoritative for compose gate):
    - `(repo root) python3 -m pytest src/backend/tests/api/test_agent_run_tracing.py` -> `3 passed` (after annotation compatibility fix).
    - `(repo root) python3 -m pytest src/backend/tests` -> `11 passed`.
- Repository/git transport blockers in this sandbox:
  - Failed commands:
    - `git add -A && git commit -m "blocked: instrument agent run tracing with smoke tests"` -> `fatal: Unable to create '.git/index.lock': Operation not permitted`
    - `git push` -> `Could not resolve host: github.com`
- Next action:
  - Run checks on a host with Docker daemon access and installed project dependencies, then re-run required gates:
    - `docker compose up -d`
    - `docker compose ps`
    - `docker compose exec backend uv run pytest`
    - `docker compose exec frontend npm run test`
    - `docker compose exec frontend npm run typecheck`
    - Health check: `curl http://localhost:8000/api/health`
  - Install frontend dependencies before local frontend checks:
    - `(src/frontend) npm ci`
  - Complete commit/push on a host with git write/network access:
    - `git add -A`
    - `git commit -m "blocked: instrument agent run tracing with smoke tests"`
    - `git push`
