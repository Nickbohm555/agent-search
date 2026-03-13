Tasks are in **required implementation order** (1...n). Each section = one context window. Complete one section at a time.
Current section to work on: section 7. (move +1 after each turn)

## Summary Creation Instructions

### Ralph Loop Commit Contract (Global)
- The executor must not run `git commit` or `git push` directly.
- `.loop-commit-msg` must contain exactly one non-empty line.
- Implementation sections in this file must use exactly one commit subject format:
  - Task sections: `{phase}-{plan}-task{task-number}`
  - Summary sections: `{phase}-{plan}-summary`

Use this guide any time a section references `SUMMARY.md` creation.

**Purpose**
- Execute a phase prompt (`PLAN.md`) and create the outcome summary (`SUMMARY.md`).

**Required reading before writing**
- Read `.planning/STATE.md` to load project context.
- Read `.planning/config.json` for planning behavior settings.

**How to create a good summary**
1. Identify the plan and summary file path: `.planning/phases/XX-name/{phase}-{plan}-SUMMARY.md`.
2. Read the executed `*-PLAN.md` and extract objective, tasks, verification requirements, success criteria, and output intent.
3. Gather execution evidence from git history (not memory):
   - `git log --oneline --grep="^<plan-id>-task[0-9]+$"`
   - `git show --stat --name-status <commit>` for each matching task commit.
4. Write the summary title as `# Phase [X] Plan [Y]: [Name] Summary`.
5. Add a substantive one-line outcome under the title.
   - Good: `JWT auth with refresh rotation using jose library`
   - Bad: `Authentication implemented`
6. Populate frontmatter from execution context:
   - `phase`, `plan`, `subsystem`, `tags`
   - `requires`, `provides`, `affects`
   - `tech-stack.added`, `tech-stack.patterns`
   - `key-files.created`, `key-files.modified`
   - `key-decisions`
   - `duration` (from `$DURATION`), `completed` (from `$PLAN_END_TIME`, `YYYY-MM-DD`)
7. Ensure claims map to evidence from task commits, and preserve task-to-commit traceability.
8. Include a deviations section:
   - If none: state the plan executed as written.
   - If present: list rule triggered, change made, verification performed, and commit hash.
9. Keep the summary focused on what was actually delivered, verified, and learned.

## Section 1 — 01-contract-foundation-and-compatibility-baseline — 01-01 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Load `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md` and use it as the reference baseline.
2. No phase context file exists for this phase; continue using roadmap/research intent only.
3. Execute only Task 1 action: add optional nested request controls on `RuntimeAgentRunRequest` and additive `sub_answers` response fields while preserving legacy fields/defaults.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "run or status"`.
5. Do not mark complete until done condition is true: legacy and additive payloads validate and response models expose additive `sub_answers`.
6. Write `.loop-commit-msg` with exactly one non-empty line: `01-01-task1`.
7. Update `.planning/STATE.md` with `phase=01` / `plan=01-01` / `task=1` / `status=implemented`.

## Section 2 — 01-contract-foundation-and-compatibility-baseline — 01-01 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Load the phase research file and use it as the implementation reference.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: replace thread-only config mapping with a single additive mapper for `thread_id`, `rerank`, `query_expansion`, and `hitl` across `/run` and `/run-async`.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "post_run or run_async"`.
5. Do not mark complete until done condition is true: both sync/async forward identical normalized config and omitted controls keep prior behavior.
6. Write `.loop-commit-msg` with exactly one non-empty line: `01-01-task2`.
7. Update `.planning/STATE.md` with `phase=01` / `plan=01-01` / `task=2` / `status=implemented`.

## Section 3 — 01-contract-foundation-and-compatibility-baseline — 01-01 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Load the phase research file and keep compatibility constraints primary.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: extend router tests for legacy validity, additive control forwarding, and additive `sub_answers` with `sub_qa` intact.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py`.
5. Do not mark complete until done condition is true: router tests explicitly enforce CTRL-02/CTRL-04/CTRL-05 and REL-01 baseline behavior.
6. Write `.loop-commit-msg` with exactly one non-empty line: `01-01-task3`.
7. Update `.planning/STATE.md` with `phase=01` / `plan=01-01` / `task=3` / `status=implemented`.

## Section 4 — 01-contract-foundation-and-compatibility-baseline — 01-01 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Create `01-01-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `01-01-summary`.
3. Update `.planning/STATE.md` with `phase=01` / `plan=01-01` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md` to mark phase completion, keeping commit subject `01-01-summary`.

## Section 5 — 01-contract-foundation-and-compatibility-baseline — 01-02 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/02-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Load the phase research file and preserve default-off compatibility.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: normalize control-to-runtime config translation in public API for `advanced_rag` and `run_async` with compatibility-safe defaults.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api.py src/backend/tests/sdk/test_runtime_config.py`.
5. Do not mark complete until done condition is true: controls are parsed/reflected and legacy defaults remain unchanged.
6. Write `.loop-commit-msg` with exactly one non-empty line: `01-02-task1`.
7. Update `.planning/STATE.md` with `phase=01` / `plan=01-02` / `task=1` / `status=implemented`.

## Section 6 — 01-contract-foundation-and-compatibility-baseline — 01-02 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/02-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Load research and keep async/resume continuity constraints.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: persist normalized request payload in runtime jobs and reconstruct full request during resume so controls are not dropped.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api_async.py -k "run_async or resume"`.
5. Do not mark complete until done condition is true: resumed runs keep original controls and omitted controls preserve baseline behavior.
6. Write `.loop-commit-msg` with exactly one non-empty line: `01-02-task2`.
7. Update `.planning/STATE.md` with `phase=01` / `plan=01-02` / `task=2` / `status=implemented`.

