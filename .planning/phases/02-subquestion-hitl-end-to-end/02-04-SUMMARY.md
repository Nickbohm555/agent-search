---
phase: "02"
plan: "02-04"
subsystem: "subquestion-hitl-runtime-checkpointing"
tags:
  - backend
  - runtime
  - hitl
  - sse
  - async
requires:
  - "02-01"
provides:
  - SQH-02
  - SQH-03
  - SQH-04
  - SQH-05
affects:
  - src/backend/agent_search/runtime/graph/builder.py
  - src/backend/agent_search/runtime/graph/routes.py
  - src/backend/agent_search/runtime/graph/state.py
  - src/backend/agent_search/runtime/jobs.py
  - src/backend/agent_search/runtime/lifecycle_events.py
  - src/backend/agent_search/runtime/resume.py
  - src/backend/agent_search/runtime/runner.py
  - src/backend/tests/api/test_run_events_stream.py
  - src/backend/tests/services/test_agent_service.py
tech-stack:
  added: []
  patterns:
    - "Single checkpoint gate after decompose and before downstream lane fan-out for HITL-enabled runs"
    - "Shared typed resume path that applies approve/edit/deny/skip decisions using checkpoint-aware payloads"
    - "SSE regression coverage for paused lifecycle metadata, deterministic resume behavior, and non-HITL pass-through"
key-files:
  created:
    - .planning/phases/02-subquestion-hitl-end-to-end/02-04-SUMMARY.md
  modified:
    - src/backend/agent_search/runtime/graph/builder.py
    - src/backend/agent_search/runtime/graph/routes.py
    - src/backend/agent_search/runtime/graph/state.py
    - src/backend/agent_search/runtime/jobs.py
    - src/backend/agent_search/runtime/lifecycle_events.py
    - src/backend/agent_search/runtime/resume.py
    - src/backend/agent_search/runtime/runner.py
    - src/backend/tests/api/test_run_events_stream.py
    - src/backend/tests/services/test_agent_service.py
key-decisions:
  - "Pause subquestion HITL exactly once at `subquestions_ready` so review happens before expand/search/rerank fan-out."
  - "Persist and emit `checkpoint_id` plus `interrupt_payload` so frontend and SDK clients can resume against a stable checkpoint contract."
  - "Keep non-HITL runs on the legacy execution path so omitted or disabled controls preserve baseline behavior."
duration: "00:09:16"
completed: "2026-03-13"
---
# Phase 2 Plan 04: Subquestion HITL End-to-End Summary

Runtime checkpoint wiring for subquestion HITL is implemented with deterministic resume decisions and paused SSE metadata.

## Outcome

Plan `02-04` completed the runtime execution slice for subquestion HITL. HITL-enabled runs now enter a checkpoint-capable path that pauses once after decomposition, resumes from typed approve/edit/deny/skip decisions, and emits paused lifecycle payloads with checkpoint metadata and proposed subquestions. Non-HITL runs continue through the prior execution path unchanged.

## Commit Traceability

- `02-04-task1` (`d6a6735`): inserted the decompose-to-fanout checkpoint gate and aligned initial HITL execution with checkpoint-aware runtime flow across the graph builder, routes, runner, and job orchestration.
- `02-04-task2` (`6bd8d56`): routed initial pause and resume through shared typed decision handling, persisted checkpoint metadata, and applied deterministic resume transformations in the runtime lifecycle stack.
- `02-04-task3` (`5e6713a`): expanded SSE and lifecycle regressions to lock paused payload shape, decision-driven resume behavior, and the no-pause non-HITL path.

## Verification

- `docker compose exec backend uv run pytest src/backend/tests/api/test_run_events_stream.py` -> failed because `/app` does not contain the `src/backend/tests/...` path referenced in the plan.
- `docker compose exec backend uv run pytest tests/api/test_run_events_stream.py` -> `13 passed`.

## Success Criteria Check

- HITL-enabled initial runs pause after decompose and before downstream lane fan-out.
- Approve, edit, deny, and skip decisions deterministically control the subquestions that continue on resume.
- Paused lifecycle and SSE payloads expose `checkpoint_id` and `interrupt_payload` for downstream clients.
- Disabled or omitted HITL controls preserve the prior non-paused runtime behavior.

## Deviations

- Summary-time verification used `tests/api/test_run_events_stream.py` because the plan's `src/backend/tests/api/test_run_events_stream.py` path does not exist inside the backend container.
