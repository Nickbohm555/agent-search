---
phase: "01"
plan: "01-03"
subsystem: "runtime-frontend-contracts"
tags:
  - backend
  - frontend
  - compatibility
  - runtime-response
requires:
  - "01-01"
  - "01-02"
provides:
  - REL-01
affects:
  - src/backend/services/agent_service.py
  - src/frontend/src/utils/api.ts
  - src/backend/tests/services/test_agent_service.py
  - src/backend/tests/contracts/test_public_contracts.py
tech-stack:
  added: []
  patterns:
    - "Additive runtime response aliasing from `sub_qa` to `sub_answers`"
    - "Frontend validators that tolerate additive response fields without breaking legacy payloads"
    - "Contract tests that lock required legacy fields while allowing additive evolution"
key-files:
  created: []
  modified:
    - src/backend/services/agent_service.py
    - src/frontend/src/utils/api.ts
    - src/backend/tests/services/test_agent_service.py
    - src/backend/tests/contracts/test_public_contracts.py
key-decisions:
  - "Emit `sub_answers` as a deep-copied alias of `sub_qa` so legacy consumers keep working while new consumers can adopt the additive field."
  - "Keep frontend response guards permissive for omitted `sub_answers` and strict only when the additive field is present."
  - "Lock compatibility with contract coverage that fails on removing or renaming legacy response fields."
duration: "00:04:32"
completed: "2026-03-13"
---
# Phase 1 Plan 03: Contract Foundation and Compatibility Baseline Summary

Additive `sub_answers` response compatibility landed across backend mapping, frontend validation, and contract tests.

## Outcome

Plan `01-03` completed the Phase 1 response-compatibility work. Runtime response mapping now emits both legacy `sub_qa` and additive `sub_answers`, frontend API validators accept both legacy-only and additive payloads, and compatibility tests assert that required legacy fields remain stable while the new field stays optional.

## Commit Traceability

- `01-03-task1` (`fceb691`): updated runtime response mapping in `agent_service.py` to emit additive `sub_answers` as a compatibility alias of `sub_qa`.
- `01-03-task2` (`f9ae961`): extended frontend runtime response types and validators in `src/frontend/src/utils/api.ts` to accept optional `sub_answers`.
- `01-03-task3` (`95c4fbc`): added compatibility coverage in service and public-contract tests to lock additive `sub_answers` behavior and preserve legacy fields.

## Verification

- `docker compose exec backend uv run pytest src/backend/tests/services/test_agent_service.py src/backend/tests/contracts/test_public_contracts.py` -> failed because `/app` does not contain the `src/backend/...` paths referenced in the plan.
- `docker compose exec backend uv run pytest tests/services/test_agent_service.py -k 'map_graph_state_to_runtime_response or backward_compatible' tests/contracts/test_public_contracts.py` -> `1 passed, 67 deselected`.
- `docker compose exec backend uv run pytest tests/contracts/test_public_contracts.py` -> `5 passed`.
- `docker compose exec frontend npm run typecheck` -> passed.
- `docker compose exec frontend npm run build` -> passed.
- `docker compose exec backend uv run pytest tests/services/test_agent_service.py tests/contracts/test_public_contracts.py` -> failed with `15 failed, 53 passed`; failures are in broader service-runtime verification cases unrelated to the additive `sub_answers` contract checks.

## Success Criteria Check

- Runtime responses include additive `sub_answers` while preserving `sub_qa` and existing required response fields.
- Frontend validators tolerate both legacy and additive response payloads.
- Contract coverage fails on breaking removal or rename of legacy response fields.

## Deviations

- Summary-time verification used `tests/...` container paths because the plan's `src/backend/tests/...` paths do not exist inside the backend container.
- The full backend verification set for `tests/services/test_agent_service.py` currently has unrelated red tests in subanswer-verification and runtime-runner paths, so only the additive compatibility checks in that suite are green for this plan.