## Section 7 — 01-contract-foundation-and-compatibility-baseline — 01-02 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/02-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Load research and enforce regression expectations.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: add sync/async control propagation regressions in SDK tests, including default-off HITL assertions.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api.py src/backend/tests/sdk/test_public_api_async.py`.
5. Do not mark complete until done condition is true: tests fail on dropped controls, implicit enablement, or changed omitted-field defaults.
6. Write `.loop-commit-msg` with exactly one non-empty line: `01-02-task3`.
7. Update `.planning/STATE.md` with `phase=01` / `plan=01-02` / `task=3` / `status=implemented`.

## Section 8 — 01-contract-foundation-and-compatibility-baseline — 01-02 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/02-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Create `01-02-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `01-02-summary`.
3. Update `.planning/STATE.md` with `phase=01` / `plan=01-02` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md` accordingly, keeping commit subject `01-02-summary`.

## Section 9 — 01-contract-foundation-and-compatibility-baseline — 01-03 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/03-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Load research and preserve additive response compatibility.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: emit additive `sub_answers` as alias of `sub_qa` in runtime response mapping without removing legacy fields.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/services/test_agent_service.py -k "runtime response or map_graph_state"`.
5. Do not mark complete until done condition is true: mapped responses include both fields with equivalent content and no regression.
6. Write `.loop-commit-msg` with exactly one non-empty line: `01-03-task1`.
7. Update `.planning/STATE.md` with `phase=01` / `plan=01-03` / `task=1` / `status=implemented`.

## Section 10 — 01-contract-foundation-and-compatibility-baseline — 01-03 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/03-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Load research and keep frontend contract tolerance additive.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: extend frontend API validators/types to accept additive `sub_answers` while preserving `sub_qa` behavior and old responses.
4. Run verify checks one by one: `docker compose exec frontend npm run typecheck`; `docker compose exec frontend npm run build`.
5. Do not mark complete until done condition is true: frontend compiles and guards accept old and additive shapes.
6. Write `.loop-commit-msg` with exactly one non-empty line: `01-03-task2`.
7. Update `.planning/STATE.md` with `phase=01` / `plan=01-03` / `task=2` / `status=implemented`.

## Section 11 — 01-contract-foundation-and-compatibility-baseline — 01-03 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/03-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Load research and lock REL-01 with compatibility tests.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: add compatibility tests ensuring `sub_answers` is additive and required legacy fields remain stable.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/services/test_agent_service.py src/backend/tests/contracts/test_public_contracts.py`.
5. Do not mark complete until done condition is true: tests fail on breaking rename/removal.
6. Write `.loop-commit-msg` with exactly one non-empty line: `01-03-task3`.
7. Update `.planning/STATE.md` with `phase=01` / `plan=01-03` / `task=3` / `status=implemented`.

## Section 12 — 01-contract-foundation-and-compatibility-baseline — 01-03 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/03-PLAN.md`
- Phase research file: `.planning/phases/01-contract-foundation-and-compatibility-baseline/01-RESEARCH.md`

**Steps:**
1. Create `01-03-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `01-03-summary`.
3. Update `.planning/STATE.md` with `phase=01` / `plan=01-03` / `task=summary` / `status=implemented`.
4. This summary can complete Phase 01; if so, update `.planning/ROADMAP.md` and `.planning/STATE.md` phase status while keeping commit subject `01-03-summary`.

## Section 13 — 02-subquestion-hitl-end-to-end — 02-01 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-01-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Load `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md` as required reference.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: add additive subquestion HITL contracts (run-async enablement, typed resume envelope with `checkpoint_id` and approve/edit/deny/skip), preserving legacy `resume=True`.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "run_async or resume"`.
5. Do not mark complete until done condition is true: typed HITL payloads validate and old payloads still work default-off.
6. Write `.loop-commit-msg` with exactly one non-empty line: `02-01-task1`.
7. Update `.planning/STATE.md` with `phase=02` / `plan=02-01` / `task=1` / `status=implemented`.

## Section 14 — 02-subquestion-hitl-end-to-end — 02-01 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-01-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Load phase research and keep contract scope only.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: add API regressions for additive/default payloads and typed validation errors for malformed decision envelopes.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "hitl or resume or validation"`.
5. Do not mark complete until done condition is true: tests enforce additive contract compatibility and typed boundary validation.
6. Write `.loop-commit-msg` with exactly one non-empty line: `02-01-task2`.
7. Update `.planning/STATE.md` with `phase=02` / `plan=02-01` / `task=2` / `status=implemented`.

## Section 15 — 02-subquestion-hitl-end-to-end — 02-01 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-01-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Create `02-01-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `02-01-summary`.
3. Update `.planning/STATE.md` with `phase=02` / `plan=02-01` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `02-01-summary`.

## Section 16 — 02-subquestion-hitl-end-to-end — 02-02 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-02-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Load phase research and Plan 02-04 dependency intent.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: add typed frontend contracts and paused payload validation for subquestion HITL start/resume.
4. Run verify checks one by one: `docker compose exec frontend npm run typecheck`.
5. Do not mark complete until done condition is true: frontend API layer handles typed paused payload and resume decisions without `any`.
6. Write `.loop-commit-msg` with exactly one non-empty line: `02-02-task1`.
7. Update `.planning/STATE.md` with `phase=02` / `plan=02-02` / `task=1` / `status=implemented`.

