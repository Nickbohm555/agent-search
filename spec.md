## Section 1: Benchmark charter - success criteria and non-goals

**Single goal:** Define the benchmark’s v1 objective contract so all later sections implement against one fixed target.

**Details:**
- Primary KPI is `correctness`; secondary KPI is `latency`.
- v1 pass threshold is `correctness >= 0.75` and `p95 latency <= 30,000 ms`.
- v1 is manual-only execution; no CI, cron, or auto-trigger requirements.
- v1 corpus scope is public data only.
- Cost is tracked but not used as a pass/fail gate.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| spec.md | Canonical benchmark charter and fixed v1 constraints. |
| src/backend/schemas/benchmark.py | Add objective schema (`BenchmarkTargets`) used by APIs and UI. |

**How to test:**
- Unit test schema defaults and threshold serialization.
- Manual: run benchmark status endpoint and verify thresholds are present.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 2: Benchmark runtime configuration - environment-backed settings

**Single goal:** Add one centralized benchmark configuration layer so runtime behavior is explicit and reproducible.

**Details:**
- Define env-backed settings for thresholds, default dataset version, timeout caps, and judge model name.
- Store an execution context fingerprint derived from key settings and model names.
- Use existing OpenAI key in project environment for all benchmark LLM calls.
- Keep config names compatible with SDK runtime config introduced in implementation plan section 7.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): optional `.env.example` additions only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/config.py | Central benchmark settings and defaults. |
| .env.example | Document benchmark-related env vars. |
| src/backend/tests/utils/test_benchmark_config.py | Validate settings parsing and fallback behavior. |

**How to test:**
- `docker compose exec backend uv run pytest src/backend/tests/utils/test_benchmark_config.py`.
- Manual: restart backend and confirm settings are loaded.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 3: Internal dataset contract - DeepResearchBench-aligned JSONL schema

**Single goal:** Define one strict internal question schema compatible with DeepResearchBench concepts.

**Details:**
- Required fields: `question_id`, `question`, `domain`, `difficulty`, `expected_answer_points`, `required_sources`, `disallowed_behaviors`.
- v1 target dataset size is 120 public questions.
- Difficulty distribution is fixed: 40 easy, 50 medium, 30 hard.
- This section defines schema and validators only.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/benchmarks/datasets/schema.md | Human-readable contract for dataset records. |
| src/backend/benchmarks/datasets/internal_v1/questions.jsonl | Canonical v1 dataset file. |
| src/backend/tests/benchmarks/test_dataset_schema.py | Validate required fields and distribution constraints. |

**How to test:**
- `docker compose exec backend uv run pytest src/backend/tests/benchmarks/test_dataset_schema.py`.
- Manual: run schema validator against dataset JSONL and verify 120 valid entries.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 4: Dataset curation workflow - reproducible authoring and review

**Single goal:** Implement one repeatable workflow to generate, review, and freeze internal benchmark datasets.

**Details:**
- Generate candidate questions from public corpora using OpenAI via existing project key.
- Require human review and approval before inclusion.
- Persist provenance: source URLs, generator prompt version, reviewer, review timestamp.
- Output immutable dataset versions (`internal_v1`, `internal_v1.1`, etc.).

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): optional `typer`; argparse acceptable.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/benchmarks/tools/generate_questions.py | Candidate question generation tool. |
| src/backend/benchmarks/tools/review_queue.py | Human review state transitions and approvals. |
| src/backend/benchmarks/datasets/internal_v1/provenance.jsonl | Provenance and review metadata ledger. |

**How to test:**
- Unit tests for review-state transitions and export behavior.
- Manual: generate candidates, approve subset, export reviewed set.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 5: Benchmark corpus fixture - deterministic source loading

**Single goal:** Add one deterministic corpus loading workflow so benchmark runs always execute against the same indexed content.

**Details:**
- Define a benchmark corpus manifest mapping question domains to public source documents.
- Provide load/reset commands that repopulate `internal_documents` and `internal_document_chunks` in a deterministic order.
- Persist a corpus version hash and attach it to every benchmark run.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): uses existing internal data load/wipe capabilities.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/benchmarks/corpus/internal_v1_manifest.json | Canonical corpus source manifest. |
| src/backend/benchmarks/tools/load_corpus.py | Deterministic corpus load/reset utility. |
| src/backend/tests/benchmarks/test_corpus_loader.py | Validate deterministic load behavior and hash generation. |

**How to test:**
- Run corpus loader twice and verify identical corpus hash and chunk counts.
- Manual: query DB to confirm expected document totals after reset.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 6: Benchmark database foundation - run metadata tables

**Single goal:** Add one persistent run metadata model so each benchmark execution is traceable.

