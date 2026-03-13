Tasks are in **required implementation order** (1...n). Each section = one context window. Complete one section at a time.
Current section to work on: section 49. (move +1 after each turn)

## Summary Creation Instructions

Use this guide any time a section references `SUMMARY.md` creation.

### Ralph Loop Commit Contract

- The executor must **not** run `git commit` or `git push` directly.
- `.loop-commit-msg` must contain exactly one non-empty line.
- Implementation sections in this file must use exactly one commit subject format:
  - Task sections: `{phase}-{plan}-task{task-number}`
  - Summary sections: `{phase}-{plan}-summary`

### Purpose

- Execute a phase prompt (`PLAN.md`) and create the outcome summary (`SUMMARY.md`). 

### Required reading before writing

- Read `.planning/STATE.md` to load project context.
- Read `.planning/config.json` for planning behavior settings.

### How to create a good summary

1. Identify the plan and summary file path: `.planning/phases/XX-name/{phase}-{plan}-SUMMARY.md`. If there already exists a summary here then there is no need to re-create it. If it doesnt exist, do steps 2-9.
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

## Section 1 — 01-state-contract-foundation — 01-01 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/01-state-contract-foundation/01-01-PLAN.md`
- Phase research file: `.planning/phases/01-state-contract-foundation/01-RESEARCH.md`

**Steps**
1. Load `.planning/phases/01-state-contract-foundation/01-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: create canonical runtime `RAGState` with boundary adapters in `src/backend/agent_search/runtime/state.py`, preserving validated boundary models and mapping all graph channels into one canonical state contract.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest src/backend/tests/services/test_agent_service.py -k "graph_state or map_graph_state"`.
4. Do not mark this task complete until done condition is satisfied: canonical `RAGState` is the sole named runtime state contract and conversion functions preserve graph payload compatibility.
5. Write `.loop-commit-msg` with exactly one non-empty line: `01-01-task1`.
6. Update `.planning/STATE.md` with `phase=01-state-contract-foundation` / `plan=01-01` / `task=1` / `status=implemented`.

## Section 2 — 01-state-contract-foundation — 01-01 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/01-state-contract-foundation/01-01-PLAN.md`
- Phase research file: `.planning/phases/01-state-contract-foundation/01-RESEARCH.md`

**Steps**
1. Load `.planning/phases/01-state-contract-foundation/01-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: re-export `RAGState` through runtime and top-level SDK package entrypoints and add consumer-oriented import/contract tests in `src/backend/tests/sdk/test_rag_state_contract.py`.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_rag_state_contract.py`.
4. Do not mark this task complete until done condition is satisfied: SDK consumers can import `RAGState` from public exports without private-module shims.
5. Write `.loop-commit-msg` with exactly one non-empty line: `01-01-task2`.
6. Update `.planning/STATE.md` with `phase=01-state-contract-foundation` / `plan=01-01` / `task=2` / `status=implemented`.

## Section 3 — 01-state-contract-foundation — 01-01 (Summary)

**Required inputs**
- Plan file: `.planning/phases/01-state-contract-foundation/01-01-PLAN.md`
- Phase research file: `.planning/phases/01-state-contract-foundation/01-RESEARCH.md`

**Steps**
1. Create `.planning/phases/01-state-contract-foundation/01-01-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `01-01-summary`.

## Section 4 — 01-state-contract-foundation — 01-02 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/01-state-contract-foundation/01-02-PLAN.md`
- Phase research file: `.planning/phases/01-state-contract-foundation/01-RESEARCH.md`

**Steps**
1. Load `.planning/phases/01-state-contract-foundation/01-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: create authoritative node I/O registry in `src/backend/agent_search/runtime/node_contracts.py` mapping each runtime node to explicit input/output schemas with stable iteration helpers.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_node_contract_registry.py -k registry`.
4. Do not mark this task complete until done condition is satisfied: all graph nodes are represented in one explicit code-level contract mapping with stable lookup behavior.
5. Write `.loop-commit-msg` with exactly one non-empty line: `01-02-task1`.
6. Update `.planning/STATE.md` with `phase=01-state-contract-foundation` / `plan=01-02` / `task=1` / `status=implemented`.

## Section 5 — 01-state-contract-foundation — 01-02 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/01-state-contract-foundation/01-02-PLAN.md`
- Phase research file: `.planning/phases/01-state-contract-foundation/01-RESEARCH.md`