## Section 17 — 02-subquestion-hitl-end-to-end — 02-02 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-02-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Load research and keep paused state actionable, not failed.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: implement paused review UX for approve/edit/deny/skip, bind resume to `job_id` + `checkpoint_id`, and continue stream to completion.
4. Run verify checks one by one: `docker compose exec frontend npm run test -- App.test.tsx`.
5. Do not mark complete until done condition is true: paused -> running -> completed path works with decisions.
6. Write `.loop-commit-msg` with exactly one non-empty line: `02-02-task2`.
7. Update `.planning/STATE.md` with `phase=02` / `plan=02-02` / `task=2` / `status=implemented`.

## Section 18 — 02-subquestion-hitl-end-to-end — 02-02 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-02-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Load research and enforce parity between HITL and non-HITL flows.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: add frontend regressions for paused rendering, decision payloads, resumed completion, and non-HITL unchanged behavior.
4. Run verify checks one by one: `docker compose exec frontend npm run test -- App.test.tsx && docker compose exec frontend npm run typecheck`.
5. Do not mark complete until done condition is true: tests protect actionable pause semantics and default path.
6. Write `.loop-commit-msg` with exactly one non-empty line: `02-02-task3`.
7. Update `.planning/STATE.md` with `phase=02` / `plan=02-02` / `task=3` / `status=implemented`.

## Section 19 — 02-subquestion-hitl-end-to-end — 02-02 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-02-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Create `02-02-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `02-02-summary`.
3. Update `.planning/STATE.md` with `phase=02` / `plan=02-02` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `02-02-summary`.

## Section 20 — 02-subquestion-hitl-end-to-end — 02-03 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-03-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Load phase research and align SDK schema parity with backend contracts.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: mirror backend subquestion HITL models into `sdk/core` schemas with additive defaults.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api_async.py -k "schema or request"`.
5. Do not mark complete until done condition is true: SDK schema supports typed HITL config/resume without breaking existing signatures.
6. Write `.loop-commit-msg` with exactly one non-empty line: `02-03-task1`.
7. Update `.planning/STATE.md` with `phase=02` / `plan=02-03` / `task=1` / `status=implemented`.

## Section 21 — 02-subquestion-hitl-end-to-end — 02-03 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-03-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Load research and preserve legacy async endpoint shape.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: wire SDK async APIs/runtime jobs for typed HITL start/resume and paused metadata exposure.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api_async.py -k "run_async or resume"`.
5. Do not mark complete until done condition is true: SDK users can start HITL runs and resume via existing methods.
6. Write `.loop-commit-msg` with exactly one non-empty line: `02-03-task2`.
7. Update `.planning/STATE.md` with `phase=02` / `plan=02-03` / `task=2` / `status=implemented`.

## Section 22 — 02-subquestion-hitl-end-to-end — 02-03 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-03-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Load research and verify full SDK async behavior.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: add SDK regressions for approve/edit/deny/skip/default-off and malformed envelope errors.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api_async.py src/backend/tests/sdk/test_sdk_async_e2e.py`.
5. Do not mark complete until done condition is true: tests prove SQH parity and backward compatibility.
6. Write `.loop-commit-msg` with exactly one non-empty line: `02-03-task3`.
7. Update `.planning/STATE.md` with `phase=02` / `plan=02-03` / `task=3` / `status=implemented`.

## Section 23 — 02-subquestion-hitl-end-to-end — 02-03 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-03-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Create `02-03-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `02-03-summary`.
3. Update `.planning/STATE.md` with `phase=02` / `plan=02-03` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `02-03-summary`.

## Section 24 — 02-subquestion-hitl-end-to-end — 02-04 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-04-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Load phase research and checkpoint positioning constraints.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: insert decompose-to-fanout checkpoint gate and ensure HITL-enabled initial runs pause while non-HITL flow is unchanged.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_run_events_stream.py -k "checkpoint or paused"`.
5. Do not mark complete until done condition is true: HITL runs pause exactly once at `subquestions_ready`; non-HITL bypasses pause.
6. Write `.loop-commit-msg` with exactly one non-empty line: `02-04-task1`.
7. Update `.planning/STATE.md` with `phase=02` / `plan=02-04` / `task=1` / `status=implemented`.

## Section 25 — 02-subquestion-hitl-end-to-end — 02-04 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-04-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Load research and enforce deterministic decision semantics.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: apply typed approve/edit/deny/skip in shared resume path and persist/emit `interrupt_payload` + `checkpoint_id`.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_run_events_stream.py -k "resume or interrupt_payload or checkpoint_id"`.
5. Do not mark complete until done condition is true: resumed subquestions are deterministic and paused payload always includes checkpoint metadata.
6. Write `.loop-commit-msg` with exactly one non-empty line: `02-04-task2`.
7. Update `.planning/STATE.md` with `phase=02` / `plan=02-04` / `task=2` / `status=implemented`.

## Section 26 — 02-subquestion-hitl-end-to-end — 02-04 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-04-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Load research and protect SSE contract shape.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: expand SSE/lifecycle tests for paused payload shape, decision-driven resume behavior, and no-pause non-HITL flow.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_run_events_stream.py`.
5. Do not mark complete until done condition is true: event-stream regressions protect checkpoint semantics and payload structure.
6. Write `.loop-commit-msg` with exactly one non-empty line: `02-04-task3`.
7. Update `.planning/STATE.md` with `phase=02` / `plan=02-04` / `task=3` / `status=implemented`.

## Section 27 — 02-subquestion-hitl-end-to-end — 02-04 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/02-subquestion-hitl-end-to-end/02-04-PLAN.md`
- Phase research file: `.planning/phases/02-subquestion-hitl-end-to-end/02-RESEARCH.md`

