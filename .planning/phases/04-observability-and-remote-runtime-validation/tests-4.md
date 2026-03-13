---
status: pending
phase: 04-observability-and-remote-runtime-validation
source:
  - 04-01-SUMMARY.md
  - 04-02-SUMMARY.md
  - 04-03-SUMMARY.md
started: 2026-03-12T00:00:00Z
updated: 2026-03-12T00:00:00Z
---

## Current Test

- number: 1
- name: Run events stream shows ordered lifecycle progression
- expected: A started run emits ordered lifecycle stages and reaches a terminal event without missing transitions.
- awaiting: user execution

## Information Needed from the Summary

- what_changed:
  - Canonical lifecycle event contract is emitted from runtime signals and exposed through SSE with reconnect safety.
  - Correlation metadata is standardized so runtime events, tracing spans, and terminal outcomes share one tuple.
  - Remote validation scripts and probes now provide reproducible evidence in Docker Compose and fresh pip-installed SDK environments.
  - A validation matrix persists PASS or FAIL outcomes with artifact links and correlation evidence for REL-05 acceptance.
- files_changed:
  - src/backend/agent_search/runtime/lifecycle_events.py
  - src/backend/agent_search/runtime/graph/execution.py
  - src/backend/agent_search/runtime/runner.py
  - src/backend/agent_search/runtime/jobs.py
  - src/backend/routers/agent.py
  - src/backend/utils/langfuse_tracing.py
  - src/backend/tests/runtime/test_lifecycle_events.py
  - src/backend/tests/runtime/test_trace_correlation.py
  - src/backend/tests/api/test_run_events_stream.py
  - src/backend/tests/api/test_trace_metadata_contract.py
  - scripts/validation/phase4_remote_compose.sh
  - scripts/validation/phase4_remote_sdk.sh
  - scripts/validation/phase4_remote_compose_probe.py
  - scripts/validation/phase4_remote_sdk_probe.py
  - scripts/validation/phase4_seed_vector_store.py
  - scripts/validation/phase4_collect_artifacts.py
  - .planning/phases/04-observability-and-remote-runtime-validation/04-VALIDATION-MATRIX.md
- code_areas:
  - Runtime lifecycle event normalization and monotonic event ID generation.
  - SSE run-events route behavior including Last-Event-ID resume.
  - Trace correlation metadata builder and terminal success/failure observations.
  - Remote validation workflow scripts, probes, and artifact collection.
  - Phase evidence matrix for cross-environment acceptance.
- testing_notes:
  - Validate observable outcomes through API responses and streamed events rather than internal implementation details.
  - Confirm both happy-path and failure-path correlation tuple consistency.
  - Confirm each remote environment run produces concrete artifact files and matrix references.
  - Treat missing artifact links or absent correlation IDs as failures.

## Tests

1. **Lifecycle stream shows full ordered timeline for a successful run**
   - Expected: Starting a run and listening to run-events yields monotonic event IDs, ordered stage progression, and a terminal completion event.
   - Result: [pending]

2. **SSE reconnect resumes from Last-Event-ID without duplicates**
   - Expected: Reconnecting with Last-Event-ID continues from the next event only, with no replay gaps or duplicate lifecycle entries.
   - Result: [pending]

3. **Every streamed lifecycle event contains run/thread/trace correlation tuple**
   - Expected: Each streamed event payload includes non-empty `run_id`, `thread_id`, and `trace_id` values for end-to-end correlation.
   - Result: [pending]

4. **Run status and stream payloads remain correlation-consistent**
   - Expected: The async run status response for a given run uses the same `run_id`/`thread_id`/`trace_id` tuple observed in streamed lifecycle events.
   - Result: [pending]

5. **Failure-path run preserves correlation and terminal metadata**
   - Expected: An intentionally failing run still emits a terminal event and status payload with the same correlation tuple and final stage/status metadata.
   - Result: [pending]

6. **Compose remote validation script produces passing probe evidence**
   - Expected: Running the Compose validation workflow completes successfully, proves lifecycle visibility, and records run/thread/trace identifiers.
   - Result: [pending]

7. **Fresh pip SDK remote validation script produces passing probe evidence**
   - Expected: Running the fresh SDK validation workflow completes successfully, proves lifecycle visibility, and records run/thread/trace identifiers.
   - Result: [pending]

8. **Validation artifacts include terminal status and event counts**
   - Expected: Collected artifacts for both environments include terminal outcome and event count evidence tied to each run tuple.
   - Result: [pending]

9. **Validation matrix records PASS for both required environments**
   - Expected: The phase validation matrix shows PASS rows for Docker Compose and fresh pip SDK targets with concrete evidence references.
   - Result: [pending]

10. **REL-05 acceptance evidence is reproducible from repository scripts**
    - Expected: A user can re-run documented scripts and regenerate equivalent proof artifacts without manual-only validation steps.
    - Result: [pending]

## Summary

- total: 10
- passed: 0
- issues: 0
- pending: 10
- skipped: 0

## Gaps

[]