**Steps**
1. Load `.planning/phases/01-state-contract-foundation/01-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: create `docs/langgraph-node-io-contracts.md` and parity tests in `src/backend/tests/sdk/test_node_contract_registry.py` to enforce registry/docs synchronization.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_node_contract_registry.py`.
4. Do not mark this task complete until done condition is satisfied: node I/O schemas are discoverable via code/docs and drift is caught by automated checks.
5. Write `.loop-commit-msg` with exactly one non-empty line: `01-02-task2`.
6. Update `.planning/STATE.md` with `phase=01-state-contract-foundation` / `plan=01-02` / `task=2` / `status=implemented`.

## Section 6 — 01-state-contract-foundation — 01-02 (Summary)

**Required inputs**
- Plan file: `.planning/phases/01-state-contract-foundation/01-02-PLAN.md`
- Phase research file: `.planning/phases/01-state-contract-foundation/01-RESEARCH.md`

**Steps**
1. Create `.planning/phases/01-state-contract-foundation/01-02-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `01-02-summary`.

## Section 7 — 01-state-contract-foundation — 01-03 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/01-state-contract-foundation/01-03-PLAN.md`
- Phase research file: `.planning/phases/01-state-contract-foundation/01-RESEARCH.md`

**Steps**
1. Load `.planning/phases/01-state-contract-foundation/01-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: implement explicit reducer semantics in `src/backend/agent_search/runtime/reducers.py` and wire state-transition code to shared reducers instead of implicit merges.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest src/backend/tests/services/test_agent_service.py -k "apply_ or parallel_graph_runner or sequential_graph_runner"`.
4. Do not mark this task complete until done condition is satisfied: transition code delegates merge behavior to explicit reducers for all merge-sensitive channels.
5. Write `.loop-commit-msg` with exactly one non-empty line: `01-03-task1`.
6. Update `.planning/STATE.md` with `phase=01-state-contract-foundation` / `plan=01-03` / `task=1` / `status=implemented`.

## Section 8 — 01-state-contract-foundation — 01-03 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/01-state-contract-foundation/01-03-PLAN.md`
- Phase research file: `.planning/phases/01-state-contract-foundation/01-RESEARCH.md`

**Steps**
1. Load `.planning/phases/01-state-contract-foundation/01-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add deterministic repeat-run reducer/service tests and document reducer channel semantics in `docs/langgraph-reducer-semantics.md`.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest src/backend/tests/sdk/test_runtime_reducers.py src/backend/tests/services/test_agent_service.py -k "deterministic or reducer or graph_runner"`.
4. Do not mark this task complete until done condition is satisfied: reducer behavior is test-proven deterministic and documentation matches implementation/test semantics.
5. Write `.loop-commit-msg` with exactly one non-empty line: `01-03-task2`.
6. Update `.planning/STATE.md` with `phase=01-state-contract-foundation` / `plan=01-03` / `task=2` / `status=implemented`.

## Section 9 — 01-state-contract-foundation — 01-03 (Summary)

**Required inputs**
- Plan file: `.planning/phases/01-state-contract-foundation/01-03-PLAN.md`
- Phase research file: `.planning/phases/01-state-contract-foundation/01-RESEARCH.md`

**Steps**
1. Create `.planning/phases/01-state-contract-foundation/01-03-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `01-03-summary`.
3. Because this is the final plan in Phase 1, update roadmap/state completion markers in `.planning/ROADMAP.md` and `.planning/STATE.md` within this summary section flow.

## Section 10 — 02-durable-execution-and-identity-semantics — 02-01 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-01-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Load `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add durable execution schema/migration/models for run registry, checkpoint linkage, and idempotency ledger with indexable unique constraints.
3. Run verify checks one-by-one: `docker compose exec backend uv run alembic upgrade head` then `docker compose exec db psql -U agent_user -d agent_search -c "\dt"`.
4. Do not mark this task complete until done condition is satisfied: migration applies cleanly and durability tables exist with replay-safe lookup constraints.
5. Write `.loop-commit-msg` with exactly one non-empty line: `02-01-task1`.
6. Update `.planning/STATE.md` with `phase=02-durable-execution-and-identity-semantics` / `plan=02-01` / `task=1` / `status=implemented`.

## Section 11 — 02-durable-execution-and-identity-semantics — 02-01 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-01-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Load `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: implement `src/backend/agent_search/runtime/persistence.py` checkpointer lifecycle helpers to bootstrap and return ready PostgresSaver-backed graph compilation utilities.
3. Run verify checks one-by-one: `docker compose exec backend uv run python -c "from agent_search.runtime.persistence import ensure_checkpointer_bootstrap; ensure_checkpointer_bootstrap()"`.
4. Do not mark this task complete until done condition is satisfied: runtime can initialize PostgresSaver tables and return a ready checkpointer without manual SQL.
5. Write `.loop-commit-msg` with exactly one non-empty line: `02-01-task2`.
6. Update `.planning/STATE.md` with `phase=02-durable-execution-and-identity-semantics` / `plan=02-01` / `task=2` / `status=implemented`.

