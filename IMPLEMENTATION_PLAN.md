- [ ] P0 - Add DeepAgent run config contract at API boundary (`thread_id`, `user_id`, `checkpoint_id`) and propagate it end-to-end through router/service/agent invocation context.
  Verification requirements (from `specs/deepagents-memory-subagents-checkpointing.md` acceptance criteria): backend smoke test proves `/api/agents/run` accepts query-only payloads and payloads with config fields; when `thread_id` is omitted the response includes a generated non-empty `thread_id`; when `thread_id` is provided it is preserved in the response and used for execution config; optional `checkpoint_id` is accepted and echoed when replay is requested; existing clients that send only `query` still receive a valid run response.

- [ ] P0 - Compile/invoke DeepAgent with persistence wiring (checkpointer + store) and runtime context (`user_id`) for durable thread state and cross-thread memory access.
  Verification requirements: backend smoke test proves same `thread_id` run sequence yields persisted graph state accessible via runtime state inspection; different `thread_id` values do not share thread checkpoints/state; run with valid `checkpoint_id` can replay/fork without crash; runs still succeed when persistence identifiers are omitted (generated/default path).

- [ ] P0 - Implement explicit memory routing with user namespace `(user_id, "memories")`: read at run start, write after synthesis with deterministic payload shape.
  Verification requirements: backend smoke test proves memory written for `user_id=A` is retrieved in a later run for `user_id=A`; `user_id=B` cannot retrieve A’s memories; run timeline/metadata includes an observable memory-read step before synthesis and a memory-write step after synthesis; memory record shape is deterministic for the same input.

- [ ] P1 - Define at least one specialized DeepAgent subagent (required keys + tool set) and delegate subquery work through the DeepAgent task delegation path.
  Verification requirements: backend smoke test proves subagent config includes required fields (`name`, `description`, `system_prompt`, `tools`); runtime timeline/metadata shows delegation to the named subagent for at least one subquery; delegated execution returns one summarized result per delegated task and feeds existing retrieval/validation flow.

- [ ] P1 - Preserve orchestration output contract while adding deepAgent features (`sub_queries`, `tool_assignments`, `retrieval_results`, `validation_results`, `output`, ordered timeline), with persistence-aware metadata.
  Verification requirements (cross-check `specs/orchestration-langgraph.md` + deepAgent spec): backend smoke test proves timeline ordering remains decomposition -> tool_selection -> per-subquery retrieval/validation -> synthesis; each subquery has exactly one tool assignment; insufficient evidence still triggers follow-up then deterministic stop; synthesis output uses validated evidence and reports insufficiency when validation fails.

- [ ] P2 - Extend agent-run tracing metadata to include persistence context (`thread_id`, `checkpoint_id`, `user_id`) while preserving current no-op behavior when tracing is disabled.
  Verification requirements (from `specs/agent-run-tracing.md` + deepAgent spec): tracing-enabled smoke test proves one span per run still exists with query, agent identity, output, and persistence identifiers; tracing-disabled test proves no span creation attempts and identical API behavior.

- [ ] P2 - Update frontend API contract/types to support optional deepAgent persistence fields in request/response without breaking current query-only flow.
  Verification requirements: frontend unit test proves `runAgent` accepts optional `thread_id`/`user_id`/`checkpoint_id` request fields and treats returned `thread_id`/`checkpoint_id` as valid response shape; malformed-response guard still rejects invalid payloads; existing tests for query-only calls keep passing.

- [x] Complete (existing scaffold) - DeepAgent dependency + runtime bootstrap exist (`deepagents` dependency and `create_deep_agent(...)` initialization in runtime agent scaffold).

- [x] Complete (existing scaffold) - `/api/agents/run` is wired through router/service/factory to the DeepAgent runtime wrapper and returns a `graph_state` envelope.
