- [ ] P0 - Implement backend streaming endpoint `POST /api/agents/run/stream` (SSE) that emits ordered scaffold events for one run.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/streaming-agent-heartbeat.md`): backend smoke test verifies `content-type: text/event-stream`; stream yields multiple events before connection close (not a single final blob); events are ordered by monotonically increasing `sequence`; stream includes at least `heartbeat`, `sub_queries`, and `completed`; `completed.data` includes non-empty `agent_name`, non-empty `output`, and non-empty `thread_id`.

- [ ] P0 - Wire compile/invoke path to DeepAgent runtime entrypoints with per-process cache, plus deterministic dummy fallback when runtime streaming is unavailable.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/orchestration-langgraph.md`): backend unit/smoke tests verify compile/init is cached across consecutive calls in one process (no per-request recompile); run path invokes `astream` and/or `ainvoke`; when runtime stream events are absent in scaffold mode, deterministic fallback events still produce valid ordered stream and `completed` payload.

- [ ] P0 - Unify final payload assembly so streaming `completed` contract matches synchronous `/api/agents/run` outcome for deterministic inputs.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/orchestration-langgraph.md`): backend contract test verifies `/api/agents/run` response shape remains intact (`sub_queries`, `tool_assignments`, `retrieval_results`, `validation_results`, `output`, `graph_state`, `thread_id`, optional `checkpoint_id`); parity test verifies streaming `completed.data` matches synchronous final fields for the same deterministic query.

- [ ] P1 - Add frontend SSE client + TypeScript stream event models for stable parsing and deterministic error states.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/demo-ui-typescript.md`): frontend unit tests verify parsing/typing for supported events (`heartbeat`, `sub_queries`, optional progress events, `completed`); malformed payload or invalid event order returns deterministic non-crashing error state; stream interruption maps to retryable user-facing error.

- [ ] P1 - Switch UI run flow to streaming heartbeat updates so users see progress before final answer.
  Verification requirements (from `specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`): frontend interaction test verifies progress region updates while run is active, sub-queries render before completion, final answer appears only after `completed`, and error states remain visible without clearing submitted query context.

- [x] Complete (scope baseline) - `POST /api/agents/run` synchronous scaffold path exists and returns deterministic runtime output + graph timeline.

- [x] Complete (scope guard) - Logging/tracing state streaming is excluded for this slice (explicitly out of scope in `specs/compile-invoke-streaming-dummy.md`).