## Section 12 — 02-durable-execution-and-identity-semantics — 02-01 — Task 3 (Execution)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-01-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Load `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: implement deterministic thread identity policy in `execution_identity.py` and regression tests for validation/mint/resolve behavior.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/runtime/test_execution_identity.py`.
4. Do not mark this task complete until done condition is satisfied: same run lineage resolves stable thread IDs and invalid identities fail fast with explicit errors.
5. Write `.loop-commit-msg` with exactly one non-empty line: `02-01-task3`.
6. Update `.planning/STATE.md` with `phase=02-durable-execution-and-identity-semantics` / `plan=02-01` / `task=3` / `status=implemented`.

## Section 13 — 02-durable-execution-and-identity-semantics — 02-01 (Summary)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-01-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Create `.planning/phases/02-durable-execution-and-identity-semantics/02-01-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `02-01-summary`.

## Section 14 — 02-durable-execution-and-identity-semantics — 02-02 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-02-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Load `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: extend API request/response contracts and FastAPI routes to carry optional/provided canonical `thread_id` across sync and async run flows.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/api/test_agent_run.py -k "run_async or run_status or run"`.
4. Do not mark this task complete until done condition is satisfied: API accepts optional `thread_id`, returns canonical `thread_id`, and tests validate stable identity fields.
5. Write `.loop-commit-msg` with exactly one non-empty line: `02-02-task1`.
6. Update `.planning/STATE.md` with `phase=02-durable-execution-and-identity-semantics` / `plan=02-02` / `task=1` / `status=implemented`.

## Section 15 — 02-durable-execution-and-identity-semantics — 02-02 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-02-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Load `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: propagate `thread_id` through SDK/public API/runtime jobs status lifecycle without regenerating IDs on retries or resumes.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/sdk/test_public_api_async.py`.
4. Do not mark this task complete until done condition is satisfied: SDK/API/runtime job status agree on one stable thread ID per run lineage.
5. Write `.loop-commit-msg` with exactly one non-empty line: `02-02-task2`.
6. Update `.planning/STATE.md` with `phase=02-durable-execution-and-identity-semantics` / `plan=02-02` / `task=2` / `status=implemented`.

## Section 16 — 02-durable-execution-and-identity-semantics — 02-02 — Task 3 (Execution)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-02-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Load `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add API/SDK thread-identity regressions for provided ID preservation, server-generated IDs, status continuity, and invalid format handling.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/api/test_agent_run.py tests/sdk/test_public_api_async.py`.
4. Do not mark this task complete until done condition is satisfied: thread identity contract is covered by happy-path and invalid-input tests across API/SDK layers.
5. Write `.loop-commit-msg` with exactly one non-empty line: `02-02-task3`.
6. Update `.planning/STATE.md` with `phase=02-durable-execution-and-identity-semantics` / `plan=02-02` / `task=3` / `status=implemented`.

## Section 17 — 02-durable-execution-and-identity-semantics — 02-02 (Summary)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-02-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Create `.planning/phases/02-durable-execution-and-identity-semantics/02-02-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `02-02-summary`.

## Section 18 — 02-durable-execution-and-identity-semantics — 02-03 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-03-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Load `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: wire checkpoint-backed graph execution/resume entrypoints with `Command(resume=...)` and strict valid-transition enforcement for pause/resume paths.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/sdk/test_sdk_async_e2e.py -k "resume or pause or interrupt"`.
4. Do not mark this task complete until done condition is satisfied: interrupted runs resume from persisted checkpoints with same thread ID and invalid resume transitions are rejected deterministically.
5. Write `.loop-commit-msg` with exactly one non-empty line: `02-03-task1`.
6. Update `.planning/STATE.md` with `phase=02-durable-execution-and-identity-semantics` / `plan=02-03` / `task=1` / `status=implemented`.

## Section 19 — 02-durable-execution-and-identity-semantics — 02-03 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-03-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Load `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add durable idempotency ledger gating side effects by `(thread_id, node_name, effect_key)` and replay recorded outcomes instead of reapplying effects.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/services/test_agent_service.py -k "idempot or replay or retry"`.
4. Do not mark this task complete until done condition is satisfied: replay/retry reuses recorded side-effect outcomes and avoids duplicate external actions.
5. Write `.loop-commit-msg` with exactly one non-empty line: `02-03-task2`.
6. Update `.planning/STATE.md` with `phase=02-durable-execution-and-identity-semantics` / `plan=02-03` / `task=2` / `status=implemented`.

