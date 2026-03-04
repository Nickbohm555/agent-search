- [x] P0 - Add backend streaming run endpoint `POST /api/agents/run/stream` that returns SSE (`text/event-stream`) with ordered scaffold events for a single run.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/streaming-agent-heartbeat.md`): add backend smoke test that posts a deterministic query and verifies response media type is SSE; verifies at least 3 streamed events arrive before close (not only one final payload); verifies strictly increasing `sequence`; verifies event set includes `heartbeat`, `sub_queries`, and `completed`; verifies `completed.data` contains non-empty `agent_name`, non-empty `output`, and non-empty `thread_id`.

- [ ] P0 - Implement runtime compile/invoke path for streaming with per-process cache and deterministic dummy fallback events when runtime stream events are unavailable.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/orchestration-langgraph.md`): add backend tests that verify runtime compile/init happens once per process across consecutive stream calls (no per-request recompile); verifies run path calls DeepAgent runtime `astream` and/or `ainvoke`; verifies fallback mode emits deterministic ordered heartbeat/progress/sub-query/completed events without requiring logging state payloads.

- [ ] P0 - Keep synchronous `/api/agents/run` contract stable and enforce parity between sync result and stream completion payload for deterministic inputs.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/orchestration-langgraph.md`): add backend contract test that existing sync response fields stay present (`sub_queries`, `tool_assignments`, `retrieval_results`, `validation_results`, `output`, `graph_state`, `thread_id`, optional `checkpoint_id`); add parity test that stream `completed.data` matches sync final values (`output`, `sub_queries`, `tool_assignments`, `thread_id` semantics) for the same deterministic query.

- [ ] P1 - Add frontend streaming client in `src/frontend/src/utils/` plus TypeScript stream event types in `src/frontend/src/lib/` for deterministic parsing.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/demo-ui-typescript.md`): add frontend unit tests for supported stream events (`heartbeat`, `sub_queries`, optional progress payloads, `completed`); malformed event payload or invalid event ordering returns deterministic non-crashing error result; interrupted stream maps to retryable user-facing error.

- [ ] P1 - Switch UI run flow to consume stream updates so progress is visible before completion.
  Verification requirements (from `specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`): add frontend interaction test that submitted query remains visible while running; progress status updates during stream; sub-queries render before final completion; final answer renders only after `completed`; stream error leaves query context and shows deterministic error state.

- [x] Complete (scope baseline) - Synchronous scaffold run path exists at `POST /api/agents/run` with deterministic response shape used by current UI/tests.

- [x] Complete (scope guard) - Logging/tracing state streaming is explicitly out of scope for this slice (`specs/compile-invoke-streaming-dummy.md`).
