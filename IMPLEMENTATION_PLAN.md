# Agent-Search Implementation Plan

Tasks are in **recommended implementation order** (1…n). Each section = **one context window**. Complete one section at a time.

Current section to work on: section 2. (move +1 after each turn)

---

## Section 1: Langfuse instrumentation (send traces)

**Single goal:** Instrument agent-search so that when it runs, it sends traces to Langfuse. This enables the agent-trace harness tracer to fetch and analyze runs.

**Details:**
- Add Langfuse SDK (or LangChain/LangGraph tracing to Langfuse) so coordinator and pipeline runs produce traces (spans, inputs, outputs, errors) in the configured Langfuse project.
- Use existing `.env` / `LANGFUSE_*` (e.g. `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`) from `.env.`; ensure `LANGFUSE_ENABLED=true` when tracing is desired.
- No change to business logic; instrumentation only.

**How to test:** Run a query with Langfuse enabled; assert traces appear in the Langfuse project for the run.

**Test results:**
- Backend tests: `docker compose exec backend sh -lc 'cd /app && uv run --with pytest pytest tests/utils/test_langfuse_tracing.py tests/services/test_agent_service.py tests/api'` -> `22 passed`.
- Langfuse-enabled runtime run executed via backend container (`LANGFUSE_ENABLED=true`) and returned output successfully.
- Langfuse traces verified through Langfuse Public API (`/api/public/traces`) using configured keys/host; latest trace timestamps include `2026-03-06T16:46:53.378Z` and `2026-03-06T16:44:25.649Z`.

---
