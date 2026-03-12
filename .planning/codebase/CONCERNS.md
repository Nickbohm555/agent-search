# Codebase Concerns

**Analysis Date:** 2026-03-12

## Tech Debt

**Duplicated runtime implementation across backend and SDK core:**
- Issue: Core runtime/service logic is duplicated in two trees, creating drift risk whenever behavior changes in one place but not the other.
- Files: `src/backend/services/agent_service.py`, `sdk/core/src/services/agent_service.py`, `src/backend/services/vector_store_service.py`, `sdk/core/src/services/vector_store_service.py`, `src/backend/services/internal_data_service.py`, `sdk/core/src/services/internal_data_service.py`
- Impact: Inconsistent runtime behavior, difficult bugfix propagation, and migration complexity when refactoring the pipeline.
- Fix approach: Consolidate shared runtime logic into one importable package path and keep only thin adapters in backend/router layers.

**Environment and dependency surface is mixed strict/loose:**
- Issue: Some critical dependencies are pinned while LangChain/OpenAI integrations use broad ranges.
- Files: `src/backend/pyproject.toml`
- Impact: Upstream breaking changes can alter behavior without code changes, especially in callback/tracing and model wrappers.
- Fix approach: Pin integration libraries to tested ranges and maintain an explicit upgrade window with compatibility tests.

## Known Bugs

**All-sources load log reports incorrect chunk count:**
- Symptoms: Logging for all-source wiki load reports `len(chunked_documents)` after loop completion, which reflects only the final source chunk count.
- Files: `src/backend/services/internal_data_service.py`
- Trigger: Call `/api/internal-data/load` with `source_id=all`.
- Workaround: None at runtime; rely on `chunks_created` response field instead of the log line.

**CORS credentials configuration is invalid for wildcard origin use:**
- Symptoms: `allow_origins=["*"]` with `allow_credentials=True` is an unsafe/invalid browser combination for credentialed requests.
- Files: `src/backend/main.py`
- Trigger: Any browser request requiring credentials/cookies.
- Workaround: None in code; use non-credentialed requests only.

## Security Considerations

**No authentication/authorization on destructive or expensive endpoints:**
- Risk: Any caller with network access can trigger data wipe, async job creation/cancellation, and model-backed workloads.
- Files: `src/backend/routers/internal_data.py`, `src/backend/routers/agent.py`
- Current mitigation: Not detected in API router layer.
- Recommendations: Add auth middleware/dependency checks, role-gate `/api/internal-data/wipe`, and require scoped API keys for run endpoints.

**Default credentials and exposed infra ports in local orchestration:**
- Risk: Predictable DB credentials and open host ports increase accidental exposure risk in shared/dev environments.
- Files: `docker-compose.yml`, `.env.example`, `src/backend/db.py`
- Current mitigation: Environment-variable overrides exist.
- Recommendations: Remove weak defaults, require explicit secrets for startup, and restrict bind addresses/ports by profile.

**Browser automation service exposes empty token:**
- Risk: Debug Chrome container is configured with `TOKEN: ""`, reducing protection if port exposure is reachable.
- Files: `docker-compose.yml`
- Current mitigation: None detected in compose file.
- Recommendations: Require non-empty token in non-local profiles and isolate service behind a local-only network.

## Performance Bottlenecks

**Repeated DB engine construction for vector collection existence checks:**
- Problem: `_collection_exists` creates/disposes a SQLAlchemy engine per call.
- Files: `src/backend/services/vector_store_service.py`
- Cause: Engine lifecycle is managed inside each check instead of reusing process-level engine/pool.
- Improvement path: Reuse a shared engine/session factory and cache collection existence with invalidation on writes/migrations.

**Nested threadpool usage for timeout guards adds overhead:**
- Problem: `_run_with_timeout` creates a fresh single-worker executor per guarded operation.
- Files: `src/backend/services/agent_service.py`
- Cause: Frequent executor creation in per-subquestion stages.
- Improvement path: Replace per-call executors with shared worker pools or cooperative async timeout controls.

**In-memory async job registries grow without lifecycle pruning:**
- Problem: Job status maps only grow; no TTL or bounded retention for completed/failed jobs.
- Files: `src/backend/services/internal_data_jobs.py`, `src/backend/agent_search/runtime/jobs.py`
- Cause: `_JOBS` and related maps are append-only for process lifetime.
- Improvement path: Add retention policy, periodic cleanup, and external persistence if long-lived visibility is required.

