Tests are in **required execution order** (1...n). Each section = one atomic verification. Complete one section at a time.
Current section to work on: section 21. (move +1 after each turn)

## Global Test Loading Rules
- Before executing any section, fully load the referenced source test markdown file for that section.
- Also load the phase `*-RESEARCH.md` file and phase `*-CONTEXT.md` file when present, and use them as supporting context.
- Do not assume test intent from this plan alone; this document is a pointer and execution checklist.
- For each section, use the exact source test block and its surrounding context as the source of truth.

## Global Test Recording Rules
- After each completed test, update the matching test block inside the source test markdown with the actual run result.
- Replace any placeholder `result:` value with concise pass/fail status and key observed evidence.
- Update file-level progress/bookkeeping fields when present (for example: `Current Test`, `updated`, `Summary`, `Gaps`).
- Keep this plan's per-section `Test results` notes aligned with what was written back to the source test markdown.

## Global Commit Rules
- Do not create git commits directly while executing these testing sections.
- `.loop-commit-msg` must use numeric IDs only: `{phase:2digits}-{plan:2digits}-test{test-number}` (or `-taskN` / `-summary` where applicable).
- For test sections, derive `plan` from the source test filename `tests-N.md` as zero-padded `0N` (example: `tests-1.md` -> `01`, so Section 1 Test 1 is `01-01-test1`).

## Section 1 — 01-contract-foundation-and-compatibility-baseline — tests-1 — Test 1 (Validation)
- Source test markdown: `.planning/phases/01-contract-foundation-and-compatibility-baseline/tests-1.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 1 (Legacy request compatibility remains intact).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/api/test_agent_run.py::test_runtime_agent_run_request_keeps_legacy_payload_compatible_when_custom_prompts_omitted` passed, and omitted-controls compatibility also passed in sync and async SDK tests `tests/sdk/test_public_api.py::test_advanced_rag_preserves_omitted_controls_and_hitl_default_off` and `tests/sdk/test_public_api_async.py::test_run_async_preserves_omitted_controls_and_hitl_default_off`.

## Section 2 — 01-contract-foundation-and-compatibility-baseline — tests-1 — Test 2 (Validation)
- Source test markdown: `.planning/phases/01-contract-foundation-and-compatibility-baseline/tests-1.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 2 (Additive controls propagate consistently in sync and async flows).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/sdk/test_public_api.py::test_advanced_rag_propagates_explicit_controls_without_mutation tests/sdk/test_public_api.py::test_advanced_rag_propagates_runtime_config_without_breaking_legacy_control_shape tests/sdk/test_public_api_async.py::test_run_async_propagates_explicit_controls_to_job_payload tests/sdk/test_public_api_async.py::test_run_async_propagates_runtime_config_to_job_payload_without_breaking_legacy_control_shape` passed, confirming sync and async entrypoints normalize explicit thread and additive controls into the same payload shapes, including the nested `runtime_config` compatibility path.

## Section 3 — 01-contract-foundation-and-compatibility-baseline — tests-1 — Test 3 (Validation)
- Source test markdown: `.planning/phases/01-contract-foundation-and-compatibility-baseline/tests-1.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 3 (Async resume preserves full normalized controls).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass - `docker compose exec backend uv run pytest tests/sdk/test_public_api_async.py::test_resume_run_reconstructs_full_request_payload` passed on 2026-03-14, confirming paused async jobs resume from the persisted normalized request payload and retain the full controls envelope instead of reverting to query/thread-only reconstruction.

## Section 4 — 01-contract-foundation-and-compatibility-baseline — tests-1 — Test 4 (Validation)
- Source test markdown: `.planning/phases/01-contract-foundation-and-compatibility-baseline/tests-1.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 4 (Response contract stays backward compatible with additive field).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/contracts/test_public_contracts.py::test_runtime_agent_run_response_contract_keeps_legacy_fields_and_additive_sub_answers tests/services/test_agent_service.py::test_map_graph_state_to_runtime_response_is_backward_compatible tests/api/test_agent_run.py::test_runtime_agent_run_response_serializes_additive_sub_answers_alongside_legacy_sub_qa` passed, confirming the schema still honors the legacy `sub_qa` and required `output` contract while backend mapping and API serialization also expose additive `sub_answers`.

## Section 5 — 01-contract-foundation-and-compatibility-baseline — tests-1 — Test 5 (Validation)
- Source test markdown: `.planning/phases/01-contract-foundation-and-compatibility-baseline/tests-1.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 5 (Frontend validation accepts legacy-only and additive payloads).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec frontend npm run test -- src/App.test.tsx -t "shows ordered stage rail and progressive status updates from streamed events|renders subanswers from additive sub_answers payloads during streamed and final updates"` passed, confirming the frontend runtime guards accept both legacy-only `sub_qa` payloads and additive `sub_answers` payloads during streamed and final updates.

Next: update .planning/STATE.md after executing this phase's testing sections.

## Section 6 — 02-subquestion-hitl-end-to-end — tests-2 — Test 1 (Validation)
- Source test markdown: `.planning/phases/02-subquestion-hitl-end-to-end/tests-2.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 1 (Async run accepts additive subquestion HITL control and remains backward compatible).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass - `docker compose exec backend uv run pytest tests/api/test_agent_run.py::test_post_run_async_accepts_subquestion_hitl_controls tests/sdk/test_public_api_async.py::test_run_async_preserves_omitted_controls_and_hitl_default_off tests/sdk/test_sdk_async_e2e.py::test_sdk_async_run_e2e_preserves_default_off_subquestion_hitl_path` passed on 2026-03-14, confirming additive async subquestion HITL acceptance and default-off backward compatibility.

