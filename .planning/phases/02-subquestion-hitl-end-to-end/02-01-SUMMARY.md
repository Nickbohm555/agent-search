---
phase: "02"
plan: "02-01"
subsystem: "subquestion-hitl-contracts"
tags:
  - backend
  - api
  - hitl
  - compatibility
requires: []
provides:
  - SQH-01
affects:
  - src/backend/agent_search/config.py
  - src/backend/agent_search/public_api.py
  - src/backend/schemas/__init__.py
  - src/backend/schemas/agent.py
  - src/backend/tests/api/test_agent_run.py
tech-stack:
  added: []
  patterns:
    - "Additive subquestion HITL request controls that remain default-off when omitted"
    - "Typed resume envelopes for approve, edit, deny, and skip decisions with stable validation"
    - "API regression coverage for additive async-start and resume payload compatibility"
key-files:
  created:
    - .planning/phases/02-subquestion-hitl-end-to-end/02-01-SUMMARY.md
  modified:
    - src/backend/agent_search/config.py
    - src/backend/agent_search/public_api.py
    - src/backend/schemas/__init__.py
    - src/backend/schemas/agent.py
    - src/backend/tests/api/test_agent_run.py
key-decisions:
  - "Treat `hitl.subquestions.enabled=true` as implicitly enabling parent HITL so additive nested config maps cleanly onto runtime defaults."
  - "Accept `resume=True` and legacy object payloads alongside typed subquestion decision envelopes to preserve backward compatibility."
  - "Reject malformed typed envelopes at the API boundary with deterministic Pydantic validation errors instead of ad hoc runtime parsing."
duration: "00:06:00"
completed: "2026-03-13"
---
# Phase 2 Plan 01: Subquestion HITL End-to-End Summary

Additive backend contracts for subquestion HITL async start and typed resume decisions are in place without changing default non-HITL behavior.

## Outcome

Plan `02-01` completed the contract layer for subquestion HITL. Async run requests now accept optional nested `hitl.subquestions.enabled` controls, runtime config normalization preserves default-off behavior when HITL is omitted, and resume requests now accept typed envelopes carrying `checkpoint_id` plus per-subquestion `approve`, `edit`, `deny`, or `skip` decisions while still allowing legacy `resume=True` and object payloads.

## Commit Traceability

- `02-01-task1` (`561ec9a`): added `RuntimeSubquestionHitlControl`, typed subquestion decision and resume-envelope schemas, runtime config normalization for `hitl.subquestions`, and public API mapping so nested HITL config is forwarded consistently.
- `02-01-task2` (`23f90a5`): expanded API router regressions to cover additive async HITL controls, typed resume-envelope acceptance, legacy boolean resume compatibility, and explicit validation failures for malformed typed decision payloads.

## Verification

- `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "run_async or resume"` -> failed because `/app` in the backend container does not contain `src/backend/tests/api/test_agent_run.py`.
- `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "hitl or resume or validation"` -> failed for the same path-resolution reason.
- `docker compose exec backend uv run pytest tests/api/test_agent_run.py -k "run_async or resume"` -> `15 passed, 10 deselected`.
- `docker compose exec backend uv run pytest tests/api/test_agent_run.py -k "hitl or resume or validation"` -> `13 passed, 12 deselected`.

## Success Criteria Check

- Async run contracts accept additive subquestion HITL enablement while omitted HITL fields keep the prior default-off path.
- Resume contracts accept typed `checkpoint_id` + decision envelopes and still allow legacy boolean/object resume payloads.
- API tests fail predictably on malformed typed envelopes, locking validation behavior at the request boundary.

## Deviations

- Summary-time verification used `tests/api/test_agent_run.py` because the plan’s `src/backend/tests/api/test_agent_run.py` path does not exist inside the running backend container.