## Fragile Areas

**Fallback-heavy behavior silently changes output quality when API keys are missing:**
- Files: `src/backend/services/query_expansion_service.py`, `src/backend/services/reranker_service.py`, `src/backend/services/initial_answer_service.py`, `src/backend/services/refinement_decomposition_service.py`, `src/backend/services/subanswer_service.py`
- Why fragile: Pipeline quietly downgrades to fallback logic, which can mask degraded retrieval/answer quality in production-like runs.
- Safe modification: Add explicit capability state in API responses and metrics when fallback paths are active.
- Test coverage: Timeout/fallback paths are tested, but no end-to-end SLO guard for quality regression under fallback mode.

**Broad exception handling suppresses root-cause specificity across runtime/tracing:**
- Files: `src/backend/utils/langfuse_tracing.py`, `src/backend/services/agent_service.py`, `src/backend/agent_search/public_api.py`, `src/backend/agent_search/runtime/jobs.py`
- Why fragile: Catch-all `except Exception` blocks can convert heterogeneous failures into generic outcomes.
- Safe modification: Narrow exception scopes by subsystem and propagate typed error context through API contracts.
- Test coverage: Error mapping tests exist, but not comprehensive for all external SDK/client failure classes.

## Scaling Limits

**Single-process in-memory job orchestration limits horizontal scale:**
- Current capacity: Async state lives in process memory with fixed executors (`max_workers=2` and `max_workers=4`).
- Limit: Multiple backend replicas cannot share job state; restarts lose active/queued state.
- Scaling path: Move job queue/state to shared infrastructure (Redis/Postgres queue) and external worker processes.

**Development server mode enabled in container command path:**
- Current capacity: Backend starts with `uvicorn ... --reload` in compose command.
- Limit: Reload watcher overhead and process behavior are unsuitable for production-like reliability/performance testing.
- Scaling path: Split dev/prod commands, disable reload in default service profile, and add worker tuning for deployment profile.

## Dependencies at Risk

**LangChain ecosystem version drift risk:**
- Risk: Multiple `langchain*` packages are used with broad constraints, increasing compatibility volatility.
- Impact: Runtime node contracts and callback plumbing can break after dependency refresh.
- Migration plan: Pin tested matrix in `src/backend/pyproject.toml` and add lockstep upgrade tests for graph runner and tracing paths.

**PGVector table-name coupling in wipe helper:**
- Risk: Raw SQL wipe assumes specific table names from current vectorstore implementation.
- Impact: Upstream naming/schema changes can break wipe or cause partial cleanup.
- Migration plan: Introspect existing tables before TRUNCATE and centralize vectorstore schema contract checks.

## Missing Critical Features

**Access control and abuse protection for API surface:**
- Problem: API endpoints are unauthenticated and unthrottled.
- Blocks: Safe deployment to multi-user/internal networks; controlled operation of wipe and model-expensive endpoints.

**Deep health/readiness checks for operability:**
- Problem: Health endpoint returns static `"ok"` without checking DB/vectorstore/model dependencies.
- Blocks: Reliable orchestration decisions and fast incident triage.

## Test Coverage Gaps

**Security controls are not exercised because controls are absent:**
- What's not tested: Authentication/authorization, endpoint-level permissions, and rate limiting behavior.
- Files: `src/backend/routers/internal_data.py`, `src/backend/routers/agent.py`, `src/backend/tests/api/test_internal_data_wipe.py`
- Risk: Security regressions remain undetected as API surface expands.
- Priority: High

**Operational resilience under high concurrency is untested:**
- What's not tested: Queue saturation, job retention cleanup behavior, and memory growth from long-running async workloads.
- Files: `src/backend/services/internal_data_jobs.py`, `src/backend/agent_search/runtime/jobs.py`
- Risk: Runtime instability appears only under load or prolonged uptime.
- Priority: High

**Migration safety verification is thin for rollback/compatibility scenarios:**
- What's not tested: End-to-end migration/downgrade safety and compatibility across generated client artifacts.
- Files: `src/backend/alembic/versions/001_add_internal_documents_tables.py`, `scripts/export_openapi.py`, `openapi.json`, `sdk/python/openapi_client`
- Risk: Schema/API drift causes deploy-time breakage or client/runtime mismatch.
- Priority: Medium

---

*Concerns audit: 2026-03-12*