## Section 7 — 02-subquestion-hitl-end-to-end — tests-2 — Test 2 (Validation)
- Source test markdown: `.planning/phases/02-subquestion-hitl-end-to-end/tests-2.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 2 (Paused HITL run exposes reviewable checkpoint metadata to clients).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/api/test_run_events_stream.py::test_checkpoint_enabled_initial_run_pauses_at_subquestions_ready_with_interrupt_payload_and_checkpoint_id` passed, confirming `/api/agents/run-events/{job_id}` emits `run.paused` at `subquestions_ready` with matching `checkpoint_id` and `interrupt_payload`; `docker compose exec frontend npm run test -- --run src/App.test.tsx -t "shows paused subquestion review and resumes to completion with typed decisions"` also passed, confirming the client renders actionable review state from that payload and resumes successfully.

## Section 8 — 02-subquestion-hitl-end-to-end — tests-2 — Test 3 (Validation)
- Source test markdown: `.planning/phases/02-subquestion-hitl-end-to-end/tests-2.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 3 (Resume with approve/edit/deny/skip decisions completes run deterministically).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/api/test_run_events_stream.py::test_subquestion_checkpoint_resume_applies_typed_decisions_deterministically tests/api/test_run_events_stream.py::test_resume_agent_run_job_records_decision_driven_completion_events` passed, confirming the checkpoint node and resume job flow deterministically apply mixed approve/edit/deny/skip decisions so edited text is preserved, denied items are removed, skipped entries keep their original text, and approved entries continue unchanged; `docker compose exec backend uv run pytest tests/sdk/test_sdk_async_e2e.py::test_sdk_async_resume_e2e_supports_typed_subquestion_decision_matrix` also passed, confirming the SDK async resume path completes successfully for each typed decision mode.

## Section 9 — 02-subquestion-hitl-end-to-end — tests-2 — Test 4 (Validation)
- Source test markdown: `.planning/phases/02-subquestion-hitl-end-to-end/tests-2.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 4 (Malformed typed resume envelope fails at API boundary).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/api/test_agent_run.py::test_post_run_resume_rejects_malformed_typed_decision_envelopes` passed, confirming malformed typed resume envelopes fail at the API boundary with deterministic `422` validation errors for missing edit payloads, empty checkpoint IDs or decision lists, invalid decision actions, and mismatched subquestion versus query-expansion decision shapes.

## Section 10 — 02-subquestion-hitl-end-to-end — tests-2 — Test 5 (Validation)
- Source test markdown: `.planning/phases/02-subquestion-hitl-end-to-end/tests-2.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 5 (Frontend paused review UX is actionable and non-HITL flow is unchanged).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec frontend npm run test -- --run src/App.test.tsx -t "shows paused subquestion review and resumes to completion with typed decisions"` and `docker compose exec frontend npm run test -- --run src/App.test.tsx -t "keeps non-HITL runs on the default completion path without review UI or resume calls"` passed, confirming the paused UI exposes actionable approve/edit/deny/skip controls and submits typed resume payloads while non-HITL runs still complete without surfacing review UI or issuing resume requests; `./launch-devtools.sh http://localhost:5173` and `curl http://127.0.0.1:9222/json/list` also confirmed a healthy local Chrome target for `http://localhost:5173/`.