**Steps:**
1. Create `02-04-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `02-04-summary`.
3. Update `.planning/STATE.md` with `phase=02` / `plan=02-04` / `task=summary` / `status=implemented`.
4. This summary can complete Phase 02; if so, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `02-04-summary`.

## Section 28 — 03-query-expansion-hitl-end-to-end — 03-01 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-01-PLAN.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`

**Steps:**
1. Load phase research and preserve additive/default-off behavior.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: add query-expansion HITL contracts across backend/router/public API and SDK schemas with typed resume envelope.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "run_async or resume"`.
5. Do not mark complete until done condition is true: API and SDK accept new fields while legacy non-HITL calls remain unchanged.
6. Write `.loop-commit-msg` with exactly one non-empty line: `03-01-task1`.
7. Update `.planning/STATE.md` with `phase=03` / `plan=03-01` / `task=1` / `status=implemented`.

## Section 29 — 03-query-expansion-hitl-end-to-end — 03-01 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-01-PLAN.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`

**Steps:**
1. Load research and keep this plan contract-scoped.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: add backend API regression coverage for additive query-expansion HITL compatibility and typed boundary handling.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "query_expansion or run_async or resume"`.
5. Do not mark complete until done condition is true: tests lock additive compatibility at API boundary.
6. Write `.loop-commit-msg` with exactly one non-empty line: `03-01-task2`.
7. Update `.planning/STATE.md` with `phase=03` / `plan=03-01` / `task=2` / `status=implemented`.

## Section 30 — 03-query-expansion-hitl-end-to-end — 03-01 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-01-PLAN.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`

**Steps:**
1. Create `03-01-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `03-01-summary`.
3. Update `.planning/STATE.md` with `phase=03` / `plan=03-01` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `03-01-summary`.

## Section 31 — 03-query-expansion-hitl-end-to-end — 03-02 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-02-PLAN.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`

**Steps:**
1. Load phase research and expand-to-search checkpoint requirements.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: insert query-expansion checkpoint before retrieval, ensure initial HITL runs pause, apply deterministic approve/edit/deny/skip decisions, persist and emit checkpoint metadata.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_run_events_stream.py -k "paused or checkpoint"`.
5. Do not mark complete until done condition is true: HITL pauses before retrieval and resumed runs use reviewed expansions.
6. Write `.loop-commit-msg` with exactly one non-empty line: `03-02-task1`.
7. Update `.planning/STATE.md` with `phase=03` / `plan=03-02` / `task=1` / `status=implemented`.

## Section 32 — 03-query-expansion-hitl-end-to-end — 03-02 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-02-PLAN.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`

**Steps:**
1. Load research and test QEH-01..QEH-05 end-to-end at backend boundary.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: add regressions for enablement, approve/edit/deny/skip semantics, paused payload shape, and non-HITL no-pause behavior.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py src/backend/tests/api/test_run_events_stream.py`.
5. Do not mark complete until done condition is true: automated tests prove QEH behavior and compatibility defaults.
6. Write `.loop-commit-msg` with exactly one non-empty line: `03-02-task2`.
7. Update `.planning/STATE.md` with `phase=03` / `plan=03-02` / `task=2` / `status=implemented`.

## Section 33 — 03-query-expansion-hitl-end-to-end — 03-02 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-02-PLAN.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`

**Steps:**
1. Create `03-02-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `03-02-summary`.
3. Update `.planning/STATE.md` with `phase=03` / `plan=03-02` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `03-02-summary`.

## Section 34 — 03-query-expansion-hitl-end-to-end — 03-03 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-03-PLAN.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`

**Steps:**
1. Load phase research and keep typed frontend payload handling strict.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: extend frontend API guards/types for query-expansion HITL config, paused payloads, and typed resume decisions.
4. Run verify checks one by one: `docker compose exec frontend npm run typecheck`.
5. Do not mark complete until done condition is true: frontend parses paused payloads and builds typed decisions safely.
6. Write `.loop-commit-msg` with exactly one non-empty line: `03-03-task1`.
7. Update `.planning/STATE.md` with `phase=03` / `plan=03-03` / `task=1` / `status=implemented`.

## Section 35 — 03-query-expansion-hitl-end-to-end — 03-03 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-03-PLAN.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`

**Steps:**
1. Load research and treat `run.paused` as expected actionable state.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: implement query-expansion paused review UI for approve/edit/deny/skip and resume bound to `job_id` + `checkpoint_id`.
4. Run verify checks one by one: `docker compose exec frontend npm run test -- App.test.tsx`.
5. Do not mark complete until done condition is true: users can review expansions and continue same run to completion.
6. Write `.loop-commit-msg` with exactly one non-empty line: `03-03-task2`.
7. Update `.planning/STATE.md` with `phase=03` / `plan=03-03` / `task=2` / `status=implemented`.

## Section 36 — 03-query-expansion-hitl-end-to-end — 03-03 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-03-PLAN.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`

**Steps:**
1. Load research and preserve non-HITL UX continuity.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: add frontend regressions for paused controls/payloads, resumed transitions, and unchanged non-HITL flow.
4. Run verify checks one by one: `docker compose exec frontend npm run test -- App.test.tsx && docker compose exec frontend npm run typecheck`.
5. Do not mark complete until done condition is true: tests lock actionable pause behavior and backward compatibility.
6. Write `.loop-commit-msg` with exactly one non-empty line: `03-03-task3`.
7. Update `.planning/STATE.md` with `phase=03` / `plan=03-03` / `task=3` / `status=implemented`.

## Section 37 — 03-query-expansion-hitl-end-to-end — 03-03 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-03-PLAN.md`
- Phase research file: `.planning/phases/03-query-expansion-hitl-end-to-end/03-RESEARCH.md`

