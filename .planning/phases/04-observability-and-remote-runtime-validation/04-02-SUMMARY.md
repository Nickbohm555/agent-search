---
phase: 04-observability-and-remote-runtime-validation
plan: 02
subsystem: runtime
tags: [observability, tracing, correlation, lifecycle-events, api]
requires:
  - 04-01-SUMMARY.md
provides:
  - canonical run-thread-trace metadata propagation across runtime lifecycle events and tracing spans
  - joinable terminal outcome metadata for successful and failed runs
  - regression coverage for trace metadata parity across runtime and API observability surfaces
affects: [runtime, api, observability, tests, phase-04]
tech-stack:
  added: []
  patterns:
    - one canonical metadata builder supplies run_id, thread_id, trace_id, stage, and status to lifecycle events and tracing spans
    - terminal runtime observations reuse the same correlation tuple as node-level traces instead of emitting ad-hoc metadata
    - API event and status contract tests enforce correlation joinability for both success and failure paths
key-files:
  created:
    - .planning/phases/04-observability-and-remote-runtime-validation/04-02-SUMMARY.md
    - src/backend/tests/runtime/test_trace_correlation.py
    - src/backend/tests/api/test_trace_metadata_contract.py
  modified:
    - src/backend/agent_search/runtime/lifecycle_events.py
    - src/backend/agent_search/runtime/runner.py
    - src/backend/tests/runtime/test_lifecycle_events.py
    - src/backend/utils/langfuse_tracing.py
key-decisions:
  - "Trace metadata is built through one shared helper so lifecycle events and Langfuse observations cannot drift on key names."
  - "Terminal success and error outcomes inherit the final stage plus canonical correlation tuple for direct joins with node spans."
  - "Failure-path observability is treated as a contract and enforced in both runtime and API regression tests."
patterns-established:
  - "Observability changes are accepted only when success and failure paths preserve the same correlation contract."
  - "Joinability between SSE payloads, run-status responses, and trace metadata is proven with automated tests."
duration: 3m 54s
completed: 2026-03-12
---

# Phase 04 Plan 02: Observability and Remote Runtime Validation Summary

**Phase 4 now guarantees one canonical `run_id` / `thread_id` / `trace_id` tuple across lifecycle events, runtime tracing spans, and terminal run outcomes.**

## Performance

- **Duration:** 3m 54s
- **Started:** 2026-03-12T19:24:19-04:00
- **Completed:** 2026-03-12T19:28:13-04:00
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Routed lifecycle event emission through shared trace metadata construction so every emitted event carries the same `run_id`, `thread_id`, `trace_id`, `stage`, and `status` fields.
- Updated runtime tracing to stamp the canonical correlation tuple onto root traces, node spans, score records, and terminal success/error observations.
- Added lifecycle and correlation regressions that prove a single run stays joinable across runtime events, node traces, and terminal outcomes.
- Added API contract coverage showing SSE event payloads and async run-status responses preserve the same correlation tuple on both successful and failed runs.

## Task Commits

Each task was committed atomically:

1. **Task 1: Standardize correlation tuple propagation in runtime + tracing** - `47083dd`
2. **Task 2: Add contract tests for correlation joinability** - `621add6`

## Files Created/Modified

- `src/backend/agent_search/runtime/lifecycle_events.py` - Reused shared trace metadata construction for canonical lifecycle event fields.
- `src/backend/agent_search/runtime/runner.py` - Propagated correlation metadata into runtime traces, stage spans, scores, and terminal success/error observations.
- `src/backend/utils/langfuse_tracing.py` - Added the shared trace metadata helper used by runtime and lifecycle code.
- `src/backend/tests/runtime/test_lifecycle_events.py` - Extended lifecycle coverage to assert one stable correlation tuple across stream and terminal events.
- `src/backend/tests/runtime/test_trace_correlation.py` - Added runtime correlation regression tests for success and failure joinability.
- `src/backend/tests/api/test_trace_metadata_contract.py` - Added API regressions for SSE and async status metadata parity.

## Decisions Made

- Centralized correlation metadata assembly rather than letting lifecycle and tracing code shape their own payloads independently.
- Used the terminal stage from runtime snapshots for final success metadata so outcome traces remain joinable to the last node execution context.
- Required failure scenarios to preserve the exact same correlation tuple contract as successful runs.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None.

## User Setup Required

None beyond the existing Docker Compose backend workflow used for implementation tasks.

## Phase Readiness

- Plan `04-02` is complete: runtime and API observability surfaces now share one deterministic correlation contract.
- Phase 4 can move to remote runtime validation with correlation evidence already locked down by runtime and API regression coverage.

---
*Phase: 04-observability-and-remote-runtime-validation*
*Completed: 2026-03-12*
