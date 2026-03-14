---
phase: "05"
plan: "05-01"
subsystem: "backend-sdk-prompt-customization-contracts"
tags:
  - backend
  - sdk
  - fastapi
  - pydantic
  - runtime-config
  - prompt-customization
requires: []
provides:
  - PRM-03
affects:
  - src/backend/schemas/agent.py
  - src/backend/routers/agent.py
  - src/backend/agent_search/config.py
  - sdk/core/src/agent_search/config.py
  - src/backend/tests/api/test_agent_run.py
  - src/backend/tests/sdk/test_runtime_config.py
tech-stack:
  added: []
  patterns:
    - "Additive request contracts that accept both canonical snake_case fields and hyphenated JSON aliases for prompt maps"
    - "Typed RuntimeConfig parsing in backend and SDK that whitelists supported prompt keys and ignores unknown entries safely"
    - "Router-level normalization that forwards custom prompt overrides through the existing runtime_config path for sync and async runs"
key-files:
  created:
    - .planning/phases/05-prompt-customization-and-guidance/05-01-SUMMARY.md
  modified:
    - src/backend/schemas/agent.py
    - src/backend/routers/agent.py
    - src/backend/agent_search/config.py
    - sdk/core/src/agent_search/config.py
    - src/backend/tests/api/test_agent_run.py
    - src/backend/tests/sdk/test_runtime_config.py
key-decisions:
  - "Constrain prompt overrides to explicit `subanswer` and `synthesis` keys instead of exposing a free-form prompt bag."
  - "Keep `custom_prompts` as the canonical internal field while accepting `custom-prompts` as an additive external alias."
  - "Ignore unknown prompt keys rather than rejecting the whole request so legacy and forward-compatible callers keep working."
duration: "00:06:20"
completed: "2026-03-13"
---
# Phase 5 Plan 01: Prompt Customization and Guidance Summary

Prompt override contracts now exist as additive backend and SDK runtime config inputs, with alias-safe request handling and regression coverage for legacy callers.

## Outcome

Plan `05-01` established the contract foundation for prompt customization without changing default advanced RAG behavior. Backend request models now accept `custom_prompts` and `custom-prompts`, normalize them to one internal shape, and pass supported `subanswer` and `synthesis` overrides through router config assembly into runtime config parsing. Matching SDK config support keeps backend and SDK behavior aligned, while focused API and runtime-config regressions lock in alias handling, safe unknown-key omission, and legacy payload compatibility when prompt overrides are absent.

## Commit Traceability

- `05-01-task1` (`a4525c2`): added typed prompt override parsing in backend and SDK runtime config models and expanded contract tests for additive request acceptance.
- `05-01-task2` (`145231b`): updated router config assembly to forward normalized prompt overrides through sync and async run entrypoints without changing `thread_id` behavior.
- `05-01-task3` (`0b6b6ee`): added regression coverage for `custom_prompts` and `custom-prompts`, safe unknown-key handling, and omission compatibility.

## Verification

- `docker compose exec backend uv run pytest src/backend/tests/sdk/test_runtime_config.py src/backend/tests/api/test_agent_run.py` -> passed.

## Success Criteria Check

- Run payloads can carry explicit prompt overrides for subanswer and synthesis without breaking legacy requests.
- Backend and SDK runtime config parsing recognize supported prompt keys and keep omitted-field defaults unchanged.
- API compatibility tests lock in alias handling and additive behavior before follow-on precedence work.

## Deviations

- The plan executed as written.