## Section 20 — 02-durable-execution-and-identity-semantics — 02-03 — Task 3 (Execution)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-03-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Load `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add integration resilience coverage for checkpoint resume, identity continuity, idempotent replay, and valid/invalid HITL pause-resume transition matrix.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/sdk/test_sdk_async_e2e.py tests/services/test_agent_service.py tests/api/test_agent_run.py`.
4. Do not mark this task complete until done condition is satisfied: automated tests prove all Phase 2 success criteria (REL-01..REL-04).
5. Write `.loop-commit-msg` with exactly one non-empty line: `02-03-task3`.
6. Update `.planning/STATE.md` with `phase=02-durable-execution-and-identity-semantics` / `plan=02-03` / `task=3` / `status=implemented`.

## Section 21 — 02-durable-execution-and-identity-semantics — 02-03 (Summary)

**Required inputs**
- Plan file: `.planning/phases/02-durable-execution-and-identity-semantics/02-03-PLAN.md`
- Phase research file: `.planning/phases/02-durable-execution-and-identity-semantics/02-RESEARCH.md`

**Steps**
1. Create `.planning/phases/02-durable-execution-and-identity-semantics/02-03-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `02-03-summary`.
3. Because this is the final plan in Phase 2, update roadmap/state completion markers in `.planning/ROADMAP.md` and `.planning/STATE.md` within this summary section flow.

## Section 22 — 03-end-to-end-langgraph-rag-cutover — 03-01 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-01-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Load `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add direct LangGraph dependencies and create `runtime/graph` package modules for state/routes/builder/execution, keeping existing node logic unchanged.
3. Run verify checks one-by-one: `docker compose exec backend uv run python -c "from agent_search.runtime.graph.builder import build_runtime_graph; print(callable(build_runtime_graph))"`.
4. Do not mark this task complete until done condition is satisfied: dependency manifest includes required packages and graph modules import cleanly in containerized backend runtime.
5. Write `.loop-commit-msg` with exactly one non-empty line: `03-01-task1`.
6. Update `.planning/STATE.md` with `phase=03-end-to-end-langgraph-rag-cutover` / `plan=03-01` / `task=1` / `status=implemented`.

## Section 23 — 03-end-to-end-langgraph-rag-cutover — 03-01 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-01-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Load `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: implement compiled `StateGraph` lifecycle wiring (START/END, nodes, `Send` fan-out, deterministic reducers, `RetryPolicy`) and one execution entrypoint.
3. Run verify checks one-by-one: `docker compose exec backend uv run python -c "from agent_search.runtime.graph.execution import execute_runtime_graph; print(callable(execute_runtime_graph))"`.
4. Do not mark this task complete until done condition is satisfied: compiled graph builds/invokes via a single entrypoint with explicit node/edge/retry definitions for full lifecycle.
5. Write `.loop-commit-msg` with exactly one non-empty line: `03-01-task2`.
6. Update `.planning/STATE.md` with `phase=03-end-to-end-langgraph-rag-cutover` / `plan=03-01` / `task=2` / `status=implemented`.

## Section 24 — 03-end-to-end-langgraph-rag-cutover — 03-01 — Task 3 (Execution)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-01-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Load `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add focused orchestration tests for graph compile contract, route fan-out behavior, and deterministic fan-in ordering.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/services/test_agent_service.py -k "graph or langgraph or runner"`.
4. Do not mark this task complete until done condition is satisfied: tests prove compiled graph is callable and deterministic without custom thread-pool orchestration assumptions.
5. Write `.loop-commit-msg` with exactly one non-empty line: `03-01-task3`.
6. Update `.planning/STATE.md` with `phase=03-end-to-end-langgraph-rag-cutover` / `plan=03-01` / `task=3` / `status=implemented`.

## Section 25 — 03-end-to-end-langgraph-rag-cutover — 03-01 (Summary)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-01-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Create `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-01-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `03-01-summary`.

## Section 26 — 03-end-to-end-langgraph-rag-cutover — 03-02 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-02-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Load `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: refactor sync runtime runner delegation to compiled graph execution while preserving request/response contracts and tracing hooks.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/sdk/test_sdk_run_e2e.py -k "runtime_runner or sync"`.
4. Do not mark this task complete until done condition is satisfied: sync production path executes through compiled graph runtime without default reliance on legacy orchestrator.
5. Write `.loop-commit-msg` with exactly one non-empty line: `03-02-task1`.
6. Update `.planning/STATE.md` with `phase=03-end-to-end-langgraph-rag-cutover` / `plan=03-02` / `task=1` / `status=implemented`.