**Steps:**
1. Create `03-03-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `03-03-summary`.
3. Update `.planning/STATE.md` with `phase=03` / `plan=03-03` / `task=summary` / `status=implemented`.
4. This summary can complete Phase 03; if so, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `03-03-summary`.

## Section 38 — 04-operator-controls-and-result-visibility — 04-01 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-01-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Load `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: add additive optional `runtime_config` contract to `RuntimeAgentRunRequest` carrying `rerank` and `query_expansion`.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "thread_id or run"`.
5. Do not mark complete until done condition is true: `runtime_config` is optional and legacy payloads still pass.
6. Write `.loop-commit-msg` with exactly one non-empty line: `04-01-task1`.
7. Update `.planning/STATE.md` with `phase=04` / `plan=04-01` / `task=1` / `status=implemented`.

## Section 39 — 04-operator-controls-and-result-visibility — 04-01 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-01-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Load research and keep SDK interface decoupled from UI naming.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: forward `runtime_config` through router and SDK sync/async entrypoints alongside `thread_id`.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api.py src/backend/tests/sdk/test_public_api_async.py`.
5. Do not mark complete until done condition is true: forwarding works and signatures/thread lineage remain unchanged.
6. Write `.loop-commit-msg` with exactly one non-empty line: `04-01-task2`.
7. Update `.planning/STATE.md` with `phase=04` / `plan=04-01` / `task=2` / `status=implemented`.

## Section 40 — 04-operator-controls-and-result-visibility — 04-01 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-01-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Load research and lock additive contract coverage.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: add API/SDK regressions for `runtime_config.rerank.enabled` and `runtime_config.query_expansion.enabled` plus legacy payload compatibility.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py src/backend/tests/sdk/test_public_api.py src/backend/tests/sdk/test_public_api_async.py`.
5. Do not mark complete until done condition is true: tests prove additive forwarding and no legacy break.
6. Write `.loop-commit-msg` with exactly one non-empty line: `04-01-task3`.
7. Update `.planning/STATE.md` with `phase=04` / `plan=04-01` / `task=3` / `status=implemented`.

## Section 41 — 04-operator-controls-and-result-visibility — 04-01 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-01-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Create `04-01-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `04-01-summary`.
3. Update `.planning/STATE.md` with `phase=04` / `plan=04-01` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `04-01-summary`.

## Section 42 — 04-operator-controls-and-result-visibility — 04-02 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-02-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Load phase research and preserve current defaults.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: extend `RuntimeConfig` with `query_expansion` section and fallback behavior for invalid values; add parser tests.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_runtime_config.py`.
5. Do not mark complete until done condition is true: defaults/overrides/fallback behavior is stable and tested.
6. Write `.loop-commit-msg` with exactly one non-empty line: `04-02-task1`.
7. Update `.planning/STATE.md` with `phase=04` / `plan=04-02` / `task=1` / `status=implemented`.

## Section 43 — 04-operator-controls-and-result-visibility — 04-02 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-02-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Load research and keep changes scoped to config selection/wiring.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: apply per-run runtime config in expand/rerank execution, replacing env-only assumptions while preserving omitted-field defaults.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/services/test_agent_service.py -k "expand or rerank or runtime_config"`.
5. Do not mark complete until done condition is true: expand/rerank behavior changes when supplied, baseline remains when absent.
6. Write `.loop-commit-msg` with exactly one non-empty line: `04-02-task2`.
7. Update `.planning/STATE.md` with `phase=04` / `plan=04-02` / `task=2` / `status=implemented`.

## Section 44 — 04-operator-controls-and-result-visibility — 04-02 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-02-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Load research and validate true runtime behavior (not object construction only).
2. No phase context file exists for this phase.
3. Execute only Task 3 action: add service-level regressions for per-run query expansion/rerank disable toggles without global default mutation.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/services/test_agent_service.py`.
5. Do not mark complete until done condition is true: tests show behavior toggles are effective and isolated.
6. Write `.loop-commit-msg` with exactly one non-empty line: `04-02-task3`.
7. Update `.planning/STATE.md` with `phase=04` / `plan=04-02` / `task=3` / `status=implemented`.

## Section 45 — 04-operator-controls-and-result-visibility — 04-02 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-02-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Create `04-02-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `04-02-summary`.
3. Update `.planning/STATE.md` with `phase=04` / `plan=04-02` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `04-02-summary`.

## Section 46 — 04-operator-controls-and-result-visibility — 04-03 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-03-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Load phase research and map UI booleans to canonical backend fields.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: add independent frontend rerank/query expansion controls and serialize to `runtime_config.rerank.enabled` and `runtime_config.query_expansion.enabled`.
4. Run verify checks one by one: `docker compose exec frontend npm run test -- App.test.tsx`.
5. Do not mark complete until done condition is true: request body includes correctly mapped independent toggles.
6. Write `.loop-commit-msg` with exactly one non-empty line: `04-03-task1`.
7. Update `.planning/STATE.md` with `phase=04` / `plan=04-03` / `task=1` / `status=implemented`.

## Section 47 — 04-operator-controls-and-result-visibility — 04-03 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-03-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Load research and preserve sub-answer rendering continuity.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: normalize `sub_answers` alongside `sub_qa` in frontend parsing and keep `sub_qa` support unchanged.
4. Run verify checks one by one: `docker compose exec frontend npm run test -- App.test.tsx -t "subanswer|run query flow|SSE"`.
5. Do not mark complete until done condition is true: sub-answer panels/summaries remain stable for streamed and final payloads.
6. Write `.loop-commit-msg` with exactly one non-empty line: `04-03-task2`.
7. Update `.planning/STATE.md` with `phase=04` / `plan=04-03` / `task=2` / `status=implemented`.

