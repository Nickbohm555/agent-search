- [ ] P0 - Add backend streaming run endpoint `POST /api/agents/run/stream` (SSE) that emits deterministic scaffold events before final completion.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/streaming-agent-heartbeat.md`): backend smoke test verifies response is `text/event-stream`; client receives multiple ordered events during execution (not only one blocking final payload); stream includes heartbeat/progress + `sub_queries` before `completed`; `sequence` is strictly increasing; `completed.data` contains non-empty `agent_name`, non-empty `output`, non-empty `thread_id`.

- [ ] P0 - Wire compile/invoke runtime path to DeepAgent entrypoints (`_get_or_create_agent`, `astream` and/or `ainvoke`) with per-process cached initialization.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/orchestration-langgraph.md`): backend unit/smoke test verifies runtime compile/init is reused across consecutive runs (no per-request recompile), and run execution calls `astream` and/or `ainvoke`; if DeepAgent stream output is unavailable in scaffold mode, deterministic dummy events still produce valid completion payloads.

- [ ] P0 - Extract a shared run engine used by both `/api/agents/run` and `/api/agents/run/stream` so final outputs stay contract-consistent.
  Verification requirements (from `specs/orchestration-langgraph.md` + compile/stream scope): backend smoke test verifies `/api/agents/run` preserves current response fields (`sub_queries`, `tool_assignments`, `retrieval_results`, `validation_results`, `output`, `graph_state`, `thread_id`), and streaming `completed` payload for the same deterministic query matches the non-stream final outcome fields.

- [ ] P1 - Finalize stream event contract in backend schema and frontend parser/types for stable TypeScript consumption.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md`, `specs/streaming-agent-heartbeat.md`): backend and frontend tests verify accepted events include `heartbeat`, `sub_queries`, `tool_assignments` (if emitted), `retrieval_result`/`validation_result` (if emitted), and `completed`; malformed event name/payload/order is rejected deterministically with a surfaced error state.

- [ ] P1 - Implement frontend streaming run flow that updates progress incrementally and finalizes answer on `completed`.
  Verification requirements (from `specs/demo-ui-typescript.md`, `specs/streaming-agent-heartbeat.md`): frontend interaction test verifies progress status updates while stream is active, sub-queries render before completion, final answer renders only after `completed`, and interrupted/invalid stream shows clear actionable error text.

- [x] Complete - Synchronous runtime endpoint `/api/agents/run` already exists and returns decomposition/tool/retrieval/validation/output plus timeline-backed `graph_state`.

- [x] Complete - UI scaffolding for query input, progress readouts, and final answer display already exists in `src/frontend/src/lib/*` and `App.tsx`.

- [x] Scope guard - Exclude logging-state/tracing-state streaming work in this slice ("do not care about logging states").
