- [x] P0 - Add DeepAgent run config contract (`thread_id`, `user_id`, `checkpoint_id`) at `/api/agents/run` request/response boundaries and pass it through router -> service -> DeepAgent invocation config/context.
  Verification requirements (from `specs/deepagents-memory-subagents-checkpointing.md` Config acceptance criteria): backend smoke test verifies query-only payload still succeeds; payload with `thread_id`/`user_id`/`checkpoint_id` is accepted; omitted `thread_id` yields generated non-empty response `thread_id`; provided `thread_id` is preserved in response and execution metadata; optional `checkpoint_id` is echoed when supplied.
  Completed in this loop:
  - Extended `RuntimeAgentRunRequest` and `RuntimeAgentRunResponse` to support persistence config fields.
  - Propagated request payload through router/service into agent runtime config/context metadata.
  - Added smoke coverage in `src/backend/tests/api/test_deepagent_run_config.py` for generated and explicit config paths.
  - Verified with `docker compose exec backend uv run pytest tests/api -m smoke` and full required checks.

- [ ] P0 - Compile and invoke DeepAgent with persistent checkpointer + cross-thread store, using runtime `user_id` context for namespace resolution.
  Verification requirements (from deepAgent Checkpointing + Memory acceptance criteria): backend smoke test verifies two runs with same `thread_id` expose persisted thread state (via run metadata/state inspection); different `thread_id` values do not share checkpoint state; run with valid `checkpoint_id` replays/forks without error; persistence-enabled runs remain compatible with existing response shape.

- [ ] P0 - Implement explicit memory routing using namespace `(user_id, "memories")` with read-before-execution and write-after-synthesis behavior.
  Verification requirements (from deepAgent Memory acceptance criteria): backend smoke test verifies memory written for `user_id=A` is retrieved on later `user_id=A` run; `user_id=B` cannot read A namespace memories; timeline/graph metadata includes a memory-read event before synthesis and memory-write event after synthesis; stored memory payload shape is deterministic for identical inputs.

- [ ] P1 - Add at least one specialized DeepAgent subagent with required fields (`name`, `description`, `system_prompt`, `tools`) and delegate relevant subquery work through the DeepAgent `task` path.
  Verification requirements (from deepAgent Subagents acceptance criteria): backend smoke test verifies subagent definitions include required keys and callable tools; runtime timeline/metadata shows at least one delegation to the named subagent; delegated subquery returns a single summarized result consumed by existing retrieval/validation/synthesis output contract.

- [ ] P2 - Extend run tracing metadata to include deepAgent persistence context (`thread_id`, `checkpoint_id`, `user_id`) while preserving no-op behavior when tracing is disabled.
  Verification requirements (from `specs/agent-run-tracing.md` + deepAgent JTBD): tracing-enabled smoke test verifies one span per run still includes query, agent identity, output, and persistence identifiers; tracing-disabled smoke test verifies API response behavior is unchanged and no tracing client call is attempted.

- [ ] P2 - Update frontend API request/response types and guards for optional deepAgent persistence fields without breaking current query-only runs.
  Verification requirements (supports deepAgent Config acceptance criteria): frontend unit test verifies `runAgent` accepts optional `thread_id`/`user_id`/`checkpoint_id`; response validator accepts `thread_id`/optional `checkpoint_id`; malformed payloads are still rejected; existing query-only tests continue to pass.

- [x] Complete (existing scaffold) - DeepAgent dependency and bootstrap are present (`deepagents` dependency + `create_deep_agent(...)` initialization path in `src/backend/agents/langgraph_agent.py`).

- [x] Complete (existing scaffold) - `/api/agents/run` is wired through router/service/factory to the runtime DeepAgent wrapper and returns `graph_state`.