## Section 48 — 04-operator-controls-and-result-visibility — 04-03 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-03-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Load research and keep regression coverage focused on UX + payload shape.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: add frontend tests for control defaults/toggles, `runtime_config` request payload, and retained sub-answer rendering.
4. Run verify checks one by one: `docker compose exec frontend npm run test -- App.test.tsx`.
5. Do not mark complete until done condition is true: tests prove CTRL-01 and REL-02 behavior continuity.
6. Write `.loop-commit-msg` with exactly one non-empty line: `04-03-task3`.
7. Update `.planning/STATE.md` with `phase=04` / `plan=04-03` / `task=3` / `status=implemented`.

## Section 49 — 04-operator-controls-and-result-visibility — 04-03 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/04-operator-controls-and-result-visibility/04-03-PLAN.md`
- Phase research file: `.planning/phases/04-operator-controls-and-result-visibility/04-RESEARCH.md`

**Steps:**
1. Create `04-03-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `04-03-summary`.
3. Update `.planning/STATE.md` with `phase=04` / `plan=04-03` / `task=summary` / `status=implemented`.
4. This summary can complete Phase 04; if so, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `04-03-summary`.

## Section 50 — 05-prompt-customization-and-guidance — 05-01 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-01-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: add typed `custom_prompts` contract (`subanswer`, `synthesis`) with `custom-prompts` alias support and safe unknown-key ignore behavior in backend/SDK config parsing.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_runtime_config.py src/backend/tests/api/test_agent_run.py -k "runtime_config or run"`.
5. Do not mark complete until done condition is true: prompt maps parse additively and legacy payloads remain valid.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-01-task1`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-01` / `task=1` / `status=implemented`.

## Section 51 — 05-prompt-customization-and-guidance — 05-01 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-01-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load research and keep this step request-to-config forwarding only.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: forward prompt maps through router config assembly for sync and async while preserving `thread_id` behavior.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py -k "run and custom"`.
5. Do not mark complete until done condition is true: endpoints pass normalized prompt values into runtime config without regression.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-01-task2`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-01` / `task=2` / `status=implemented`.

## Section 52 — 05-prompt-customization-and-guidance — 05-01 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-01-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load research and enforce alias/additive compatibility.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: add tests for `custom-prompts` and `custom_prompts`, unknown-key handling, and legacy omission compatibility.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py src/backend/tests/sdk/test_runtime_config.py`.
5. Do not mark complete until done condition is true: regressions prove required aliasing and additive behavior.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-01-task3`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-01` / `task=3` / `status=implemented`.

## Section 53 — 05-prompt-customization-and-guidance — 05-01 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-01-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Create `05-01-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `05-01-summary`.
3. Update `.planning/STATE.md` with `phase=05` / `plan=05-01` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `05-01-summary`.

## Section 54 — 05-prompt-customization-and-guidance — 05-02 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-02-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load phase research and keep defaults/fallback safety unchanged.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: add optional prompt-template parameters to subanswer/synthesis services with current templates as defaults; preserve no-key/no-evidence fallback behavior.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/services/test_subanswer_service.py src/backend/tests/services/test_initial_answer_service.py`.
5. Do not mark complete until done condition is true: services accept overrides and default/fallback behavior is intact.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-02-task1`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-02` / `task=1` / `status=implemented`.

## Section 55 — 05-prompt-customization-and-guidance — 05-02 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-02-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load research and focus on service-level regression hardening.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: add tests comparing unset override vs default templates and fallback safety under failure conditions with provided overrides.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/services/test_subanswer_service.py src/backend/tests/services/test_initial_answer_service.py -k "prompt or fallback or default"`.
5. Do not mark complete until done condition is true: service tests lock prompt parameter semantics and baseline safety.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-02-task2`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-02` / `task=2` / `status=implemented`.

## Section 56 — 05-prompt-customization-and-guidance — 05-02 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-02-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Create `05-02-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `05-02-summary`.
3. Update `.planning/STATE.md` with `phase=05` / `plan=05-02` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `05-02-summary`.

## Section 57 — 05-prompt-customization-and-guidance — 05-03 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-03-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load phase research and keep docs aligned to implementation.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: create canonical `docs/prompt-customization.md` documenting keys, responsibilities, defaults, precedence, and canonical naming with alias note.
4. Run verify checks one by one: `rg -n "subanswer|synthesis|precedence|custom-prompts|custom_prompts" docs/prompt-customization.md`.
5. Do not mark complete until done condition is true: guide includes all required sections and explicit boundaries.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-03-task1`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-03` / `task=1` / `status=implemented`.

## Section 58 — 05-prompt-customization-and-guidance — 05-03 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-03-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load research and keep SDK examples tied to existing config-map workflow.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: update `sdk/core/README.md` and `sdk/python/README.md` with mutable defaults and per-run override examples plus merge behavior.
4. Run verify checks one by one: `rg -n "custom_prompts|custom-prompts|subanswer|synthesis|override" sdk/core/README.md sdk/python/README.md`.
5. Do not mark complete until done condition is true: SDK docs clearly demonstrate PRM-03 usage patterns.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-03-task2`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-03` / `task=2` / `status=implemented`.

## Section 59 — 05-prompt-customization-and-guidance — 05-03 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-03-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load research and keep top-level guidance concise and safety-focused.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: add root README pointer to prompt customization guidance and explicit note that citation/fallback safeguards remain code-level.
4. Run verify checks one by one: `rg -n "prompt customization|custom prompts|citation|fallback" README.md`.
5. Do not mark complete until done condition is true: root docs route users correctly and set safe-use expectations.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-03-task3`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-03` / `task=3` / `status=implemented`.