## Section 11 — 02-subquestion-hitl-end-to-end — tests-2 — Test 6 (Validation)
- Source test markdown: `.planning/phases/02-subquestion-hitl-end-to-end/tests-2.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 6 (SDK typed async parity supports new and legacy resume modes).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/sdk/test_public_api_async.py::test_resume_run_reconstructs_full_request_payload tests/sdk/test_public_api_async.py::test_resume_run_preserves_legacy_boolean_resume_mode tests/sdk/test_public_api_async.py::test_resume_run_validates_typed_subquestion_decisions_before_dispatch tests/sdk/test_sdk_async_e2e.py::test_sdk_async_resume_e2e_supports_typed_subquestion_decision_matrix tests/sdk/test_sdk_async_e2e.py::test_sdk_async_resume_e2e_reuses_thread_id_after_interrupt` passed, confirming SDK async resume parity for typed subquestion checkpoint decisions while preserving both legacy `resume=True` and legacy object-style resume payload compatibility.

Next: update .planning/STATE.md after executing this phase's testing sections.

## Section 12 — 03-query-expansion-hitl-end-to-end — tests-3 — Test 1 (Validation)
- Source test markdown: `.planning/phases/03-query-expansion-hitl-end-to-end/tests-3.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 1 (Non-HITL backward compatibility remains unchanged).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/api/test_run_events_stream.py::test_run_events_stream_non_hitl_completed_run_has_no_pause_event`, `docker compose exec backend uv run pytest tests/services/test_agent_service.py::test_run_sequential_graph_runner_disables_query_expansion_per_run_without_mutating_defaults`, and `docker compose exec frontend npm run test -- --run src/App.test.tsx -t "keeps non-HITL runs on the default completion path without review UI or resume calls"` passed, confirming non-HITL runs still complete without `run.paused`, query-expansion review UI, or any resume request.

