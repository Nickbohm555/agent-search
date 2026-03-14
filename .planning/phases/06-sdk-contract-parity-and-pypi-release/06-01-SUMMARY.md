---
phase: "06"
plan: "06-01"
subsystem: "sdk-contract-parity-and-generated-artifacts"
tags:
  - backend
  - sdk
  - openapi
  - release
  - pytest
requires:
  - REL-03
provides:
  - REL-03
affects:
  - src/backend/schemas/agent.py
  - src/backend/routers/agent.py
  - src/backend/agent_search/config.py
  - sdk/core/src/schemas/agent.py
  - sdk/core/src/agent_search/config.py
  - openapi.json
  - sdk/python/openapi_client/models/runtime_agent_run_request.py
  - sdk/python/openapi_client/models/runtime_agent_run_response.py
  - src/backend/tests/api/test_agent_run.py
  - src/backend/tests/sdk/test_runtime_config.py
tech-stack:
  added: []
  patterns:
    - "Backend request and response schemas remain the contract source of truth, with sdk/core mirrors preserving the same additive aliases and default-safe behavior."
    - "OpenAPI export and generated sdk/python models are refreshed atomically through the repository regeneration scripts instead of hand-editing generated artifacts."
    - "Release-blocking parity regressions cover request acceptance, omitted-field defaults, additive response serialization, and OpenAPI drift validation."
key-files:
  created:
    - .planning/phases/06-sdk-contract-parity-and-pypi-release/06-01-SUMMARY.md
  modified:
    - src/backend/schemas/agent.py
    - src/backend/routers/agent.py
    - src/backend/agent_search/config.py
    - sdk/core/src/schemas/agent.py
    - sdk/core/src/agent_search/config.py
    - openapi.json
    - sdk/python/openapi_client/models/runtime_agent_run_request.py
    - sdk/python/openapi_client/models/runtime_agent_run_response.py
    - src/backend/tests/api/test_agent_run.py
    - src/backend/tests/sdk/test_runtime_config.py
key-decisions:
  - "Keep `runtime_config`, `custom_prompts`, and additive `sub_answers` aligned across backend schemas, sdk/core models, and generated HTTP SDK artifacts rather than introducing a separate release-only contract layer."
  - "Preserve compatibility by accepting additive request controls with default-off behavior and by serializing `sub_answers` alongside legacy `sub_qa`."
  - "Treat OpenAPI drift validation as a release-blocking parity gate for this plan."
duration: "00:05:02"
completed: "2026-03-13"
---
# Phase 6 Plan 01: SDK Contract Parity and PyPI Release Summary

Backend schemas, committed OpenAPI, sdk/core models, and generated HTTP SDK artifacts now expose the same additive HITL, runtime control, custom prompt, and `sub_answers` contract surface ahead of release.

## Outcome

Plan `06-01` completed the REL-03 parity gate for external consumers. The backend contract models and sdk/core mirrors now accept the same request shapes for nested HITL controls, `runtime_config`, and `custom_prompts`, while response models keep legacy `sub_qa` intact and expose additive `sub_answers`. The committed `openapi.json` and generated `sdk/python` artifacts were then refreshed from the backend schema source of truth, and targeted regressions were added so request acceptance, omitted-field defaults, additive response serialization, and drift validation remain release-blocking.

## Commit Traceability

- `06-01-task1` (`fed95f1`): updated backend and sdk/core schema/config surfaces for canonical runtime controls, prompt options, HITL compatibility, and additive `sub_answers` support.
- `06-01-task2` (`3e2b563`): regenerated `openapi.json` and the generated HTTP SDK models/tests so the committed artifacts match the backend-exported contract.
- `06-01-task3` (`37891d7`): added parity regressions in API and runtime-config tests to lock additive request defaults, field acceptance, response serialization, and release drift expectations.

## Verification

- `docker compose exec backend uv run pytest tests/api/test_agent_run.py tests/sdk/test_runtime_config.py` -> passed (`52 passed`).
- `./scripts/validate_openapi.sh` -> passed.

## Success Criteria Check

- SDK/OpenAPI models now include HITL controls, runtime controls, prompt options, and additive `sub_answers` in parity with backend contracts.
- Generated HTTP SDK artifacts are refreshed from committed OpenAPI and validated against runtime-exported schema output.
- Release-blocking regressions protect default-safe compatibility and additive response behavior before PyPI publication work begins.

## Deviations

- The plan executed as written; verification used container-relative test paths (`tests/...`) because the backend container root is `/app`.
- Summary duration was inferred from the task commit window because `$DURATION` and `$PLAN_END_TIME` were not populated in the shell environment.
