# Compile + Invoke with Streaming (Dummy-First) — Spec

**JTBD:** When I run the agent during scaffold phase, I need agent compile/invoke and observable streaming progress so I can validate end-to-end behavior before real event wiring.

**Scope (one sentence, no "and"):** The backend exposes a deterministic streaming run path that compiles/invokes the agent and emits dummy heartbeat/progress events.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers scaffold-phase compile/invoke + streaming delivery using deterministic dummy event data. It does not define production event instrumentation, Langfuse/logging state emission, or non-streaming UI design.
</scope>

<requirements>
## Requirements

### Compile + invoke
- Runtime path compiles/initializes DeepAgent once per process lifecycle (or equivalent cached runtime).
- Run execution invokes the compiled runtime through `astream` and/or `ainvoke` entrypoints.
- If runtime stream output is unavailable in scaffold mode, deterministic dummy events may be emitted as fallback while preserving response contract.

### Streaming heartbeat
- Backend provides a streaming endpoint for agent runs (SSE or equivalent) that pushes ordered progress events.
- At minimum, stream includes heartbeat/progress, sub-queries, and completion with final answer payload.
- Event payloads use a stable schema suitable for TypeScript UI consumption.

### Codex's Discretion
- Exact transport (SSE vs WebSocket), event granularity, and fallback strategy.
- Whether completion payload duplicates non-streaming `/api/agents/run` response fields.
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- A client can call the streaming run endpoint and receive ordered events for a typical run without waiting for one final blocking response.
- Stream includes enough data for UI to render sub-queries and progress before completion.
- Compile/invoke path exercises DeepAgent runtime entrypoints (`astream` and/or `ainvoke`) for the run path.
- Scaffold mode works deterministically with dummy streaming data and does not require logging state emission.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Production tracing/logging payloads and state logging.
- Detailed retrieval/validation/synthesis behavior.
- MCP exposure.
</boundaries>

---
*Topic: compile-invoke-streaming-dummy*
*Spec created: 2026-03-04*
*Relates to: orchestration-langgraph, streaming-agent-heartbeat, demo-ui-typescript*
---