## Section 60 — 05-prompt-customization-and-guidance — 05-03 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-03-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Create `05-03-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `05-03-summary`.
3. Update `.planning/STATE.md` with `phase=05` / `plan=05-03` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `05-03-summary`.

## Section 61 — 05-prompt-customization-and-guidance — 05-04 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-04-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load phase research and maintain node-level safeguards.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: wire effective `subanswer` and `synthesis` prompts through agent service into answer/synthesize nodes without weakening citation/fallback enforcement.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_node_answer.py src/backend/tests/sdk/test_node_synthesize.py src/backend/tests/services/test_agent_service.py -k "synth or answer or prompt"`.
5. Do not mark complete until done condition is true: runtime nodes consume resolved prompts and safeguards remain active.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-04-task1`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-04` / `task=1` / `status=implemented`.

## Section 62 — 05-prompt-customization-and-guidance — 05-04 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-04-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load research and verify both influence and safety in tests.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: add integration tests proving prompt text reaches generation and can influence deterministic outputs while citation/fallback guardrails still enforce behavior.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_node_answer.py src/backend/tests/sdk/test_node_synthesize.py src/backend/tests/services/test_agent_service.py`.
5. Do not mark complete until done condition is true: tests prove PRM-01/PRM-02 influence with safeguards preserved.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-04-task2`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-04` / `task=2` / `status=implemented`.

## Section 63 — 05-prompt-customization-and-guidance — 05-04 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-04-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Create `05-04-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `05-04-summary`.
3. Update `.planning/STATE.md` with `phase=05` / `plan=05-04` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `05-04-summary`.

## Section 64 — 05-prompt-customization-and-guidance — 05-05 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-05-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load phase research and keep precedence deterministic across sync/async.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: implement prompt precedence merge in backend/core SDK public APIs (defaults -> SDK/client map -> per-run override) with defensive copying for mutable maps.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api.py src/backend/tests/sdk/test_public_api_async.py -k "config or precedence or prompt"`.
5. Do not mark complete until done condition is true: sync and async precedence matches and mutable defaults are isolated.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-05-task1`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-05` / `task=1` / `status=implemented`.

## Section 65 — 05-prompt-customization-and-guidance — 05-05 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-05-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Load research and keep tests merge-plumbing scoped.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: add focused regressions for precedence ordering and mutable-default map isolation across runs.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_public_api.py src/backend/tests/sdk/test_public_api_async.py`.
5. Do not mark complete until done condition is true: regression suite proves PRM-03 precedence and isolation.
6. Write `.loop-commit-msg` with exactly one non-empty line: `05-05-task2`.
7. Update `.planning/STATE.md` with `phase=05` / `plan=05-05` / `task=2` / `status=implemented`.

## Section 66 — 05-prompt-customization-and-guidance — 05-05 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/05-prompt-customization-and-guidance/05-05-PLAN.md`
- Phase research file: `.planning/phases/05-prompt-customization-and-guidance/05-RESEARCH.md`

**Steps:**
1. Create `05-05-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `05-05-summary`.
3. Update `.planning/STATE.md` with `phase=05` / `plan=05-05` / `task=summary` / `status=implemented`.
4. This summary can complete Phase 05; if so, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `05-05-summary`.

## Section 67 — 06-sdk-contract-parity-and-pypi-release — 06-01 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-01-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Load `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: lock canonical contract fields/aliases for HITL, controls, prompts, and additive `sub_answers` across backend and `sdk/core` with compatibility-safe defaults.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py src/backend/tests/sdk/test_runtime_config.py -k "runtime_config or hitl or prompt or sub_answers or sub_qa"`.
5. Do not mark complete until done condition is true: backend and sdk/core models expose all REL-03 fields with additive compatibility behavior.
6. Write `.loop-commit-msg` with exactly one non-empty line: `06-01-task1`.
7. Update `.planning/STATE.md` with `phase=06` / `plan=06-01` / `task=1` / `status=implemented`.

## Section 68 — 06-sdk-contract-parity-and-pypi-release — 06-01 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-01-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Load research and keep generated artifacts non-hand-edited.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: regenerate OpenAPI and generated SDK artifacts atomically via repository scripts.
4. Run verify checks one by one: `./scripts/update_sdk.sh`; `./scripts/validate_openapi.sh`.
5. Do not mark complete until done condition is true: `openapi.json` and generated `sdk/python` models are refreshed and drift-free.
6. Write `.loop-commit-msg` with exactly one non-empty line: `06-01-task2`.
7. Update `.planning/STATE.md` with `phase=06` / `plan=06-01` / `task=2` / `status=implemented`.

## Section 69 — 06-sdk-contract-parity-and-pypi-release — 06-01 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-01-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Load research and make parity tests release-blocking.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: add regressions for new field acceptance/defaults and additive response serialization plus OpenAPI drift validation.
4. Run verify checks one by one: `docker compose exec backend uv run pytest src/backend/tests/api/test_agent_run.py src/backend/tests/sdk/test_runtime_config.py`; `./scripts/validate_openapi.sh`.
5. Do not mark complete until done condition is true: tests explicitly protect REL-03 parity ahead of release.
6. Write `.loop-commit-msg` with exactly one non-empty line: `06-01-task3`.
7. Update `.planning/STATE.md` with `phase=06` / `plan=06-01` / `task=3` / `status=implemented`.

## Section 70 — 06-sdk-contract-parity-and-pypi-release — 06-01 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-01-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Create `06-01-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `06-01-summary`.
3. Update `.planning/STATE.md` with `phase=06` / `plan=06-01` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `06-01-summary`.