**Details:**
- Create `benchmark_runs` table for run lifecycle and SLO snapshot.
- Create `benchmark_run_modes` table for selected mode list and immutable config snapshot.
- Include context fingerprint and corpus hash columns for reproducibility.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration required.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/models.py | SQLAlchemy models for run metadata entities. |
| src/backend/alembic/versions/002_add_benchmark_run_metadata_tables.py | Migration for run metadata tables. |
| src/backend/tests/db/test_benchmark_run_metadata_schema.py | DB schema and constraint tests. |

**How to test:**
- `docker compose exec backend uv run alembic upgrade head`.
- `docker compose exec db psql -U agent_user -d agent_search -c "\\dt"` shows new tables.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 7: Benchmark database outputs - per-question result tables

**Single goal:** Add one persistent result model for per-question/per-mode outputs.

**Details:**
- Create `benchmark_results` table keyed by `(run_id, mode, question_id)`.
- Persist answer payload, citations payload, latency, token usage, and execution error class.
- This section excludes judge and retrieval detail tables.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration required.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/models.py | Add `BenchmarkResult` ORM model. |
| src/backend/alembic/versions/003_add_benchmark_results_table.py | Migration for per-question result table. |
| src/backend/tests/db/test_benchmark_results_schema.py | Constraint and insert tests for results table. |

**How to test:**
- Apply migration and insert synthetic row through tests.
- Manual: verify new row appears after a partial benchmark run.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 8: Evaluation mode registry - deterministic mode definitions

**Single goal:** Implement one explicit mode registry so all benchmark comparisons use stable mode semantics.

**Details:**
- v1 modes: `baseline_retrieve_then_answer`, `agentic_default`, `agentic_no_rerank`, `agentic_single_query_no_decompose`.
- Mode definitions include parameter overrides and a stable version string.
- Registry rejects unknown modes at request validation time.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/benchmark_modes.py | Source of truth for mode definitions and overrides. |
| src/backend/schemas/benchmark.py | Mode enums and request validation models. |
| src/backend/tests/services/test_benchmark_modes.py | Validate mode registry behavior. |

**How to test:**
- `docker compose exec backend uv run pytest src/backend/tests/services/test_benchmark_modes.py`.
- Manual: send invalid mode and verify 4xx response.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 9: Benchmark runner core - synchronous evaluation service

**Single goal:** Build one core runner service that executes dataset questions across selected modes and persists raw outputs.

**Details:**
- Load dataset by version and iterate `(mode x question)` combinations.
- Call `agent_search.public_api` sync entrypoint as the execution boundary (compatible with implementation plan sections 2, 8, 15, and 19).
- Persist `benchmark_results` rows incrementally so partial progress survives interruptions.
- Validate run-context fingerprint and corpus hash before execution starts.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/benchmark_runner.py | Core execution loop and persistence writes. |
| src/backend/tests/services/test_benchmark_runner.py | Verify question/mode iteration and persistence behavior. |

**How to test:**
- Run service tests with mocked agent responses.
- Manual: execute runner directly for a smoke dataset.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 10: Benchmark job orchestration API - manual run lifecycle endpoints

**Single goal:** Expose one manual API workflow to start, monitor, list, and cancel benchmark runs.

**Details:**
- Endpoints required: `POST /api/benchmarks/runs`, `GET /api/benchmarks/runs`, `GET /api/benchmarks/runs/{run_id}`, `POST /api/benchmarks/runs/{run_id}/cancel`.
- Use async job pattern consistent with existing `agent_jobs` design.
- Async execution calls SDK async lifecycle APIs (`run_async`, `get_run_status`, `cancel_run`) once implementation plan sections 3, 16, and 18 are merged.
- Persist status transitions into `benchmark_runs` lifecycle fields.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/routers/benchmarks.py | Benchmark lifecycle endpoints. |
| src/backend/services/benchmark_jobs.py | Async job state and background execution wiring. |
| src/backend/main.py | Register benchmark router. |
| src/backend/tests/api/test_benchmark_runs_api.py | API coverage for create/list/get/cancel. |

**How to test:**
- `docker compose exec backend uv run pytest src/backend/tests/api/test_benchmark_runs_api.py`.
- Manual: start run, poll, cancel, and verify lifecycle states.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 11: Correctness judge integration - OpenAI rubric scoring

**Single goal:** Add one correctness evaluator that scores each benchmark result using OpenAI and stores normalized scores.

