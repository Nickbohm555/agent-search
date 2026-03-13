---
phase: "01"
plan: "01-02"
subsystem: "backend-sdk-runtime"
tags:
  - sdk
  - runtime-controls
  - async-jobs
  - compatibility
requires:
  - "01-01"
provides:
  - CTRL-02
  - CTRL-04
  - CTRL-05
affects:
  - src/backend/agent_search/public_api.py
  - src/backend/agent_search/runtime/jobs.py
  - src/backend/tests/sdk/test_public_api.py
  - src/backend/tests/sdk/test_public_api_async.py
  - src/backend/tests/sdk/test_runtime_config.py
tech-stack:
  added: []
  patterns:
    - "Shared SDK request-to-runtime config normalization for sync and async entrypoints"
    - "Persisted normalized async request payload for resume-safe control continuity"
    - "Regression tests that lock omitted-control defaults and explicit HITL enablement"
key-files:
  created: []
  modified:
    - src/backend/agent_search/config.py
    - src/backend/agent_search/public_api.py
    - src/backend/agent_search/runtime/jobs.py
    - src/backend/tests/sdk/test_public_api.py
    - src/backend/tests/sdk/test_public_api_async.py
key-decisions:
  - "Build runtime request payloads from normalized `RuntimeConfig` state so sync and async SDK entrypoints forward the same additive control contract."
  - "Persist the normalized request payload in async job metadata and rebuild resume requests from it instead of query/thread-only fallbacks."
  - "Keep HITL default-off unless explicitly enabled, and assert omitted controls serialize to the preexisting baseline payload shape."
duration: "00:06:02"
completed: "2026-03-13"
---
# Phase 1 Plan 02: Contract Foundation and Compatibility Baseline Summary

SDK runtime control propagation and async resume continuity landed without changing omitted-field defaults.

## Outcome

Plan `01-02` threaded additive per-run controls through the backend SDK/public API layer and the async job lifecycle. Sync `advanced_rag` and async `run_async` now derive the same normalized runtime request payload, persisted async jobs retain the full control envelope across pause/resume, and regression coverage locks the default-off compatibility behavior for omitted fields and HITL.

## Commit Traceability

- `01-02-task1` (`16a33cf`): normalized SDK/public API control mapping so `thread_id`, `rerank`, `query_expansion`, and `hitl` are reflected in runtime request payloads with compatibility-safe defaults.
- `01-02-task2` (`ca7147c`): persisted normalized async request payloads in runtime jobs and rebuilt resume requests from stored payload state.
- `01-02-task3` (`84c9742`): added sync and async regression tests for explicit control propagation, omitted-control defaults, and default-off HITL behavior.

## Verification

- `docker compose exec backend uv run pytest tests/sdk/test_public_api.py tests/sdk/test_public_api_async.py` -> `23 passed`
- `docker compose exec backend uv run pytest tests/sdk/test_runtime_config.py` -> `3 passed`

## Success Criteria Check

- Control fields are reflected in runtime config processing for sync and async runs.
- Resume reconstructs full request controls rather than query/thread-only payload.
- Default behavior for legacy requests remains unchanged when controls are omitted.

## Deviations

- Summary-time verification used `tests/sdk/...` inside the backend container because the plan's `src/backend/tests/...` paths do not exist at `/app`.