## Section 13 — 03-query-expansion-hitl-end-to-end — tests-3 — Test 2 (Validation)
- Source test markdown: `.planning/phases/03-query-expansion-hitl-end-to-end/tests-3.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 2 (HITL-enabled run pauses after expansion and before retrieval).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-15: `docker compose exec backend uv run pytest tests/api/test_run_events_stream.py::test_query_expansion_checkpoint_enabled_initial_run_pauses_with_interrupt_payload_and_checkpoint_id` and `docker compose exec frontend npm run test -- --run src/App.test.tsx -t "shows paused query expansion review and resumes to completion with typed decisions"` passed, confirming HITL-enabled runs emit a single `run.paused` after expansion candidates are available and before retrieval continues, with stable `checkpoint_id` plus actionable review payload that the frontend consumes into paused review UX.

## Section 14 — 03-query-expansion-hitl-end-to-end — tests-3 — Test 3 (Validation)
- Source test markdown: `.planning/phases/03-query-expansion-hitl-end-to-end/tests-3.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 3 (Approve decision resumes same run to completion).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/api/test_agent_run.py::test_post_run_resume_accepts_typed_query_expansion_decision_envelope tests/api/test_run_events_stream.py::test_query_expansion_checkpoint_resume_applies_typed_decisions_before_search` and `docker compose exec frontend npm run test -- --run src/App.test.tsx -t "shows paused query expansion review and resumes to completion with typed decisions"` passed, confirming the typed query-expansion resume envelope is accepted with the paused `checkpoint_id`, the paused run resumes into downstream search without spawning a new job, and the frontend continues the same `job_id` to `run.completed`.

## Section 15 — 03-query-expansion-hitl-end-to-end — tests-3 — Test 4 (Validation)
- Source test markdown: `.planning/phases/03-query-expansion-hitl-end-to-end/tests-3.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 4 (Edit decision uses operator-modified expansions).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/api/test_run_events_stream.py::test_query_expansion_checkpoint_resume_applies_typed_decisions_before_search tests/api/test_agent_run.py::test_post_run_resume_accepts_typed_query_expansion_decision_envelope` and `docker compose exec frontend npm run test -- --run src/App.test.tsx -t "shows paused query expansion review and resumes to completion with typed decisions"` passed, confirming the typed resume envelope accepts checkpoint-bound edit decisions, the runtime replaces generated expansions with the operator-edited query before `search`, and the frontend submits the edited expansion payload then resumes the same run to `run.completed`.

## Section 16 — 03-query-expansion-hitl-end-to-end — tests-3 — Test 5 (Validation)
- Source test markdown: `.planning/phases/03-query-expansion-hitl-end-to-end/tests-3.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 5 (Deny and skip paths are supported and deterministic).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/api/test_agent_run.py::test_post_run_resume_accepts_typed_query_expansion_decision_envelope tests/api/test_run_events_stream.py::test_query_expansion_checkpoint_resume_applies_typed_decisions_before_search` passed, confirming checkpoint-bound typed query-expansion resume envelopes accept both `deny` and `skip` and the runtime deterministically removes denied expansions while preserving skipped expansions before `search`; `docker compose exec frontend npm run test -- --run src/App.test.tsx -t "skips paused query expansion review with skip decisions and resumes to completion|shows paused query expansion review and resumes to completion with typed decisions"` also passed, confirming the UI supports both the mixed typed-decision review flow and the explicit skip-review path without breaking stream handling or terminal completion.

## Section 17 — 03-query-expansion-hitl-end-to-end — tests-3 — Test 6 (Validation)
- Source test markdown: `.planning/phases/03-query-expansion-hitl-end-to-end/tests-3.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 6 (Frontend review UX renders actionable controls and resumes stream).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec frontend npm run test -- --run src/App.test.tsx -t "shows paused query expansion review and resumes to completion with typed decisions"` passed, confirming the UI renders the query-expansion pause as actionable review state, submits a checkpoint-bound typed resume payload with approve/edit/deny decisions, and resumes the same event stream through `search` to terminal completion.

Next: update .planning/STATE.md after executing this phase's testing sections.

## Section 18 — 04-operator-controls-and-result-visibility — tests-4 — Test 1 (Validation)
- Source test markdown: `.planning/phases/04-operator-controls-and-result-visibility/tests-4.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 1 (UAT-4.1 Optional runtime config is additive and backward compatible).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/api/test_agent_run.py::test_post_run_accepts_additive_runtime_config_payload_without_breaking_legacy_forwarding tests/api/test_agent_run.py::test_post_run_async_accepts_additive_runtime_config_payload_without_breaking_legacy_forwarding tests/sdk/test_public_api.py::test_advanced_rag_preserves_omitted_controls_and_hitl_default_off tests/sdk/test_public_api_async.py::test_run_async_preserves_omitted_controls_and_hitl_default_off` passed, confirming `runtime_config` is additive on sync and async API requests and that omitting it still preserves legacy/default payload behavior in sync and async SDK flows.

## Section 19 — 04-operator-controls-and-result-visibility — tests-4 — Test 2 (Validation)
- Source test markdown: `.planning/phases/04-operator-controls-and-result-visibility/tests-4.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 2 (UAT-4.2 Per-run query expansion control affects only that run).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/services/test_agent_service.py::test_run_sequential_graph_runner_disables_query_expansion_per_run_without_mutating_defaults` passed, confirming a run with `runtime_config.query_expansion.enabled=false` skips expand-node execution and searches only the original sub-question, while the next run with omitted `runtime_config` restores default expansion behavior without cross-run mutation.

## Section 20 — 04-operator-controls-and-result-visibility — tests-4 — Test 3 (Validation)
- Source test markdown: `.planning/phases/04-operator-controls-and-result-visibility/tests-4.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 3 (UAT-4.3 Per-run rerank control affects only that run).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pass on 2026-03-14: `docker compose exec backend uv run pytest tests/services/test_agent_service.py::test_run_parallel_graph_runner_disables_rerank_per_run_without_mutating_defaults` passed, confirming a run with `runtime_config.rerank.enabled=false` bypasses rerank and carries search results directly into the answer path, while the next run with omitted `runtime_config` restores default rerank behavior without mutating global reranker defaults.

## Section 21 — 04-operator-controls-and-result-visibility — tests-4 — Test 4 (Validation)
- Source test markdown: `.planning/phases/04-operator-controls-and-result-visibility/tests-4.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 4 (UAT-4.4 Frontend controls map to canonical backend runtime config).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

## Section 22 — 04-operator-controls-and-result-visibility — tests-4 — Test 5 (Validation)
- Source test markdown: `.planning/phases/04-operator-controls-and-result-visibility/tests-4.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 5 (UAT-4.5 Sub-answer visibility remains stable across response shapes).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

Next: update .planning/STATE.md after executing this phase's testing sections.

