---
status: pending
phase: 02-durable-execution-and-identity-semantics
source:
  - 02-01-SUMMARY.md
  - 02-02-SUMMARY.md
  - 02-03-SUMMARY.md
started: 2026-03-12T00:00:00Z
updated: 2026-03-12T00:00:00Z
---

## Current Test

- number: 1
- name: Thread identity continuity across sync and async lifecycle
- expected: A single canonical `thread_id` is visible and stable from run start through status polling and resume-oriented paths.
- awaiting: user execution

## Information Needed from the Summary

- what_changed:
  - Durable execution storage primitives were added for run registry, checkpoint linkage, and idempotency effects.
  - Postgres checkpointer bootstrap and graph compile helpers were added with guarded one-time setup.
  - Thread identity became a public, canonical API and SDK contract with validation and propagation.
  - Resume/replay paths were wired to checkpointed thread lineage with strict pause/resume transition validation.
  - A durable idempotency ledger was integrated to prevent duplicate side effects on replay/retry.
- files_changed:
  - src/backend/alembic/versions/008_add_runtime_execution_durability_tables.py
  - src/backend/models.py
  - src/backend/agent_search/runtime/persistence.py
  - src/backend/agent_search/runtime/execution_identity.py
  - src/backend/agent_search/runtime/resume.py
  - src/backend/services/idempotency_service.py
  - src/backend/agent_search/runtime/runner.py
  - src/backend/agent_search/runtime/jobs.py
  - src/backend/agent_search/public_api.py
  - src/backend/routers/agent.py
  - src/backend/schemas/agent.py
  - src/backend/tests/api/test_agent_run.py
  - src/backend/tests/sdk/test_public_api_async.py
  - src/backend/tests/sdk/test_sdk_async_e2e.py
  - src/backend/tests/services/test_agent_service.py
- code_areas:
  - Runtime durability schema and ORM model layer.
  - LangGraph Postgres checkpointer bootstrap and compile-time persistence wiring.
  - Thread identity validation, minting, and immutable run-thread binding.
  - API/SDK request and response schemas for `thread_id`.
  - Async job lifecycle storage and status continuity.
  - Checkpoint-backed resume and HITL continuation helpers.
  - Idempotency ledger effect recording and replay dedupe checks.
  - API/runtime transition guardrails for pause/resume state changes.
- testing_notes:
  - One prior ad hoc container test rerun reported `Failed to spawn: pytest`; treat these as UAT execution tasks rather than already-verified reruns.
  - Validate behavior by observable API/SDK outcomes and status payloads, not implementation internals.
  - Confirm deterministic failures for invalid `thread_id` input and invalid resume transitions.

## Tests

1. Sync run returns canonical thread identity and preserves caller-provided thread UUID
   - expected: When a valid `thread_id` is provided, sync run response returns the same `thread_id`; when omitted, response includes a server-generated UUID.
   - result: [pending]

2. Async run start/status maintain one thread lineage per run
   - expected: Async start response includes `thread_id`, and repeated status polling for the same run returns the identical `thread_id`.
   - result: [pending]

3. Invalid thread identity is rejected deterministically
   - expected: Invalid `thread_id` input is rejected at API/SDK boundary with deterministic error shape, without creating valid run lineage state.
   - result: [pending]

4. Resume path reuses checkpointed thread identity
   - expected: Resume of an interrupted/checkpointed run continues on the existing `thread_id` rather than minting a new thread lineage.
   - result: [pending]

5. Replay/retry side effects are deduplicated by durable idempotency ledger
   - expected: Replaying the same effect identity within the same thread lineage reuses recorded outcome and does not duplicate external side effects.
   - result: [pending]

6. Valid HITL pause/resume transitions succeed and invalid transitions fail safely
   - expected: Allowed pause/resume transitions complete with consistent state progression; invalid transitions return deterministic errors and leave persisted state unchanged.
   - result: [pending]

7. API and SDK surfaces expose consistent thread_id contract
   - expected: HTTP responses and SDK payloads expose `thread_id` consistently across sync, async start, async status, and resume-related flows.
   - result: [pending]

## Summary

- total: 7
- passed: 0
- issues: 0
- pending: 7
- skipped: 0

## Gaps

[]