## Section 27 — 03-end-to-end-langgraph-rag-cutover — 03-02 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-02-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Load `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: cut over async jobs to the shared compiled graph runtime while preserving existing job status/cancel API contracts.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/sdk/test_sdk_async_e2e.py -k "async or run_status"`.
4. Do not mark this task complete until done condition is satisfied: async run path is graph-native and lifecycle contract remains consumer-compatible.
5. Write `.loop-commit-msg` with exactly one non-empty line: `03-02-task2`.
6. Update `.planning/STATE.md` with `phase=03-end-to-end-langgraph-rag-cutover` / `plan=03-02` / `task=2` / `status=implemented`.

## Section 28 — 03-end-to-end-langgraph-rag-cutover — 03-02 — Task 3 (Execution)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-02-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Load `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add cutover regression tests that fail if sync/async paths fall back to `run_parallel_graph_runner`.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/sdk/test_sdk_run_e2e.py tests/sdk/test_sdk_async_e2e.py`.
4. Do not mark this task complete until done condition is satisfied: tests enforce graph-native runtime path and reject accidental legacy orchestration fallback.
5. Write `.loop-commit-msg` with exactly one non-empty line: `03-02-task3`.
6. Update `.planning/STATE.md` with `phase=03-end-to-end-langgraph-rag-cutover` / `plan=03-02` / `task=3` / `status=implemented`.

## Section 29 — 03-end-to-end-langgraph-rag-cutover — 03-02 (Summary)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-02-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Create `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-02-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `03-02-summary`.

## Section 30 — 03-end-to-end-langgraph-rag-cutover — 03-03 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-03-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Load `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: expand API/SDK contract tests to validate full lifecycle behavior and production response contract integrity under LangGraph orchestration.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/api/test_agent_run.py tests/sdk/test_public_api.py tests/sdk/test_public_api_async.py`.
4. Do not mark this task complete until done condition is satisfied: API/SDK contract tests pass and confirm cutover preserves response structure/quality guardrails.
5. Write `.loop-commit-msg` with exactly one non-empty line: `03-03-task1`.
6. Update `.planning/STATE.md` with `phase=03-end-to-end-langgraph-rag-cutover` / `plan=03-03` / `task=1` / `status=implemented`.

## Section 31 — 03-end-to-end-langgraph-rag-cutover — 03-03 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-03-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Load `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add anti-regression tests (monkeypatch/sentinel guards) that fail if legacy orchestrator functions are invoked by sync/async production paths.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest tests/services/test_agent_service.py tests/sdk/test_public_api.py tests/sdk/test_public_api_async.py -k "legacy or orchestration or cutover"`.
4. Do not mark this task complete until done condition is satisfied: suite explicitly blocks fallback to legacy orchestration for v1 mainline completion.
5. Write `.loop-commit-msg` with exactly one non-empty line: `03-03-task2`.
6. Update `.planning/STATE.md` with `phase=03-end-to-end-langgraph-rag-cutover` / `plan=03-03` / `task=2` / `status=implemented`.

## Section 32 — 03-end-to-end-langgraph-rag-cutover — 03-03 — Task 3 (Execution)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-03-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Load `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: run containerized backend cutover validation suite and resolve failures before completion.
3. Run verify checks one-by-one: `docker compose restart backend` then `docker compose exec backend uv run pytest tests/api/test_agent_run.py tests/sdk/test_sdk_run_e2e.py tests/sdk/test_sdk_async_e2e.py tests/contracts/test_public_contracts.py`.
4. Do not mark this task complete until done condition is satisfied: containerized validation confirms cutover is production-ready, contract-stable, and legacy-main-path-free.
5. Write `.loop-commit-msg` with exactly one non-empty line: `03-03-task3`.
6. Update `.planning/STATE.md` with `phase=03-end-to-end-langgraph-rag-cutover` / `plan=03-03` / `task=3` / `status=implemented`.

## Section 33 — 03-end-to-end-langgraph-rag-cutover — 03-03 (Summary)

**Required inputs**
- Plan file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-03-PLAN.md`
- Phase research file: `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-RESEARCH.md`

**Steps**
1. Create `.planning/phases/03-end-to-end-langgraph-rag-cutover/03-03-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `03-03-summary`.
3. Because this is the final plan in Phase 3, update roadmap/state completion markers in `.planning/ROADMAP.md` and `.planning/STATE.md` within this summary section flow.

## Section 34 — 04-observability-and-remote-runtime-validation — 04-01 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/04-observability-and-remote-runtime-validation/04-01-PLAN.md`
- Phase research file: `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md`

