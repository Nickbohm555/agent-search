- [x] P0 - Add backend streaming run endpoint `POST /api/agents/run/stream` that returns SSE (`text/event-stream`) with ordered scaffold events for a single run.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/streaming-agent-heartbeat.md`): add backend smoke test that posts a deterministic query and verifies response media type is SSE; verifies at least 3 streamed events arrive before close (not only one final payload); verifies strictly increasing `sequence`; verifies event set includes `heartbeat`, `sub_queries`, and `completed`; verifies `completed.data` contains non-empty `agent_name`, non-empty `output`, and non-empty `thread_id`.

- [x] P0 - Implement runtime compile/invoke path for streaming with per-process cache and deterministic dummy fallback events when runtime stream events are unavailable.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/orchestration-langgraph.md`): add backend tests that verify runtime compile/init happens once per process across consecutive stream calls (no per-request recompile); verifies run path calls DeepAgent runtime `astream` and/or `ainvoke`; verifies fallback mode emits deterministic ordered heartbeat/progress/sub-query/completed events without requiring logging state payloads.
  Completed in this run:
  - Added process-cached stream runtime compile path in `src/backend/services/agent_service.py` (`_get_or_compile_stream_runtime`) with deterministic scaffold adapter that exposes `astream` + `ainvoke`.
  - Updated stream run flow to call runtime `astream` first and always call runtime `ainvoke` for completion payload parity, emitting fallback `progress` + `sub_queries` + `completed` when runtime events are unavailable.
  - Added smoke tests in `src/backend/tests/api/test_streaming_compile_invoke_dummy.py` covering compile-once across consecutive stream calls and runtime `astream`/`ainvoke` invocation with deterministic fallback event ordering.

- [x] P0 - Keep synchronous `/api/agents/run` contract stable and enforce parity between sync result and stream completion payload for deterministic inputs.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/orchestration-langgraph.md`): add backend contract test that existing sync response fields stay present (`sub_queries`, `tool_assignments`, `retrieval_results`, `validation_results`, `output`, `graph_state`, `thread_id`, optional `checkpoint_id`); add parity test that stream `completed.data` matches sync final values (`output`, `sub_queries`, `tool_assignments`, `thread_id` semantics) for the same deterministic query.
  Completed in this run:
  - Added `src/backend/tests/api/test_sync_stream_contract_parity.py::test_runtime_agent_run_contract_stays_stable` to lock required sync response fields and non-empty output/thread semantics.
  - Added `src/backend/tests/api/test_sync_stream_contract_parity.py::test_runtime_agent_stream_completed_payload_matches_sync_final_values` to verify stream `completed.data` parity with sync run values (`output`, `sub_queries`, `tool_assignments`, `thread_id`) for one deterministic payload with explicit `thread_id`.
  - Verified required checks pass: health endpoint, backend tests, frontend tests, and frontend typecheck.

- [x] P1 - Add frontend streaming client in `src/frontend/src/utils/` plus TypeScript stream event types in `src/frontend/src/lib/` for deterministic parsing.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/demo-ui-typescript.md`): add frontend unit tests for supported stream events (`heartbeat`, `sub_queries`, optional progress payloads, `completed`); malformed event payload or invalid event ordering returns deterministic non-crashing error result; interrupted stream maps to retryable user-facing error.
  Completed in this run:
  - Added stream event types and validators in `src/frontend/src/lib/stream-events.ts` for deterministic parsing of `heartbeat`, `progress`, `sub_queries`, and `completed` payloads plus supported passthrough event names.
  - Added streaming client `streamAgentRun` in `src/frontend/src/utils/stream.ts` that POSTs to `/api/agents/run/stream`, parses SSE `data:` frames, validates strict sequence ordering, enforces heartbeat-first and `sub_queries`-before-`completed`, and maps malformed/interrupted states to deterministic error results.
  - Added `src/frontend/src/utils/stream.test.ts` unit coverage for supported ordered events, malformed payload handling, invalid ordering handling, and interrupted stream retryable error mapping.
  - Verified required checks pass: health endpoint, backend tests, frontend tests, and frontend typecheck.

- [x] P1 - Switch UI run flow to consume stream updates so progress is visible before completion.
  Verification requirements (from `specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`): add frontend interaction test that submitted query remains visible while running; progress status updates during stream; sub-queries render before final completion; final answer renders only after `completed`; stream error leaves query context and shows deterministic error state.
  Completed in this run:
  - Switched UI run execution in `src/frontend/src/App.tsx` from sync `runAgent` calls to streamed `streamAgentRun` consumption with `onEvent` updates for `heartbeat`, `progress`, and `sub_queries`.
  - Added dedicated streamed state (`streamedProgress`, `streamedSubQueries`) and wired `ProgressHistory` to render in-flight stream data before completion while preserving deterministic empty states.
  - Ensured final answer is rendered only after stream completion payload is returned; query readout is set at submit and preserved on stream failure.
  - Added/updated frontend interaction tests in `src/frontend/src/App.test.tsx` covering: in-flight query context visibility, progress/sub-query rendering before completion, final answer gating to completion, stream error handling, and in-flight duplicate submission prevention.
  - Verified required checks pass for this loop: health endpoint, backend tests, frontend tests, and frontend typecheck.

- [x] Complete (scope baseline) - Synchronous scaffold run path exists at `POST /api/agents/run` with deterministic response shape used by current UI/tests.

- [x] Complete (scope guard) - Logging/tracing state streaming is explicitly out of scope for this slice (`specs/compile-invoke-streaming-dummy.md`).
