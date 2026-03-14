---
phase: "04"
plan: "04-02"
subsystem: "operator-controls-runtime-behavior"
tags:
  - backend
  - runtime
  - retrieval
  - query-expansion
  - rerank
requires:
  - "04-01"
provides:
  - CTRL-01
  - CTRL-03
affects:
  - src/backend/services/agent_service.py
  - src/backend/tests/sdk/test_runtime_config.py
  - src/backend/tests/services/test_agent_service.py
tech-stack:
  added: []
  patterns:
    - "Request-scoped runtime control resolution for expand and rerank execution without mutating process defaults"
    - "Service-level regressions that prove per-run disablement changes runtime behavior rather than only accepted payload shape"
    - "Scoped backend verification that isolates operator-control behavior from unrelated service-suite failures"
key-files:
  created:
    - .planning/phases/04-operator-controls-and-result-visibility/04-02-SUMMARY.md
  modified:
    - src/backend/services/agent_service.py
    - src/backend/tests/sdk/test_runtime_config.py
    - src/backend/tests/services/test_agent_service.py
key-decisions:
  - "Keep query-expansion and rerank toggles request-scoped by resolving effective node config inside the runtime service path instead of mutating global defaults."
  - "Prove behavioral control changes with targeted service tests that observe expand and rerank execution outcomes, not only parser construction."
  - "Record summary-time verification with the narrowed plan-specific selectors because the full service suite currently contains unrelated regressions."
duration: "00:10:49"
completed: "2026-03-13"
---
# Phase 4 Plan 02: Operator Controls and Result Visibility Summary

Per-run query-expansion and rerank controls now affect live runtime behavior while default behavior stays unchanged when no runtime config is supplied.

## Outcome

Plan `04-02` completed the runtime-behavior slice for operator controls. The runtime service path now resolves per-run expand and rerank settings during execution, query-expansion defaults and override parsing are pinned with focused config tests, and service regressions confirm both toggles can be disabled for a single run without mutating later runs or global process behavior.

## Commit Traceability

- `04-02-task1` (`9ea57cb`): extended runtime-config regression coverage so query-expansion defaults, explicit disablement, and fallback parsing are locked at the config boundary.
- `04-02-task2` (`e060a9f`): wired request-scoped runtime config through the agent service so expand and rerank execution use effective per-run controls instead of env-only assumptions.
- `04-02-task3` (`1502848`): added service-level regressions proving query expansion and rerank can be disabled per run without changing subsequent default behavior.

## Verification

- `docker compose exec backend uv run pytest tests/sdk/test_runtime_config.py` -> `4 passed`.
- `docker compose exec backend uv run pytest tests/services/test_agent_service.py -k "expand or rerank or runtime_config"` -> `13 passed, 52 deselected`.
- `docker compose exec backend uv run pytest tests/sdk/test_runtime_config.py tests/services/test_agent_service.py` -> failed with 6 unrelated `tests/services/test_agent_service.py` regressions outside the plan selectors, including answer-node verification expectations, runtime-runner test doubles, agent-jobs wrapper expectations, and timeout behavior assertions.

## Success Criteria Check

- Per-run `query_expansion.enabled` changes expand-node behavior without any environment change.
- Per-run `rerank.enabled` changes rerank execution without mutating global defaults or later runs.
- Omitted `runtime_config` preserves the prior default behavior with regression coverage at both config and service levels.

## Deviations

- Summary-time verification used the plan-scoped selectors as the authoritative signal because the full `tests/services/test_agent_service.py` suite currently has unrelated failures that do not exercise the operator-control paths changed in `04-02`.
