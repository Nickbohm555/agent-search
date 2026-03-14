---
phase: "03"
plan: "03-01"
subsystem: "query-expansion-hitl-contracts"
tags:
  - backend
  - api
  - sdk
  - hitl
  - compatibility
requires: []
provides:
  - QEH-01
affects:
  - src/backend/agent_search/public_api.py
  - src/backend/schemas/__init__.py
  - src/backend/schemas/agent.py
  - src/backend/tests/api/test_agent_run.py
  - sdk/core/src/schemas/__init__.py
  - sdk/core/src/schemas/agent.py
tech-stack:
  added: []
  patterns:
    - "Additive query-expansion HITL request controls that stay default-off when omitted"
    - "Typed resume envelopes for checkpoint-bound approve, edit, deny, and skip query-expansion decisions"
    - "Backend API regressions that lock additive async-start and resume compatibility at the request boundary"
key-files:
  created:
    - .planning/phases/03-query-expansion-hitl-end-to-end/03-01-SUMMARY.md
  modified:
    - src/backend/agent_search/public_api.py
    - src/backend/schemas/__init__.py
    - src/backend/schemas/agent.py
    - src/backend/tests/api/test_agent_run.py
    - sdk/core/src/schemas/__init__.py
    - sdk/core/src/schemas/agent.py
key-decisions:
  - "Keep query-expansion HITL fields additive and optional so non-HITL callers preserve existing async behavior without sending new config."
  - "Use typed resume envelopes keyed by `checkpoint_id` for query-expansion decisions instead of raw dict parsing."
  - "Mirror schema exports in backend and SDK packages in the same plan to avoid contract drift before runtime checkpoint work begins."
duration: "00:02:14"
completed: "2026-03-13"
---
# Phase 3 Plan 01: Query Expansion HITL End-to-End Summary

Additive backend and SDK contracts for query-expansion HITL async start and typed resume decisions are in place without changing default non-HITL behavior.

## Outcome

Plan `03-01` completed the contract layer for query-expansion HITL. Async run requests now accept optional query-expansion HITL controls, backend and SDK schemas expose typed checkpoint decision envelopes for approve/edit/deny/skip flows, and API boundary coverage locks additive compatibility so legacy non-HITL requests still validate and execute unchanged when the new fields are omitted.

## Commit Traceability

- `03-01-task1` (`86341ca`): added backend and SDK query-expansion HITL request/resume schemas, exported the new schema types, and updated public API mapping so typed query-expansion HITL data flows through the async and resume entry points.
- `03-01-task2` (`0de32eb`): expanded API regressions in `test_agent_run.py` to cover additive query-expansion HITL request acceptance, typed resume-envelope handling, and unchanged legacy async/resume behavior.

## Verification

- `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "query_expansion or run_async or resume"` -> failed because `/app` in the backend container does not contain `src/backend/tests/api/test_agent_run.py`.
- `docker compose exec backend uv run pytest tests/api/test_agent_run.py -k "query_expansion or run_async or resume"` -> `21 passed, 10 deselected`.

## Success Criteria Check

- Async run and resume contracts accept additive query-expansion HITL fields with typed checkpoint decision payloads.
- Backend and SDK schema surfaces stay aligned for the new query-expansion HITL contract types.
- Omitted HITL controls preserve the prior non-HITL default behavior at the API boundary.

## Deviations

- Summary-time verification used `tests/api/test_agent_run.py` because the plan's `src/backend/tests/api/test_agent_run.py` path does not exist inside the running backend container.
