# Langfuse Tracing Scaffold

This folder contains scaffold-only observability setup for Langfuse.

Current state:
- Environment-based config loading exists.
- Runtime initialization hook exists.
- Langfuse client initialization occurs when enabled and credentials are present.
- Disabled or misconfigured environments get a safe no-op tracing handle.

When implementing:
1. Instrument request lifecycle and agent/service boundaries.
2. Add per-run trace payloads for agent execution paths.