**Steps**
1. Load `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: implement canonical lifecycle event envelope with monotonic event IDs and ordered emissions from start through retries/recovery to terminal states using LangGraph-native signals.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest src/backend/tests/runtime -k "lifecycle or event"`.
4. Do not mark this task complete until done condition is satisfied: one deterministic lifecycle event builder emits ordered events correlated by run/thread/trace identity.
5. Write `.loop-commit-msg` with exactly one non-empty line: `04-01-task1`.
6. Update `.planning/STATE.md` with `phase=04-observability-and-remote-runtime-validation` / `plan=04-01` / `task=1` / `status=implemented`.

## Section 35 — 04-observability-and-remote-runtime-validation — 04-01 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/04-observability-and-remote-runtime-validation/04-01-PLAN.md`
- Phase research file: `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md`

**Steps**
1. Load `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: expose SSE lifecycle stream endpoint with `Last-Event-ID` reconnect safety and payload parity with canonical lifecycle contract.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest src/backend/tests/api/test_run_events_stream.py`.
4. Do not mark this task complete until done condition is satisfied: operators can observe ordered start-to-terminal lifecycle with reconnect-safe continuity.
5. Write `.loop-commit-msg` with exactly one non-empty line: `04-01-task2`.
6. Update `.planning/STATE.md` with `phase=04-observability-and-remote-runtime-validation` / `plan=04-01` / `task=2` / `status=implemented`.

## Section 36 — 04-observability-and-remote-runtime-validation — 04-01 (Summary)

**Required inputs**
- Plan file: `.planning/phases/04-observability-and-remote-runtime-validation/04-01-PLAN.md`
- Phase research file: `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md`

**Steps**
1. Create `.planning/phases/04-observability-and-remote-runtime-validation/04-01-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `04-01-summary`.

## Section 37 — 04-observability-and-remote-runtime-validation — 04-02 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/04-observability-and-remote-runtime-validation/04-02-PLAN.md`
- Phase research file: `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md`

**Steps**
1. Load `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: standardize correlation tuple propagation (`run_id`, `thread_id`, `trace_id`) across runtime, tracing utilities, and lifecycle events with consistent metadata keys.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest src/backend/tests/runtime -k "trace or correlation"`.
4. Do not mark this task complete until done condition is satisfied: runtime/tracing enforce one stable tuple for node and terminal observations.
5. Write `.loop-commit-msg` with exactly one non-empty line: `04-02-task1`.
6. Update `.planning/STATE.md` with `phase=04-observability-and-remote-runtime-validation` / `plan=04-02` / `task=1` / `status=implemented`.

## Section 38 — 04-observability-and-remote-runtime-validation — 04-02 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/04-observability-and-remote-runtime-validation/04-02-PLAN.md`
- Phase research file: `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md`

**Steps**
1. Load `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add correlation joinability tests covering successful and failure paths across runtime/API metadata surfaces.
3. Run verify checks one-by-one: `docker compose exec backend uv run pytest src/backend/tests/runtime/test_trace_correlation.py src/backend/tests/api/test_trace_metadata_contract.py`.
4. Do not mark this task complete until done condition is satisfied: tests fail if any path drops/mutates `run_id`, `thread_id`, or `trace_id`.
5. Write `.loop-commit-msg` with exactly one non-empty line: `04-02-task2`.
6. Update `.planning/STATE.md` with `phase=04-observability-and-remote-runtime-validation` / `plan=04-02` / `task=2` / `status=implemented`.

## Section 39 — 04-observability-and-remote-runtime-validation — 04-02 (Summary)

**Required inputs**
- Plan file: `.planning/phases/04-observability-and-remote-runtime-validation/04-02-PLAN.md`
- Phase research file: `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md`

**Steps**
1. Create `.planning/phases/04-observability-and-remote-runtime-validation/04-02-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `04-02-summary`.

## Section 40 — 04-observability-and-remote-runtime-validation — 04-03 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/04-observability-and-remote-runtime-validation/04-03-PLAN.md`
- Phase research file: `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md`

**Steps**
1. Load `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: implement remote validation scripts for Compose and fresh pip SDK environments, asserting health, full E2E query run, lifecycle streaming visibility, and run/thread/trace evidence capture.
3. Run verify checks one-by-one: `bash scripts/validation/phase4_remote_compose.sh` then `bash scripts/validation/phase4_remote_sdk.sh`.
4. Do not mark this task complete until done condition is satisfied: both scripts return zero only after full run + stream + correlation checks pass.
5. Write `.loop-commit-msg` with exactly one non-empty line: `04-03-task1`.
6. Update `.planning/STATE.md` with `phase=04-observability-and-remote-runtime-validation` / `plan=04-03` / `task=1` / `status=implemented`.

## Section 41 — 04-observability-and-remote-runtime-validation — 04-03 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/04-observability-and-remote-runtime-validation/04-03-PLAN.md`
- Phase research file: `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md`