**Details:**
- Judge input includes question, expected answer points, model answer, and cited evidence.
- Structured output: `score_0_to_1`, `coverage`, `major_error_flags`, `rationale`.
- Judge calls use deterministic settings.
- Persist outputs in a dedicated judgments table.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): use existing `langchain-openai`.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/benchmark_judge_service.py | OpenAI judging and normalization. |
| src/backend/models.py | Add `benchmark_judgments` ORM model. |
| src/backend/alembic/versions/004_add_benchmark_judgments_table.py | Migration for judgments table. |
| src/backend/prompts/benchmark_judge_v1.txt | Versioned rubric prompt. |
| src/backend/tests/services/test_benchmark_judge_service.py | Judge parsing and persistence tests. |

**How to test:**
- Unit tests with mocked judge responses.
- Manual: run small benchmark and verify scores are written.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 12: Latency capture - per-question and per-stage timing records

**Single goal:** Add one timing instrumentation layer so latency can be analyzed at both end-to-end and stage levels.

**Details:**
- Persist end-to-end latency for each `(run_id, mode, question_id)`.
- Persist optional stage timings aligned to current stages.
- Record timeout and cancellation timing states distinctly.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/benchmark_runner.py | Emit timing checkpoints during execution. |
| src/backend/models.py | Add stage-timing model or JSON field. |
| src/backend/alembic/versions/005_add_benchmark_timing_fields.py | Migration for timing persistence additions. |
| src/backend/tests/services/test_benchmark_latency_capture.py | Timing persistence and edge-case tests. |

**How to test:**
- Unit tests for timing capture with mocked clocks.
- Manual: run benchmark and inspect timing fields in DB.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 13: Retrieval diagnostics - retrieval metrics persistence

**Single goal:** Add one retrieval diagnostics layer so benchmark failures can be explained using retrieval quality signals.

**Details:**
- Persist `recall@k`, `mrr`, `ndcg`, and retrieved document identifiers per result where labels allow.
- Attach diagnostics rows to `(run_id, mode, question_id)`.
- Expose diagnostics in run detail APIs for debugging.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration required.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/models.py | Add `benchmark_retrieval_metrics` ORM model. |
| src/backend/alembic/versions/006_add_benchmark_retrieval_metrics_table.py | Migration for retrieval metrics table. |
| src/backend/services/benchmark_retrieval_metrics_service.py | Compute and persist retrieval diagnostics. |
| src/backend/tests/services/test_benchmark_retrieval_metrics_service.py | Retrieval metrics calculation tests. |

**How to test:**
- Unit tests on synthetic retrieval labels.
- Manual: inspect retrieval metrics rows for a completed run.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 14: Benchmark aggregation service - correctness and latency summaries

**Single goal:** Implement one aggregation service that computes run-level and mode-level summary metrics.

**Details:**
- Compute metrics: mean correctness, p50 latency, p95 latency, pass/fail status.
- Recompute deterministically from persisted rows.
- Provide one summary payload used by APIs and dashboard.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/benchmark_metrics_service.py | Aggregation and percentile logic. |
| src/backend/services/benchmark_summary_service.py | Build run summary payloads. |
| src/backend/tests/services/test_benchmark_metrics_service.py | Aggregation correctness tests. |

**How to test:**
- Run service tests with synthetic metric fixtures.
- Manual: compare API summaries with SQL spot checks.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 15: Benchmark comparison endpoint - mode delta reporting

**Single goal:** Add one API endpoint that reports correctness and latency deltas between modes within a run.

**Details:**
- Endpoint: `GET /api/benchmarks/runs/{run_id}/compare`.
- Response includes deltas vs baseline mode for correctness and p95 latency.
- Use aggregation outputs instead of recomputing raw execution.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/routers/benchmarks.py | Add compare endpoint. |
| src/backend/schemas/benchmark.py | Comparison response models. |
| src/backend/tests/api/test_benchmark_compare_api.py | Compare payload and baseline behavior tests. |

**How to test:**
- `docker compose exec backend uv run pytest src/backend/tests/api/test_benchmark_compare_api.py`.
- Manual: call compare endpoint and validate delta math.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 16: Benchmark admin controls - data reset and retention tools

**Single goal:** Add one benchmark admin control layer so benchmark data can be safely reset and retained for long-term use.

**Details:**
- Add benchmark-specific wipe endpoint/CLI that clears only benchmark tables.
- Add retention policy command for deleting old runs beyond configured threshold.
- Protect production internal document tables from benchmark-only cleanup operations.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/routers/benchmarks.py | Add benchmark admin reset endpoints. |
| src/backend/common/db/benchmark_wipe.py | DB utilities for benchmark-only cleanup. |
| src/backend/benchmarks/retention.py | Retention policy command entrypoint. |
| src/backend/tests/db/test_benchmark_wipe.py | Validate wipe scope safety and retention behavior. |

**How to test:**
- Unit tests verifying only benchmark tables are truncated.
- Manual: run cleanup then verify benchmark tables empty and internal docs intact.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 17: Manual operator CLI - run and export commands