## Section 23 — 05-prompt-customization-and-guidance — tests-5 — Test 1 (Validation)
- Source test markdown: `.planning/phases/05-prompt-customization-and-guidance/tests-5.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 1 (Alias Compatibility and Safe Prompt Key Handling).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

## Section 24 — 05-prompt-customization-and-guidance — tests-5 — Test 2 (Validation)
- Source test markdown: `.planning/phases/05-prompt-customization-and-guidance/tests-5.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 2 (Default Behavior Preserved When Overrides Are Omitted).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

## Section 25 — 05-prompt-customization-and-guidance — tests-5 — Test 3 (Validation)
- Source test markdown: `.planning/phases/05-prompt-customization-and-guidance/tests-5.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 3 (Prompt Override Influences Subanswer/Synthesis Output).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

## Section 26 — 05-prompt-customization-and-guidance — tests-5 — Test 4 (Validation)
- Source test markdown: `.planning/phases/05-prompt-customization-and-guidance/tests-5.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 4 (Guardrails Still Enforced Under Custom Prompts).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

## Section 27 — 05-prompt-customization-and-guidance — tests-5 — Test 5 (Validation)
- Source test markdown: `.planning/phases/05-prompt-customization-and-guidance/tests-5.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 5 (Deterministic Precedence in Public API (Sync + Async)).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

## Section 28 — 05-prompt-customization-and-guidance — tests-5 — Test 6 (Validation)
- Source test markdown: `.planning/phases/05-prompt-customization-and-guidance/tests-5.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 6 (Documentation UAT for Prompt Customization Discoverability).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

Next: update .planning/STATE.md after executing this phase's testing sections.

## Section 29 — 06-sdk-contract-parity-and-pypi-release — tests-6 — Test 1 (Validation)
- Source test markdown: `.planning/phases/06-sdk-contract-parity-and-pypi-release/tests-6.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 1 (Runtime API accepts canonical controls and preserves compatibility response fields).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

## Section 30 — 06-sdk-contract-parity-and-pypi-release — tests-6 — Test 2 (Validation)
- Source test markdown: `.planning/phases/06-sdk-contract-parity-and-pypi-release/tests-6.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 2 (OpenAPI and generated SDK artifacts stay in backend-contract parity).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

## Section 31 — 06-sdk-contract-parity-and-pypi-release — tests-6 — Test 3 (Validation)
- Source test markdown: `.planning/phases/06-sdk-contract-parity-and-pypi-release/tests-6.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 3 (Release guard blocks mismatched release tag before publish).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

## Section 32 — 06-sdk-contract-parity-and-pypi-release — tests-6 — Test 4 (Validation)
- Source test markdown: `.planning/phases/06-sdk-contract-parity-and-pypi-release/tests-6.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 4 (CI workflow publishes only validated uploaded artifacts).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

## Section 33 — 06-sdk-contract-parity-and-pypi-release — tests-6 — Test 5 (Validation)
- Source test markdown: `.planning/phases/06-sdk-contract-parity-and-pypi-release/tests-6.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`
- Phase context file: none present
- In the source test markdown, look for this test's `expected` field and any `result`, `reported`, `severity`, and `reason` fields.
- Also locate `what_changed`, `files_changed`, `code_areas`, and `testing_notes` under `## Information Needed from the Summary` when present.

Steps:
1. Re-read `Global Test Loading Rules`, `Global Test Recording Rules`, and `Global Commit Rules` at the top of this document.
2. Load the source test file, the phase research file, and the phase context file when present.
3. In the source test file, locate target test id/name: Test 5 (Public release docs provide a complete 1.0.3 adoption path).
4. Extract the test's `expected`, `result`, `reported`, `severity`, and `reason` fields from that test block.
5. Extract `what_changed`, `files_changed`, `code_areas`, and `testing_notes` from `## Information Needed from the Summary` when present.
6. Use extracted information from the source test markdown to execute and record the validation. Do not duplicate full test content into `IMPLEMENTATION_PLAN.md`.
7. Update the source test markdown for this exact test with the actual run result, including pass/fail and concise evidence.
8. Update any file-level bookkeeping in the source test markdown such as `Current Test`, `updated`, `Summary`, and `Gaps` so the file reflects the completed test.
9. Update this section's `Test results` notes in `IMPLEMENTATION_PLAN.md` with the same observed result summary.
10. After this test is fully recorded, write `.loop-commit-msg` with exactly one non-empty line in format `{phase}-{plan}-test{test-number}` (example: `01-02-test1`).

Test results:
- Pending.

Next: update .planning/STATE.md after executing this phase's testing sections.