**Steps**
1. Load `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: implement evidence collector and persist `.planning/phases/04-observability-and-remote-runtime-validation/04-VALIDATION-MATRIX.md` with criteria-level PASS/FAIL and evidence links/identifiers.
3. Run verify checks one-by-one: `python scripts/validation/phase4_collect_artifacts.py` then `rg "remote-compose|pip-sdk|PASS|run_id|thread_id|trace_id" .planning/phases/04-observability-and-remote-runtime-validation/04-VALIDATION-MATRIX.md`.
4. Do not mark this task complete until done condition is satisfied: matrix exists with explicit PASS/FAIL for both required environments and evidence-backed lifecycle/correlation checks.
5. Write `.loop-commit-msg` with exactly one non-empty line: `04-03-task2`.
6. Update `.planning/STATE.md` with `phase=04-observability-and-remote-runtime-validation` / `plan=04-03` / `task=2` / `status=implemented`.

## Section 42 — 04-observability-and-remote-runtime-validation — 04-03 (Summary)

**Required inputs**
- Plan file: `.planning/phases/04-observability-and-remote-runtime-validation/04-03-PLAN.md`
- Phase research file: `.planning/phases/04-observability-and-remote-runtime-validation/04-RESEARCH.md`

**Steps**
1. Create `.planning/phases/04-observability-and-remote-runtime-validation/04-03-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `04-03-summary`.
3. Because this is the final plan in Phase 4, update roadmap/state completion markers in `.planning/ROADMAP.md` and `.planning/STATE.md` within this summary section flow.

## Section 43 — 05-major-release-and-migration-documentation — 05-01 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-01-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Load `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: set `agent-search-core` major version to `1.0.0` in `sdk/core/pyproject.toml` while preserving release metadata consistency.
3. Run verify checks one-by-one: `rg "version = \"1\\.0\\.0\"" sdk/core/pyproject.toml`.
4. Do not mark this task complete until done condition is satisfied: `sdk/core/pyproject.toml` declares `1.0.0` and remains build-tool parseable.
5. Write `.loop-commit-msg` with exactly one non-empty line: `05-01-task1`.
6. Update `.planning/STATE.md` with `phase=05-major-release-and-migration-documentation` / `plan=05-01` / `task=1` / `status=implemented`.

## Section 44 — 05-major-release-and-migration-documentation — 05-01 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-01-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Load `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: author `docs/releases/1.0.0-langgraph-migration.md` with SemVer-explicit scope, breaking changes, migration prerequisites, guide/deprecation links, and release-candidate checklist.
3. Run verify checks one-by-one: `rg "release-candidate checklist|Breaking|Migration Guide|Deprecation Map" docs/releases/1.0.0-langgraph-migration.md`.
4. Do not mark this task complete until done condition is satisfied: release notes are publish-ready with migration/deprecation clarity and pre-publish checklist.
5. Write `.loop-commit-msg` with exactly one non-empty line: `05-01-task2`.
6. Update `.planning/STATE.md` with `phase=05-major-release-and-migration-documentation` / `plan=05-01` / `task=2` / `status=implemented`.

## Section 45 — 05-major-release-and-migration-documentation — 05-01 — Task 3 (Execution)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-01-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Load `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add root README release section linking `1.0.0` release notes and migration docs for immediate discoverability.
3. Run verify checks one-by-one: `rg "1\\.0\\.0|release notes|migration" README.md`.
4. Do not mark this task complete until done condition is satisfied: README clearly links release and migration documentation for v1 adopters.
5. Write `.loop-commit-msg` with exactly one non-empty line: `05-01-task3`.
6. Update `.planning/STATE.md` with `phase=05-major-release-and-migration-documentation` / `plan=05-01` / `task=3` / `status=implemented`.

## Section 46 — 05-major-release-and-migration-documentation — 05-01 (Summary)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-01-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Create `.planning/phases/05-major-release-and-migration-documentation/05-01-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `05-01-summary`.

## Section 47 — 05-major-release-and-migration-documentation — 05-02 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-02-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Load `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: write `docs/migration-guide.md` with concrete legacy-to-LangGraph mapping, stepwise migration flow, and command-level verification per step.
3. Run verify checks one-by-one: `rg "Step|Verify|legacy|LangGraph|mapping" docs/migration-guide.md`.
4. Do not mark this task complete until done condition is satisfied: migration guide includes actionable sequence, mapping table, and testable verification commands.
5. Write `.loop-commit-msg` with exactly one non-empty line: `05-02-task1`.
6. Update `.planning/STATE.md` with `phase=05-major-release-and-migration-documentation` / `plan=05-02` / `task=1` / `status=implemented`.

