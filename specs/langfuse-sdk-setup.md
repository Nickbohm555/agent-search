# Langfuse SDK Setup — Spec

**JTBD:** Add Langfuse tracing to the agent-search application so that all agent runs are traced.
**Scope (one sentence, no "and"):** The application initializes the Langfuse SDK from environment configuration so tracing can be used at runtime.
**Status:** Ready

<scope>
## Topic Boundary

This spec covers: loading Langfuse configuration from environment variables, instantiating the Langfuse client/tracer at application startup, and exposing a handle (e.g. on app state) so other code can create traces and spans. It does not cover where or how agent runs are instrumented (agent run tracing spec) or what data is sent per trace (covered there).
</scope>

<requirements>
## Requirements

### Configuration
- Configuration is loaded from environment (existing vars: `LANGFUSE_ENABLED`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `LANGFUSE_ENVIRONMENT`, `LANGFUSE_RELEASE`).
- When `LANGFUSE_ENABLED` is false or credentials are missing, the app runs without a real client (no-op / disabled handle) so the app does not depend on Langfuse to start.

### Initialization
- On FastAPI startup, the app initializes the Langfuse SDK when enabled and stores a usable handle (e.g. client or tracer) on `app.state.langfuse` (or equivalent) for the rest of the process.
- The handle exposes a way for instrumented code to create traces/spans (e.g. get client, start observation). Exact API is implementation detail.

### Dependency
- Langfuse Python SDK is added as a dependency (e.g. in `pyproject.toml`); version is implementation choice.

### Claude's Discretion
- Whether to use Langfuse native client vs OpenTelemetry bridge.
- Exact shape of the handle (e.g. wrapper type, async vs sync).
- Logging or metrics when tracing is disabled vs enabled.
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- When `LANGFUSE_ENABLED=true` and valid `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set, the application starts and a Langfuse client (or equivalent) is available on app state for creating observations.
- When `LANGFUSE_ENABLED=false` or credentials are not set, the application starts without error and code that uses the handle does not emit traces (graceful no-op).
- A request that triggers tracing (e.g. an agent run) can create a trace/span using the initialized handle without runtime errors when tracing is enabled.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Instrumenting each agent run and what data is sent (query, agent name, output) → agent-run-tracing.md
- Langfuse UI usage, dashboards, or alerting (product use, not this app’s scope).
</boundaries>

---
*Topic: langfuse-sdk-setup*
*Spec created: 2025-03-03*
