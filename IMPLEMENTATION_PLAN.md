- [ ] P0 - Add backend streaming run endpoint (`POST /api/agents/run/stream`) using SSE and deterministic dummy event data first.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md` + `specs/streaming-agent-heartbeat.md`): backend smoke test verifies a client receives ordered events during a run (not one final blocking payload), includes `sub_queries` + progress before completion, event `sequence` values are strictly increasing, and `completed` includes non-empty `thread_id` + final `output`.

- [ ] P0 - Refactor runtime execution into a shared run engine that supports incremental emission for streaming while preserving the current `/api/agents/run` response contract.
  Verification requirements (from `specs/orchestration-langgraph.md` response acceptance): backend smoke test verifies `/api/agents/run` still returns the existing fields (`sub_queries`, `tool_assignments`, `retrieval_results`, `validation_results`, `output`, `graph_state`), and streaming completion payload is consistent with the same query's final run outcome.

- [ ] P0 - Wire true compile/invoke usage of DeepAgent runtime entrypoints (`_get_or_create_agent`, `astream` and/or `ainvoke`) in the run path with deterministic fallback behavior in scaffold mode.
  Verification requirements (from `specs/compile-invoke-streaming-dummy.md` + `specs/orchestration-langgraph.md`): backend test verifies DeepAgent runtime is initialized once (cached compile/init) and invocation entrypoint(s) are called per run; fallback path remains deterministic and still satisfies run/stream contracts.

- [ ] P1 - Implement frontend streaming consumption for heartbeat progress and sub-queries using the new stream endpoint.
  Verification requirements (from `specs/demo-ui-typescript.md` + `specs/streaming-agent-heartbeat.md`): frontend render/interaction test verifies sub-queries/progress appear incrementally before completion, final answer appears on `completed`, and interrupted/malformed stream transitions to a clear error state.

- [ ] P1 - Finalize shared stream event typing/validation across backend schema and frontend parser.
  Verification requirements (from `specs/streaming-agent-heartbeat.md`): backend + frontend tests verify valid stream events are accepted, malformed event shapes are rejected deterministically, and event type coverage includes at least heartbeat/progress/sub-queries/completed.

- [x] Complete (already present) - Synchronous runtime run path exists at `/api/agents/run` and returns timeline-backed `graph_state` plus final output payload.

- [x] Complete (already present) - UI scaffolding exists for query submission and readouts (`ProgressHistory`, status banners, final answer panel) after run completion.

- [x] Scope guard - Exclude logging-state work for this slice (user explicitly does not care about logging states).