## Section 71 — 06-sdk-contract-parity-and-pypi-release — 06-02 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-02-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Load phase research and keep `scripts/release_sdk.sh` as canonical gate.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: bump `agent-search-core` version and enforce strict tag/version alignment in release script.
4. Run verify checks one by one: `./scripts/release_sdk.sh`; run with intentionally wrong `RELEASE_TAG` and confirm mismatch failure.
5. Do not mark complete until done condition is true: release version updated and gating blocks mismatched metadata.
6. Write `.loop-commit-msg` with exactly one non-empty line: `06-02-task1`.
7. Update `.planning/STATE.md` with `phase=06` / `plan=06-02` / `task=1` / `status=implemented`.

## Section 72 — 06-sdk-contract-parity-and-pypi-release — 06-02 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-02-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Load research and preserve Trusted Publishing as sole CI publish path.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: align workflow to build/check before publish, publish downloaded validated artifacts only, and preserve dry-run path.
4. Run verify checks one by one: `rg -n "id-token: write|upload-artifact|download-artifact|gh-action-pypi-publish|Build and validate SDK artifacts" .github/workflows/release-sdk.yml`; `./scripts/release_sdk.sh`.
5. Do not mark complete until done condition is true: workflow+script enforce build-once/publish-once semantics.
6. Write `.loop-commit-msg` with exactly one non-empty line: `06-02-task2`.
7. Update `.planning/STATE.md` with `phase=06` / `plan=06-02` / `task=2` / `status=implemented`.

## Section 73 — 06-sdk-contract-parity-and-pypi-release — 06-02 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-02-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Load research and focus on installability evidence after publish.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: run clean-environment install/import proof for the newly published version.
4. Run verify checks one by one: `python3 -m venv /tmp/agent-search-core-release-check && source /tmp/agent-search-core-release-check/bin/activate && pip install --upgrade pip && pip install agent-search-core==<new_version> && python -c "import agent_search; print(agent_search.__file__)"`.
5. Do not mark complete until done condition is true: published package installs and imports in a clean environment.
6. Write `.loop-commit-msg` with exactly one non-empty line: `06-02-task3`.
7. Update `.planning/STATE.md` with `phase=06` / `plan=06-02` / `task=3` / `status=implemented`.

## Section 74 — 06-sdk-contract-parity-and-pypi-release — 06-02 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-02-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Create `06-02-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `06-02-summary`.
3. Update `.planning/STATE.md` with `phase=06` / `plan=06-02` / `task=summary` / `status=implemented`.
4. If this summary completes the phase, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `06-02-summary`.

## Section 75 — 06-sdk-contract-parity-and-pypi-release — 06-03 — Task 1 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-03-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Load phase research and keep migration guide canonical and implementation-aligned.
2. No phase context file exists for this phase.
3. Execute only Task 1 action: author migration guide with canonical fields, accepted aliases, default-safe behavior, and before/after request-response examples including `sub_answers` with `sub_qa` continuity.
4. Run verify checks one by one: `rg -n "HITL|runtime_config|custom_prompts|sub_answers|sub_qa|default" docs/migration-guide.md`.
5. Do not mark complete until done condition is true: migration guide provides exact adoption steps and compatibility expectations.
6. Write `.loop-commit-msg` with exactly one non-empty line: `06-03-task1`.
7. Update `.planning/STATE.md` with `phase=06` / `plan=06-03` / `task=1` / `status=implemented`.

## Section 76 — 06-sdk-contract-parity-and-pypi-release — 06-03 — Task 2 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-03-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Load research and align release notes with canonical field names.
2. No phase context file exists for this phase.
3. Execute only Task 2 action: publish dedicated release notes and update both SDK READMEs with executable examples for HITL/control/prompt options and additive sub-answer handling.
4. Run verify checks one by one: `rg -n "runtime_config|custom_prompts|sub_answers|sub_qa|pip install agent-search-core|release" docs/releases/1.0.3-sdk-contract-parity.md sdk/core/README.md sdk/python/README.md`.
5. Do not mark complete until done condition is true: release/SDK docs provide aligned adoption guidance.
6. Write `.loop-commit-msg` with exactly one non-empty line: `06-03-task2`.
7. Update `.planning/STATE.md` with `phase=06` / `plan=06-03` / `task=2` / `status=implemented`.

## Section 77 — 06-sdk-contract-parity-and-pypi-release — 06-03 — Task 3 (Execution)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-03-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Load research and ensure top-level discoverability consistency.
2. No phase context file exists for this phase.
3. Execute only Task 3 action: update root README entrypoints to migration/release docs and add concise compatibility checklist matching release artifacts.
4. Run verify checks one by one: `rg -n "migration guide|release notes|agent-search-core|compatibility|default-off" README.md`; validate markdown links resolve.
5. Do not mark complete until done condition is true: root docs route users correctly with no dead links/contradictions.
6. Write `.loop-commit-msg` with exactly one non-empty line: `06-03-task3`.
7. Update `.planning/STATE.md` with `phase=06` / `plan=06-03` / `task=3` / `status=implemented`.

## Section 78 — 06-sdk-contract-parity-and-pypi-release — 06-03 (Summary)
**Required inputs:**
- Plan file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-03-PLAN.md`
- Phase research file: `.planning/phases/06-sdk-contract-parity-and-pypi-release/06-RESEARCH.md`

**Steps:**
1. Create `06-03-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `06-03-summary`.
3. Update `.planning/STATE.md` with `phase=06` / `plan=06-03` / `task=summary` / `status=implemented`.
4. This summary can complete Phase 06; if so, update `.planning/ROADMAP.md` and `.planning/STATE.md`, keeping commit subject `06-03-summary`.
