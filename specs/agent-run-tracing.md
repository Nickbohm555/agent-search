# Agent Run Tracing — Spec

**JTBD:** Add Langfuse tracing to the agent-search application so that all agent runs are traced.
**Scope (one sentence, no "and"):** Every agent run is recorded as a trace (or span) in Langfuse with the run input, agent identity, and output.
**Status:** Ready

<scope>
## Topic Boundary

This spec covers: instrumenting agent execution so that each call to run an agent (e.g. via the `/api/agents/run` flow) produces a trace or span in Langfuse. It includes what is captured (query, agent name, response) and that all such runs are traced when Langfuse is enabled. It does not cover SDK initialization or configuration (langfuse-sdk-setup.md).
</scope>

<requirements>
## Requirements

### Coverage
- Every agent run that goes through the application’s agent execution path (e.g. `run_runtime_agent` / `agent.run(query)`) is traced when Langfuse is enabled. No agent run is silently untraced.

### Captured data
- Each trace (or top-level span) includes: the run input (e.g. query string), agent identity (e.g. agent name), and the run output (e.g. response text). Metadata such as timestamp or duration is at implementer’s discretion (Langfuse often captures this automatically).

### Behavior when tracing is disabled
- When Langfuse is disabled (no client or no-op handle), agent runs execute as today with no tracing and no failure or side effects from tracing code.

### Integration point
- Instrumentation is applied at the boundary where the agent is executed (e.g. agent service or runtime agent wrapper), so all agents created by the factory are traced regardless of concrete agent type (e.g. LangGraph scaffold vs future implementations).

### Claude's Discretion
- Whether each run is a single trace or a span under a request trace; naming of traces/spans; use of decorator vs context manager vs manual observation.
- Level of detail for errors (e.g. recording exceptions in the span).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- When Langfuse is enabled and a client posts a query to the agent run endpoint, a trace (or span) appears in Langfuse for that run with the request query, the agent name, and the response body.
- When Langfuse is disabled, posting to the agent run endpoint returns the same response as today and no trace is created.
- Multiple consecutive agent runs each produce a distinct trace (or span) in Langfuse when tracing is enabled.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Langfuse SDK dependency, config loading, and startup initialization → langfuse-sdk-setup.md
- Tracing of non-agent endpoints (e.g. search, health) or internal LLM/tool calls inside an agent (future scope).
</boundaries>

---
*Topic: agent-run-tracing*
*Spec created: 2025-03-03*