## Section 48 — 05-major-release-and-migration-documentation — 05-02 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-02-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Load `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: create explicit `docs/deprecation-map.md` with deprecated flows, replacement paths, support status, and removal horizon semantics.
3. Run verify checks one-by-one: `rg "Deprecated|Replacement|Removal|Status" docs/deprecation-map.md`.
4. Do not mark this task complete until done condition is satisfied: deprecation map clearly defines status/timeline and operational meaning of removals.
5. Write `.loop-commit-msg` with exactly one non-empty line: `05-02-task2`.
6. Update `.planning/STATE.md` with `phase=05-major-release-and-migration-documentation` / `plan=05-02` / `task=2` / `status=implemented`.

## Section 49 — 05-major-release-and-migration-documentation — 05-02 — Task 3 (Execution)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-02-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Load `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: add migration/deprecation callout section near top of `sdk/README.md` linking both docs with concise action-oriented guidance.
3. Run verify checks one-by-one: `rg "Migration|deprecation-map|migration-guide" sdk/README.md`.
4. Do not mark this task complete until done condition is satisfied: SDK docs entrypoint clearly surfaces migration and deprecation artifacts.
5. Write `.loop-commit-msg` with exactly one non-empty line: `05-02-task3`.
6. Update `.planning/STATE.md` with `phase=05-major-release-and-migration-documentation` / `plan=05-02` / `task=3` / `status=implemented`.

## Section 50 — 05-major-release-and-migration-documentation — 05-02 (Summary)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-02-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Create `.planning/phases/05-major-release-and-migration-documentation/05-02-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `05-02-summary`.

## Section 51 — 05-major-release-and-migration-documentation — 05-03 — Task 1 (Execution)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-03-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Load `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: regenerate canonical `openapi.json` and align generated `sdk/python/README.md` references using script-driven flow to avoid manual drift.
3. Run verify checks one-by-one: `uv run --project src/backend python scripts/export_openapi.py --output openapi.json` then `./scripts/validate_openapi.sh`.
4. Do not mark this task complete until done condition is satisfied: committed OpenAPI artifact matches runtime export and generated docs are in sync.
5. Write `.loop-commit-msg` with exactly one non-empty line: `05-03-task1`.
6. Update `.planning/STATE.md` with `phase=05-major-release-and-migration-documentation` / `plan=05-03` / `task=1` / `status=implemented`.

## Section 52 — 05-major-release-and-migration-documentation — 05-03 — Task 2 (Execution)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-03-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Load `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: update `docs/application-documentation.html` architecture/runtime flow content for LangGraph-first correctness and migration-aware guidance.
3. Run verify checks one-by-one: `rg "LangGraph|state graph|migration|runtime" docs/application-documentation.html`.
4. Do not mark this task complete until done condition is satisfied: application docs accurately describe migrated architecture and operational behavior.
5. Write `.loop-commit-msg` with exactly one non-empty line: `05-03-task2`.
6. Update `.planning/STATE.md` with `phase=05-major-release-and-migration-documentation` / `plan=05-03` / `task=2` / `status=implemented`.

## Section 53 — 05-major-release-and-migration-documentation — 05-03 — Task 3 (Execution)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-03-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Load `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md` and use it as reference while executing this task.
2. Execute only this task action: refresh `sdk/examples/run_health.py` usability for base URL selection and failure logging while preserving endpoint semantics.
3. Run verify checks one-by-one: `python sdk/examples/run_health.py --base-url http://localhost:8000`.
4. Do not mark this task complete until done condition is satisfied: example executes against healthy service and remains aligned with documented SDK flow.
5. Write `.loop-commit-msg` with exactly one non-empty line: `05-03-task3`.
6. Update `.planning/STATE.md` with `phase=05-major-release-and-migration-documentation` / `plan=05-03` / `task=3` / `status=implemented`.

## Section 54 — 05-major-release-and-migration-documentation — 05-03 (Summary)

**Required inputs**
- Plan file: `.planning/phases/05-major-release-and-migration-documentation/05-03-PLAN.md`
- Phase research file: `.planning/phases/05-major-release-and-migration-documentation/05-RESEARCH.md`

**Steps**
1. Create `.planning/phases/05-major-release-and-migration-documentation/05-03-SUMMARY.md` by following `## Summary Creation Instructions` in this file.
2. Write `.loop-commit-msg` with exactly one non-empty line: `05-03-summary`.
3. Because this is the final plan in Phase 5, update roadmap/state completion markers in `.planning/ROADMAP.md` and `.planning/STATE.md` within this summary section flow.
