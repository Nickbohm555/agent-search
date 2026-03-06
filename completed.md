# Section 1: Langfuse instrumentation (send traces)

**Single goal:** Instrument agent-search so that when it runs, it sends traces to Langfuse. This enables the agent-trace harness tracer to fetch and analyze runs.

**Details implemented:**
- Added `langfuse>=3.0.0` to backend dependencies and regenerated `src/backend/uv.lock`.
- Added `src/backend/utils/langfuse_tracing.py`:
  - `build_langfuse_callback_handler()` gated by `LANGFUSE_ENABLED`.
  - Reads `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and host from `LANGFUSE_BASE_URL` fallback `LANGFUSE_HOST`.
  - Initializes Langfuse client and LangChain callback handler with SDK-signature-compatible kwargs.
  - Logs enabled/disabled/misconfiguration states.
  - Best-effort flush helper for callback/client.
- Reused existing callback architecture in `src/backend/services/agent_service.py`:
  - Adds Langfuse callback to existing callback list when enabled.
  - Logs callback configuration.
  - Flushes Langfuse callback/client after coordinator invoke.
- Added backend tests in `src/backend/tests/utils/test_langfuse_tracing.py`.

**Useful logs and validation outputs:**
- Rebuild/restart:
  - `docker compose down && docker compose build && docker compose up -d`
  - Backend startup logs include uvicorn + alembic startup with no runtime errors.
- Backend health:
  - `curl -i http://localhost:8000/api/health` -> `HTTP/1.1 200 OK` with `{"status":"ok"}`.
- Tests:
  - `docker compose exec backend sh -lc 'cd /app && uv run --with pytest pytest tests/utils/test_langfuse_tracing.py tests/services/test_agent_service.py tests/api'`
  - Result: `22 passed`.
- Langfuse-enabled run:
  - Executed `run_runtime_agent` in backend container with `LANGFUSE_ENABLED=true`.
  - Output summary: `RUN_OK True`.
- Langfuse trace verification:
  - `GET https://us.cloud.langfuse.com/api/public/traces?limit=10` with configured keys returned `200`.
  - Latest traces include:
    - `2026-03-06T16:46:53.378Z` trace `192a697a1a2dcbf21ac6af212b7bf73c`
    - `2026-03-06T16:44:25.649Z` trace `3451be79178fa1683f083587722b9793`
