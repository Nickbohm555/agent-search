---
phase: "01"
plan: "01-01"
subsystem: "backend-contracts"
tags:
  - fastapi
  - pydantic
  - compatibility
  - runtime-controls
requires: []
provides:
  - CTRL-02
  - CTRL-04
  - CTRL-05
  - REL-01
affects:
  - src/backend/schemas/agent.py
  - src/backend/schemas/__init__.py
  - src/backend/routers/agent.py
  - src/backend/tests/api/test_agent_run.py
tech-stack:
  added: []
  patterns:
    - "Additive Pydantic request controls with compatibility-safe defaults"
    - "Shared router config normalization for sync and async run entrypoints"
    - "Additive response aliasing for backward-compatible contract evolution"
key-files:
  created: []
  modified:
    - src/backend/schemas/agent.py
    - src/backend/schemas/__init__.py
    - src/backend/routers/agent.py
    - src/backend/tests/api/test_agent_run.py
key-decisions:
  - "Keep runtime request evolution additive by nesting optional controls under `controls` instead of replacing legacy fields."
  - "Preserve legacy response consumers by exposing `sub_answers` alongside existing `sub_qa`."
  - "Normalize control forwarding once at the router boundary so `/run` and `/run-async` send the same config shape."
duration: "00:04:23"
completed: "2026-03-13"
---
# Phase 1 Plan 01: Contract Foundation and Compatibility Baseline Summary

Additive runtime controls and `sub_answers` support landed without changing legacy run payload behavior.

## Outcome

Plan `01-01` established the compatibility baseline for later HITL and control-surface work. The backend schema now accepts optional nested per-run controls, the router forwards a single normalized config shape for sync and async runs, and API responses expose additive `sub_answers` while preserving `sub_qa`, `output`, and citation fields.

## Commit Traceability

- `01-01-task1` (`7625993`): added additive request control models, exported schema types, and additive `sub_answers` response fields while keeping legacy request/response compatibility intact.
- `01-01-task2` (`9417379`): replaced thread-only config mapping with one additive router mapper shared by `/run` and `/run-async`.
- `01-01-task3` (`ea8d45b`): extended router tests to enforce legacy validity, additive control forwarding, and additive `sub_answers` coverage.

## Verification

- `docker compose exec backend uv run pytest tests/api/test_agent_run.py` -> `18 passed`
- `docker compose exec backend uv run pytest tests/contracts/test_public_contracts.py` -> `3 passed`

## Success Criteria Check

- Legacy clients can omit new fields and still submit runs successfully.
- Additive control fields are accepted and forwarded into normalized runtime config.
- Response models include additive `sub_answers` without removing or renaming required legacy fields.

## Deviations

- No implementation deviations from the plan.
- Summary-time verification used `tests/api/test_agent_run.py` and `tests/contracts/test_public_contracts.py` because the plan's `src/backend/tests/...` paths do not exist inside the backend container.
