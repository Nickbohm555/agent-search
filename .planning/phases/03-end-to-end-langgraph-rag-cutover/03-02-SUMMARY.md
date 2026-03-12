---
phase: 03-end-to-end-langgraph-rag-cutover
plan: 02
subsystem: runtime
tags: [langgraph, rag, cutover, runtime, async, sdk]
requires:
  - 03-01-SUMMARY.md
provides:
  - production sync runtime execution through the compiled LangGraph gateway
  - production async job execution through the same compiled LangGraph path
  - regression coverage blocking default fallback to legacy orchestration
affects: [runtime, async-jobs, sdk-tests, phase-03]
tech-stack:
  added: []
  patterns:
    - single runtime graph execution entrypoint shared by sync and async flows
    - legacy orchestration retained only behind checkpointed compatibility boundaries
    - contract-preserving cutover tests with monkeypatch guards against fallback drift
key-files:
  created: []
  modified:
    - src/backend/agent_search/runtime/runner.py
    - src/backend/agent_search/runtime/jobs.py
    - src/backend/tests/sdk/test_sdk_run_e2e.py
    - src/backend/tests/sdk/test_sdk_async_e2e.py
    - .planning/STATE.md
    - IMPLEMENTATION_PLAN.md
key-decisions:
  - "Sync production runs now call execute_runtime_graph directly from the runtime runner."
  - "Async jobs use the same compiled graph execution path instead of the legacy imperative runner."
  - "Legacy orchestration remains only where checkpoint compatibility still depends on it, not in the default production path."
patterns-established:
  - "SDK-level sync and async tests assert runtime path selection rather than exact model text."
  - "Cutover verification treats legacy runner invocation as a regression."
duration: 6m 04s
completed: 2026-03-12
---

# Phase 03 Plan 02: End-to-End LangGraph RAG Cutover Summary

**Production sync and async query execution now route through the compiled LangGraph runtime path, with regression coverage preventing silent fallback to the legacy orchestrator.**

## Performance

- **Duration:** 6m 04s
- **Started:** 2026-03-12T22:42:54Z
- **Completed:** 2026-03-12T22:48:58Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Replaced the default sync runtime path in `runner.py` so `run_runtime_agent` executes the compiled graph entrypoint while preserving tracing hooks and response contract mapping.
- Cut async job execution over to the same runtime graph path, keeping job status, cancellation, resume behavior, and thread identity continuity compatible with existing consumers.
- Added SDK sync and async regression tests that fail immediately if the mainline runtime falls back to `run_parallel_graph_runner`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace sync runtime runner delegation with compiled graph execution** - `dd3b574`
2. **Task 2: Cut over async jobs to shared compiled graph runtime path** - `1b5516a`
3. **Task 3: Add cutover regressions that fail on legacy orchestration usage** - `9270c94`

## Files Created/Modified

- `src/backend/agent_search/runtime/runner.py` - Switched the primary sync runtime path to `execute_runtime_graph` while preserving durable execution helpers and response shaping.
- `src/backend/agent_search/runtime/jobs.py` - Routed async jobs through the compiled graph execution path and kept status snapshots aligned with existing API expectations.
- `src/backend/tests/sdk/test_sdk_run_e2e.py` - Added sync runtime cutover assertions and guards that fail on legacy runner use.
- `src/backend/tests/sdk/test_sdk_async_e2e.py` - Added async cutover, cancellation, and resume regression coverage that enforces stable thread and orchestration behavior.

## Decisions Made

- Kept the checkpointed compatibility path separate from the new production runtime path so durable resume behavior can evolve without reintroducing legacy orchestration into normal runs.
- Verified path selection at the SDK boundary, where regressions would matter most to consumers, instead of relying only on lower-level unit assertions.
- Preserved existing request and response payload shapes during cutover so Phase 3 can proceed to contract validation instead of forcing API consumers to adapt.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None.

## User Setup Required

Backend refresh and targeted docker-compose pytest verification were part of task execution; no additional manual setup is required for this summary artifact.

## Phase Readiness

- Phase 3 now has the production runtime path cut over to compiled LangGraph execution for both sync and async flows.
- The next plan can focus on full lifecycle contract validation and anti-regression coverage for the cutover path.

---
*Phase: 03-end-to-end-langgraph-rag-cutover*
*Completed: 2026-03-12*
