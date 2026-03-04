# Langfuse Tracing Scaffold

This folder contains scaffold-only observability setup for Langfuse.

Current state:
- Environment-based config loading exists.
- Runtime initialization hook exists.
- No Langfuse SDK client/tracer is instantiated yet.

When implementing:
1. Add Langfuse SDK dependency in `pyproject.toml`.
2. Create actual client/tracer in `initialize_langfuse_tracing()`.
3. Instrument request lifecycle and agent/service boundaries.
