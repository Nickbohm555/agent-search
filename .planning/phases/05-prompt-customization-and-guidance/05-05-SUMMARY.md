---
phase: "05"
plan: "05-05"
subsystem: "sdk-prompt-precedence-and-default-isolation"
tags:
  - backend
  - sdk
  - pytest
  - prompt-customization
requires:
  - PRM-01
  - PRM-02
provides:
  - PRM-03
affects:
  - src/backend/agent_search/public_api.py
  - sdk/core/src/agent_search/public_api.py
  - src/backend/tests/sdk/test_public_api.py
  - src/backend/tests/sdk/test_public_api_async.py
tech-stack:
  added: []
  patterns:
    - "Public API entrypoints build an effective custom-prompts map by applying reusable config defaults before per-run runtime overrides."
    - "Both backend and core SDK copy caller-owned prompt mappings at merge boundaries so one run cannot mutate another run's defaults."
    - "Sync and async regression tests lock identical precedence behavior and mutable-default isolation across the two public API paths."
key-files:
  created:
    - .planning/phases/05-prompt-customization-and-guidance/05-05-SUMMARY.md
  modified:
    - src/backend/agent_search/public_api.py
    - sdk/core/src/agent_search/public_api.py
    - src/backend/tests/sdk/test_public_api.py
    - src/backend/tests/sdk/test_public_api_async.py
key-decisions:
  - "Keep prompt precedence inside the existing function-based API surface instead of introducing a new SDK client abstraction in Phase 5."
  - "Merge prompt values in one deterministic order: built-in defaults, reusable config-level custom prompts, then per-run runtime overrides."
  - "Use focused regression tests that mutate request payload objects during execution to prove default prompt maps are isolated across runs."
duration: "00:03:24"
completed: "2026-03-13"
---
# Phase 5 Plan 05: Prompt Customization and Guidance Summary

SDK and backend public APIs now resolve prompt defaults and per-run overrides in the same deterministic order without leaking mutable custom prompt state between runs.

## Outcome

Plan `05-05` completed the public API merge-plumbing layer for prompt customization. The backend and core SDK entrypoints now derive one effective `custom_prompts` payload by combining reusable config-level defaults with per-run runtime overrides, then pass only the resolved values into the runtime request model. This keeps `thread_id` behavior unchanged while ensuring sync and async flows honor the same precedence order and do not share mutable prompt maps across calls.

## Commit Traceability

- `05-05-task1` (`90ec99f`): updated backend and core SDK public API merge logic so `custom_prompts` defaults and per-run overrides resolve deterministically and are copied defensively at request boundaries.
- `05-05-task2` (`d47f642`): added focused sync and async regressions covering override precedence and cross-run mutable-default isolation.

## Verification

- `docker compose exec backend uv run pytest tests/sdk/test_public_api.py tests/sdk/test_public_api_async.py` -> passed (`32 passed`).

## Success Criteria Check

- SDK consumers can set reusable prompt defaults through the `custom_prompts` map without state leaking across runs.
- Per-run prompt overrides deterministically win over reusable defaults in both sync and async public API flows.
- Prompt precedence behavior is locked by focused regressions at the merge-plumbing layer.

## Deviations

- The plan executed as written; verification used container-relative test paths (`tests/...`) because the backend container root is `/app`.
