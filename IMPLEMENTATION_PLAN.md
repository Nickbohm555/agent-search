- [x] P0 - Add DeepAgent run config contract (`thread_id`, `user_id`, `checkpoint_id`) at `/api/agents/run` request/response boundaries and pass it through router -> service -> DeepAgent invocation config/context.
  Verification requirements (from `specs/deepagents-memory-subagents-checkpointing.md` Config acceptance criteria): backend smoke test verifies query-only payload still succeeds; payload with `thread_id`/`user_id`/`checkpoint_id` is accepted; omitted `thread_id` yields generated non-empty response `thread_id`; provided `thread_id` is preserved in response and execution metadata; optional `checkpoint_id` is echoed when supplied.
  Completed in this loop:
  - Extended `RuntimeAgentRunRequest` and `RuntimeAgentRunResponse` to support persistence config fields.
  - Propagated request payload through router/service into agent runtime config/context metadata.
  - Added smoke coverage in `src/backend/tests/api/test_deepagent_run_config.py` for generated and explicit config paths.
  - Verified with `docker compose exec backend uv run pytest tests/api -m smoke` and full required checks.

- [x] P0 - Compile and invoke DeepAgent with persistent checkpointer + cross-thread store, using runtime `user_id` context for namespace resolution.
  Verification requirements (from deepAgent Checkpointing + Memory acceptance criteria): backend smoke test verifies two runs with same `thread_id` expose persisted thread state (via run metadata/state inspection); different `thread_id` values do not share checkpoint state; run with valid `checkpoint_id` replays/forks without error; persistence-enabled runs remain compatible with existing response shape.
  Completed in this loop:
  - Added runtime persistence scaffolding in `src/backend/agents/langgraph_agent.py` using a shared in-process checkpointer (thread-scoped history) and cross-thread store (user namespace `(user_id, "memories")`).
  - Wired runtime context resolution so omitted `user_id` falls back to deterministic `"anonymous"` namespace, while explicit `user_id` controls store namespace selection.
  - Extended runtime graph execution metadata with `persistence` fields (`thread_checkpoint_count_before_run`, checkpoint replay info, `resolved_checkpoint_id`, `store_namespace`, store entry/thread summaries) without changing top-level API response shape.
  - Added backend smoke tests in `src/backend/tests/api/test_deepagent_persistence.py` covering same-thread persistence, thread isolation, checkpoint replay with valid checkpoint id, and user-scoped namespace reuse across threads.
  - Verified required checks:
    - Health: `curl http://localhost:8000/api/health` -> `200 {"status":"ok"}`.
    - Backend tests: `docker compose exec backend uv run pytest` -> `32 passed`.
    - Frontend tests: `docker compose exec frontend npm run test` -> `25 passed`.
    - Frontend typecheck: `docker compose exec frontend npm run typecheck` -> pass (exit 0).

- [x] P0 - Implement explicit memory routing using namespace `(user_id, "memories")` with read-before-execution and write-after-synthesis behavior.
  Verification requirements (from deepAgent Memory acceptance criteria): backend smoke test verifies memory written for `user_id=A` is retrieved on later `user_id=A` run; `user_id=B` cannot read A namespace memories; timeline/graph metadata includes a memory-read event before synthesis and memory-write event after synthesis; stored memory payload shape is deterministic for identical inputs.
  Completed in this loop:
  - Split scaffold persistence wiring in `src/backend/agents/langgraph_agent.py` into explicit checkpoint history (`persist_thread_checkpoint`) and cross-thread memory routing (`read_memories` + `write_memory`) using namespace `(user_id, "memories")`.
  - Added deterministic memory payload generation (`kind`, `query`, `summary`) with stable `memory_id` hashing so identical inputs produce identical stored memory payload identifiers.
  - Added timeline instrumentation for `memory.read` before decomposition/synthesis and `memory.write` after synthesis; exposed read/write records in `graph_state.graph.execution.persistence` metadata.
  - Added backend smoke coverage in `src/backend/tests/api/test_deepagent_persistence.py` for:
    - user-scoped memory retrieval on later runs for same `user_id`;
    - cross-user isolation (`user_id=B` cannot read `user_id=A` memories);
    - ordering of `memory.read` before synthesis and `memory.write` after synthesis;
    - deterministic stored memory payload/id for identical inputs.
  - Verified required checks:
    - Health: `curl http://localhost:8000/api/health` -> `200 {"status":"ok"}`.
    - Backend tests: `docker compose exec backend uv run pytest` -> `34 passed`.
    - Frontend tests: `docker compose exec frontend npm run test` -> `25 passed`.
    - Frontend typecheck: `docker compose exec frontend npm run typecheck` -> pass (exit 0).

