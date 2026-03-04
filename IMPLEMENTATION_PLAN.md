- [ ] P0 - Add backend streaming run endpoint `POST /api/agents/run/stream` using SSE that emits deterministic scaffold events for one run.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/streaming-agent-heartbeat.md`): backend smoke test verifies `content-type` is `text/event-stream`; stream emits multiple ordered events before termination; stream includes at least `heartbeat`, `sub_queries`, and `completed`; `sequence` increases monotonically; `completed.data` includes non-empty `agent_name`, non-empty `output`, and non-empty `thread_id`.

- [ ] P0 - Exercise DeepAgent compile/invoke entrypoints in the scoped run path with per-process runtime caching.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/orchestration-langgraph.md`): backend unit/smoke tests verify the runtime compile/init path is reused across consecutive runs (no per-request recompile), and run execution calls `astream` and/or `ainvoke`; when runtime stream output is absent in scaffold mode, deterministic dummy stream events still produce a valid `completed` payload.

- [ ] P0 - Share final run-output assembly between synchronous `/api/agents/run` and streaming completion payload so contracts stay aligned.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/orchestration-langgraph.md`): backend test verifies existing `/api/agents/run` response contract stays intact (`sub_queries`, `tool_assignments`, `retrieval_results`, `validation_results`, `output`, `graph_state`, `thread_id`); for the same deterministic query, streaming `completed` payload matches the synchronous final outcome fields.

- [ ] P1 - Add frontend streaming client/types for typed SSE consumption and deterministic error handling.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/demo-ui-typescript.md`): frontend unit tests verify supported events parse into stable TS shapes (`heartbeat`, `sub_queries`, optional progress events, `completed`); malformed event payload/order surfaces a deterministic error state; stream interruption produces actionable retryable messaging.

- [ ] P1 - Wire frontend run flow to streaming heartbeat updates with progressive progress rendering and completion finalization.
  Verification requirements (from `specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`): frontend interaction test verifies progress area updates during an active stream, sub-queries appear before completion, final answer renders only after `completed`, and failed stream states remain visible without clearing user query input.

- [x] Complete (scoped baseline) - Synchronous run path `/api/agents/run` exists and returns deterministic scaffold output with timeline/readout fields.

- [x] Complete (scope guard) - Exclude logging/tracing state streaming from this slice (`specs/compile-invoke-streaming-dummy.md` out-of-scope).