**Single goal:** Provide one backend CLI interface for manual benchmark execution and artifact export.

**Details:**
- Add run command to trigger benchmark with dataset and modes.
- Add export command to dump run results to JSON.
- CLI must call existing services/APIs instead of duplicating logic.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): optional `typer`; argparse acceptable.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/benchmarks/run.py | Manual benchmark run command. |
| src/backend/benchmarks/export.py | Export completed runs to JSON artifact files. |
| README.md | Document manual benchmark commands. |

**How to test:**
- `docker compose exec backend uv run python -m benchmarks.run --help`.
- Manual: trigger run via CLI and export artifact.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 18: Frontend benchmark run list - historical run visibility

**Single goal:** Add one dashboard view that lists benchmark runs with primary KPIs.

**Details:**
- Display `status`, `dataset`, `modes`, `correctness`, `p95 latency`, `started_at`, `duration`.
- Show pass/fail badge based on section 1 thresholds.
- This section is list view only.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/frontend/src/components/BenchmarkRunList.tsx | Historical run table component. |
| src/frontend/src/utils/api.ts | Add run-list client and types. |
| src/frontend/src/App.tsx | Integrate benchmark list view. |
| src/frontend/src/components/BenchmarkRunList.test.tsx | Rendering and KPI display tests. |

**How to test:**
- `docker compose exec frontend npm run typecheck`.
- `docker compose exec frontend npm run test`.
- Manual: open frontend and verify run list rendering.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 19: Frontend run details and compare view - per-mode and per-question inspection

**Single goal:** Add one dashboard detail view that surfaces per-mode and per-question benchmark outcomes.

**Details:**
- Show mode scorecards with correctness and latency.
- Show per-question rows with correctness, latency, and error status.
- Render compare endpoint deltas against baseline mode.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no Docker changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/frontend/src/components/BenchmarkRunDetail.tsx | Run details and mode comparison UI. |
| src/frontend/src/utils/api.ts | Add run-detail and compare client methods. |
| src/frontend/src/components/BenchmarkRunDetail.test.tsx | Detail-view behavior tests. |

**How to test:**
- `docker compose exec frontend npm run typecheck`.
- `docker compose exec frontend npm run test`.
- Manual: select run and verify detail rendering.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Section 20: End-to-end acceptance matrix - section-by-section completion gates

**Single goal:** Define one completion checklist that can be executed after each section to prove readiness for the next section.

**Details:**
- Add explicit gate checks for every section so implementation can proceed sequentially.
- Include negative paths: invalid mode, missing dataset, OpenAI timeout/failure, job cancellation.
- Include final E2E path: load corpus -> create run -> complete run -> compare modes -> inspect dashboard.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): use existing docker compose test commands.

**Files and purpose**

| File | Purpose |
|------|--------|
| spec.md | Ordered gate checklist and acceptance criteria. |
| src/backend/tests/e2e/test_benchmark_pipeline.py | Backend E2E acceptance flow. |
| src/frontend/src/components/BenchmarkRunList.test.tsx | Frontend list acceptance coverage. |
| src/frontend/src/components/BenchmarkRunDetail.test.tsx | Frontend detail acceptance coverage. |

**How to test:**
- `docker compose exec backend uv run pytest src/backend/tests/e2e/test_benchmark_pipeline.py`.
- `docker compose exec frontend npm run test`.
- Manual: validate full workflow across API and UI.

**Test results:** (Add when section is complete.)
- Not implemented yet.

---

## Implementation order rationale

- Sections 1-2 lock objective and runtime controls.
- Sections 3-5 lock dataset and corpus determinism before any run execution.
- Sections 6-7 create persistence primitives before runner writes.
- Sections 8-10 create executable benchmark runs and lifecycle APIs.
- Sections 11-15 add scoring, latency, diagnostics, and comparisons.
- Sections 16-17 complete operator controls for long-term maintainability.
- Sections 18-19 complete product integration in frontend.
- Section 20 validates full-system integration end-to-end.
- Cross-branch merge constraint: merge implementation plan section 20 (OpenAPI regeneration) after benchmark API routes are merged to avoid clobbering benchmark paths in `openapi.json`.

## Source alignment notes

- Onyx article concepts adapted: mode comparison, correctness/latency focus, operator workflow.
- DeepResearchBench concepts adapted: structured question records and per-question evaluation rigor.
- Per your requirement, benchmark logic is re-implemented in this repository.
- References:
  - https://onyx.app/blog/benchmarking-agentic-rag-on-workplace-questions
  - https://deepresearch-bench.github.io/
  - https://github.com/Ayanami0730/deep_research_bench