- [x] P1 - Add at least one specialized DeepAgent subagent with required fields (`name`, `description`, `system_prompt`, `tools`) and delegate relevant subquery work through the DeepAgent `task` path.
  Verification requirements (from deepAgent Subagents acceptance criteria): backend smoke test verifies subagent definitions include required keys and callable tools; runtime timeline/metadata shows at least one delegation to the named subagent; delegated subquery returns a single summarized result consumed by existing retrieval/validation/synthesis output contract.
  Completed in this loop:
  - Implemented a specialized subagent definition in `src/backend/agents/langgraph_agent.py::get_subagents` with required DeepAgent keys and callable tools (`subquery-executor`).
  - Added DB-bound delegated tool wiring in `build_subquery_execution_tool` so each subquery executes retrieval + validation through a single delegated callable and returns a concise summary.
  - Routed runtime subquery execution via task-style delegation metadata in `LangGraphAgentScaffold.run`, including:
    - timeline events (`subagent.delegation` started/completed),
    - execution metadata (`execution.subagents`, `execution.delegations`),
    - per-subquery delegated summary while preserving existing retrieval/validation/synthesis response contract.
  - Added smoke coverage in `src/backend/tests/api/test_deepagent_subagents.py` for:
    - required subagent keys + callable tool definitions;
    - runtime evidence of delegation to `subquery-executor` via `"delegated_via": "task"` with one delegation per subquery and delegation timeline entries.
  - Updated orchestration smoke assertion in `src/backend/tests/api/test_orchestration_langgraph.py` to validate deep-agent node presence without brittle exact-node-list coupling.
  - Verified required checks:
    - Health: `curl http://localhost:8000/api/health` -> `200 {"status":"ok"}`.
    - Backend tests: `docker compose exec backend uv run pytest` -> `36 passed`.
    - Frontend tests: `docker compose exec frontend npm run test` -> `25 passed`.
    - Frontend typecheck: `docker compose exec frontend npm run typecheck` -> pass (exit 0).

- [ ] P2 - Extend run tracing metadata to include deepAgent persistence context (`thread_id`, `checkpoint_id`, `user_id`) while preserving no-op behavior when tracing is disabled.
  Verification requirements (from `specs/agent-run-tracing.md` + deepAgent JTBD): tracing-enabled smoke test verifies one span per run still includes query, agent identity, output, and persistence identifiers; tracing-disabled smoke test verifies API response behavior is unchanged and no tracing client call is attempted.

- [ ] P2 - Update frontend API request/response types and guards for optional deepAgent persistence fields without breaking current query-only runs.
  Verification requirements (supports deepAgent Config acceptance criteria): frontend unit test verifies `runAgent` accepts optional `thread_id`/`user_id`/`checkpoint_id`; response validator accepts `thread_id`/optional `checkpoint_id`; malformed payloads are still rejected; existing query-only tests continue to pass.

- [x] Complete (existing scaffold) - DeepAgent dependency and bootstrap are present (`deepagents` dependency + `create_deep_agent(...)` initialization path in `src/backend/agents/langgraph_agent.py`).

- [x] Complete (existing scaffold) - `/api/agents/run` is wired through router/service/factory to the runtime DeepAgent wrapper and returns `graph_state`.
