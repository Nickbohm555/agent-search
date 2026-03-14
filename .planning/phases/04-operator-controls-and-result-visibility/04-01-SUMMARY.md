---
phase: "04"
plan: "04-01"
subsystem: "operator-controls-runtime-config-contract"
tags:
  - backend
  - api
  - sdk
  - compatibility
  - runtime-config
requires:
  - "01-02"
provides:
  - CTRL-03
affects:
  - src/backend/schemas/agent.py
  - src/backend/routers/agent.py
  - src/backend/agent_search/public_api.py
  - src/backend/tests/api/test_agent_run.py
  - src/backend/tests/sdk/test_public_api.py
  - src/backend/tests/sdk/test_public_api_async.py
tech-stack:
  added: []
  patterns:
    - "Top-level REST `runtime_config` contract that stays optional and additive beside existing run fields"
    - "Router-to-SDK config forwarding that preserves `thread_id` while carrying nested rerank and query-expansion controls"
    - "API and SDK sync/async regressions that lock additive control forwarding without breaking legacy payloads"
key-files:
  created:
    - .planning/phases/04-operator-controls-and-result-visibility/04-01-SUMMARY.md
  modified:
    - src/backend/schemas/agent.py
    - src/backend/routers/agent.py
    - src/backend/agent_search/public_api.py
    - src/backend/tests/api/test_agent_run.py
    - src/backend/tests/sdk/test_public_api.py
    - src/backend/tests/sdk/test_public_api_async.py
key-decisions:
  - "Expose per-run retrieval controls as an optional top-level `runtime_config` request field instead of coupling the contract to frontend-only state."
  - "Keep the SDK public interface on the existing `config` dict shape and merge nested `runtime_config` fields into sync and async normalization logic."
  - "Pin compatibility with focused API and SDK regressions that assert both additive forwarding and unchanged legacy payload behavior."
duration: "00:05:54"
completed: "2026-03-13"
---
# Phase 4 Plan 01: Operator Controls and Result Visibility Summary

Per-run `runtime_config` controls now flow from the API request contract into the SDK sync and async entrypoints with compatibility coverage.

## Outcome

Plan `04-01` completed the contract-plumbing slice for Phase 4 operator controls. The backend request schema now accepts optional nested `runtime_config` input for rerank and query-expansion toggles, the router forwards that payload alongside existing `thread_id` handling, and the SDK sync and async entrypoints normalize nested runtime config without changing their external `config` interface. Focused regressions now lock both additive control forwarding and legacy payload compatibility.

## Commit Traceability

- `04-01-task1` (`6ef9e82`): added the additive `runtime_config` request models and exported the new schema types without changing legacy request validity.
- `04-01-task2` (`66857e9`): forwarded `runtime_config` through the router and SDK normalization path while preserving the existing `config` envelope and `thread_id` behavior.
- `04-01-task3` (`b46d13f`): added API plus SDK sync/async regressions for `runtime_config.rerank.enabled`, `runtime_config.query_expansion.enabled`, and legacy payload pass-through.

## Verification

- `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py src/backend/tests/sdk/test_public_api.py src/backend/tests/sdk/test_public_api_async.py` -> failed because `/app` does not contain the `src/backend/tests/...` paths referenced in the plan.
- `docker compose exec backend uv run pytest tests/api/test_agent_run.py tests/sdk/test_public_api.py tests/sdk/test_public_api_async.py` -> `62 passed`.

## Success Criteria Check

- Run endpoints accept optional per-run retrieval controls without requiring frontend-specific fields.
- SDK sync and async entrypoints accept rerank and query-expansion runtime config while preserving `thread_id` handling.
- Contract-level regressions prove additive forwarding and unchanged legacy behavior when `runtime_config` is omitted.

## Deviations

- Summary-time verification used `tests/...` container paths because the plan's `src/backend/tests/...` paths do not exist inside the backend container.
