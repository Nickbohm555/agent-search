Tasks are in **required implementation order** (1...n). Each section = one context window. Complete one section at a time.

Current section to work on: section 1. (move +1 after each turn)

---

## Section 1: Baseline contract snapshot - runtime behavior guardrail

**Single goal:** Capture current backend runtime response contracts so all refactors and benchmark integration are validated against fixed baselines.

**Details:**
- Snapshot sync/async agent-run payload shapes.
- Snapshot current route inventory and response schemas.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): existing backend pytest workflow.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tests/api/test_agent_run.py` | API response-shape baseline assertions. |
| `src/backend/tests/api/test_health.py` | Baseline API sanity guard. |
| `test_completed.md` | Track baseline results and commands. |

**How to test:** Run backend API tests for route/shape stability.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 2: Shared contract freeze - SDK + benchmark interfaces

**Single goal:** Freeze public interfaces used by both SDK extraction and benchmark system before implementation diverges.

**Details:**
- Lock `agent_search.public_api` sync/async signatures.
- Lock benchmark API schema contracts and core request/response models.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/public_api.py` | Canonical SDK function signatures. |
| `src/backend/schemas/benchmark.py` | Canonical benchmark API model contracts. |
| `src/backend/tests/contracts/test_public_contracts.py` | Contract freeze tests for signatures/schemas. |

**How to test:** Run contract tests and verify no interface drift.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 3: SDK public sync API contract - stable callable entrypoint

**Single goal:** Expose primary in-process SDK sync entrypoint requiring `query`, `vector_store`, and `model`.

**Details:**
- Enforce required `model` argument.
- Return type compatible with runtime response model.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/__init__.py` | Public SDK import surface. |
| `src/backend/agent_search/public_api.py` | Sync SDK entrypoint. |
| `src/backend/tests/sdk/test_public_api.py` | Signature and return-contract tests. |

**How to test:** Run SDK sync API contract tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 4: SDK public async API contract - stable lifecycle entrypoint

**Single goal:** Expose SDK async `run_async`, `get_run_status`, and `cancel_run` interfaces.

**Details:**
- Keep payload fields aligned with current async runtime shape.
- Keep cancellation/status semantics stable.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/public_api.py` | Async SDK lifecycle functions. |
| `src/backend/tests/sdk/test_public_api_async.py` | Async lifecycle contract tests. |

**How to test:** Run SDK async contract tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 5: SDK error taxonomy - explicit consumer-facing exceptions

**Single goal:** Add deterministic SDK exception types.

**Details:**
- Define configuration, retrieval, model, and timeout exceptions.
- Map internal errors to public SDK exception hierarchy.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/errors.py` | SDK exception hierarchy. |
| `src/backend/agent_search/public_api.py` | Boundary exception mapping. |
| `src/backend/tests/sdk/test_errors.py` | Exception contract tests. |

**How to test:** Run SDK error-path tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 6: VectorStore protocol contract - runtime storage abstraction

**Single goal:** Define SDK retrieval protocol boundary.

**Details:**
- Specify required retrieval methods and document semantics.
- Fail fast on protocol-incompatible stores.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/vectorstore/protocol.py` | `VectorStoreProtocol` definition. |
| `src/backend/tests/sdk/test_vectorstore_protocol.py` | Protocol compatibility tests. |

**How to test:** Run protocol contract tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 7: LangChain vector store adapter - first-class implementation

**Single goal:** Implement LangChain adapter for SDK vector store protocol.

**Details:**
- Support similarity retrieval and score behaviors currently used.
- Preserve fallback retrieval paths.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): reuse existing LangChain packages.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/vectorstore/langchain_adapter.py` | Production protocol adapter. |
| `src/backend/tests/sdk/test_langchain_vectorstore_adapter.py` | Adapter behavior tests. |

**How to test:** Run adapter tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 8: Runtime configuration model - explicit SDK knobs

**Single goal:** Add public `RuntimeConfig` for SDK execution controls.

**Details:**
- Include timeout, retrieval, and rerank controls.
- Defaults must preserve current behavior.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/config.py` | SDK runtime configuration model. |
| `src/backend/tests/sdk/test_runtime_config.py` | Config defaults/override tests. |

**How to test:** Run runtime config tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 9: Runtime core module boundary - framework-independent orchestration shell

**Single goal:** Extract framework-independent runtime orchestrator.

**Details:**
- Move orchestration into SDK runtime module.
- Remove FastAPI/SQLAlchemy coupling at core runtime boundary.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/runner.py` | Core orchestration boundary. |
| `src/backend/services/agent_service.py` | Compatibility wrapper during migration. |
| `src/backend/tests/services/test_agent_service.py` | Wrapper parity tests. |

**How to test:** Run runtime + service parity tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 10: Decomposition node extraction - isolated runtime node module

**Single goal:** Extract decomposition node without behavior change.

**Details:**
- Preserve prompt/parse/fallback semantics.
- Keep output guarantees unchanged.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/decompose.py` | Decomposition node. |
| `src/backend/tests/sdk/test_node_decompose.py` | Decomposition tests. |

**How to test:** Run decomposition node tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 11: Expansion node extraction - isolated runtime node module

**Single goal:** Extract query expansion node without behavior change.

**Details:**
- Preserve bounds, dedupe, fallback behavior.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/expand.py` | Expansion node. |
| `src/backend/tests/sdk/test_node_expand.py` | Expansion tests. |

**How to test:** Run expansion node tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 12: Search node extraction - protocol-backed retrieval module

**Single goal:** Extract retrieval/merge/dedupe logic into protocol-backed node.

**Details:**
- Use `VectorStoreProtocol` only.
- Preserve provenance output used for citations/debug.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/search.py` | Search node implementation. |
| `src/backend/tests/sdk/test_node_search.py` | Search node tests. |

**How to test:** Run search node tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 13: Rerank node extraction - isolated ranking module

**Single goal:** Extract rerank logic without behavior change.

**Details:**
- Preserve deterministic fallback.
- Preserve citation row remapping semantics.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): reuse existing `flashrank`.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/rerank.py` | Rerank node. |
| `src/backend/tests/sdk/test_node_rerank.py` | Rerank tests. |

**How to test:** Run rerank node tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 14: Subanswer node extraction - isolated answer module

**Single goal:** Extract subanswer generation/verification node.

**Details:**
- Preserve answerability verification and fallback behavior.
- Keep sub-question output fields stable.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/answer.py` | Subanswer node implementation. |
| `src/backend/tests/sdk/test_node_answer.py` | Subanswer node tests. |

**How to test:** Run subanswer node tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 15: Final synthesis node extraction - isolated output module

**Single goal:** Extract final synthesis/citation contract logic.

**Details:**
- Preserve final output shape and fallback selection behavior.
- Preserve citation contract enforcement.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/nodes/synthesize.py` | Final synthesis node. |
| `src/backend/tests/sdk/test_node_synthesize.py` | Synthesis node tests. |

**How to test:** Run synthesis node tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 16: SDK sync runtime wiring - end-to-end sync path

**Single goal:** Wire public SDK sync API to extracted runtime graph.

**Details:**
- Use extracted runtime modules only.
- Require caller-provided `model` and `vector_store`.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/public_api.py` | Sync execution wiring. |
| `src/backend/agent_search/runtime/runner.py` | Sync orchestration entry. |
| `src/backend/tests/sdk/test_sdk_run_e2e.py` | Sync E2E tests. |

**How to test:** Run SDK sync E2E tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 17: SDK async runtime wiring - end-to-end async path

**Single goal:** Wire SDK async lifecycle to shared runtime job manager.

**Details:**
- Implement start/status/cancel manager.
- Preserve stage snapshots and cancellation semantics.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/jobs.py` | Async job manager. |
| `src/backend/agent_search/public_api.py` | Async lifecycle wiring. |
| `src/backend/tests/sdk/test_sdk_async_e2e.py` | Async E2E tests. |

**How to test:** Run SDK async E2E tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 18: Backend endpoint delegation - SDK-only runtime path

**Single goal:** Delegate backend sync/async agent routes to SDK public API.

**Details:**
- `/api/agents/run` delegates to SDK sync.
- Async start/status/cancel routes delegate to SDK async lifecycle.
- Preserve current payload contracts.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/routers/agent.py` | SDK delegation for all agent routes. |
| `src/backend/tests/api/test_agent_run.py` | Delegation parity tests. |

**How to test:** Run backend agent API tests for sync+async.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 19: Legacy runtime cleanup - single orchestration implementation

**Single goal:** Remove duplicate orchestration paths outside SDK runtime.

**Details:**
- Keep service wrappers thin.
- Ensure backend and internal callers share same runtime path.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Thin SDK wrapper only. |
| `src/backend/services/agent_jobs.py` | Delegate to SDK jobs manager. |
| `src/backend/tests/services/test_agent_service.py` | Single-path behavior tests. |

**How to test:** Run service tests and verify no duplicate path usage.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 20: Benchmark charter - correctness and latency targets

**Single goal:** Define benchmark objective contract used by APIs, runner, and UI.

**Details:**
- Primary KPI correctness, secondary KPI latency.
- v1 thresholds: correctness >= 0.75 and p95 latency <= 30,000ms.
- Manual-only benchmark execution.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `spec.md` | Benchmark requirement source of truth. |
| `src/backend/schemas/benchmark.py` | Threshold models used by API/UI. |

**How to test:** Validate threshold block appears in benchmark run status response.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 21: Benchmark runtime settings - env-backed and reproducible

**Single goal:** Add centralized benchmark settings and context fingerprinting.

**Details:**
- Add settings for dataset default, judge model, timeout caps, and targets.
- Compute execution context fingerprint for run reproducibility.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): update `.env.example` only.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/config.py` | Benchmark runtime settings. |
| `.env.example` | Benchmark env docs. |
| `src/backend/tests/utils/test_benchmark_config.py` | Config parsing tests. |

**How to test:** Run benchmark config tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 22: Internal benchmark dataset schema - DeepResearchBench-aligned

**Single goal:** Define strict JSONL schema for internal benchmark questions.

**Details:**
- Required fields: `question_id`, `question`, `domain`, `difficulty`, `expected_answer_points`, `required_sources`, `disallowed_behaviors`.
- v1 dataset size target: 120 public questions.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/benchmarks/datasets/schema.md` | Dataset contract documentation. |
| `src/backend/benchmarks/datasets/internal_v1/questions.jsonl` | v1 benchmark questions. |
| `src/backend/tests/benchmarks/test_dataset_schema.py` | Schema/distribution tests. |

**How to test:** Run dataset schema tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 23: Dataset curation workflow - generation and human review

**Single goal:** Build reproducible question generation and review workflow.

**Details:**
- Generate question candidates from public corpora via OpenAI.
- Require human approval and provenance metadata before dataset freeze.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): optional `typer` or argparse.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/benchmarks/tools/generate_questions.py` | Candidate generation utility. |
| `src/backend/benchmarks/tools/review_queue.py` | Review/approval workflow utility. |
| `src/backend/benchmarks/datasets/internal_v1/provenance.jsonl` | Provenance ledger. |

**How to test:** Run unit tests for review transitions and export.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 24: Benchmark corpus fixture - deterministic source loading

**Single goal:** Ensure benchmark runs operate on deterministic indexed source corpus.

**Details:**
- Define corpus manifest.
- Add repeatable load/reset utility and corpus hash generation.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): reuse existing internal-data load/wipe flow.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/benchmarks/corpus/internal_v1_manifest.json` | Source manifest for benchmark corpus. |
| `src/backend/benchmarks/tools/load_corpus.py` | Deterministic corpus loader/reset tool. |
| `src/backend/tests/benchmarks/test_corpus_loader.py` | Deterministic corpus tests. |

**How to test:** Run corpus load twice and verify identical hash/counts.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 25: Benchmark DB foundation - run metadata tables

**Single goal:** Add persistent run metadata schema.

**Details:**
- Add `benchmark_runs` and `benchmark_run_modes`.
- Record SLO snapshot, context fingerprint, and corpus hash.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/models.py` | Benchmark run metadata models. |
| `src/backend/alembic/versions/002_add_benchmark_run_metadata_tables.py` | Migration file. |
| `src/backend/tests/db/test_benchmark_run_metadata_schema.py` | Schema tests. |

**How to test:** Run alembic upgrade and schema tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 26: Benchmark DB outputs - per-question result table

**Single goal:** Add persistent per-question/per-mode result storage.

**Details:**
- Add `benchmark_results` keyed by `(run_id, mode, question_id)`.
- Persist answer payload, citations, latency, tokens, execution errors.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/models.py` | `BenchmarkResult` model. |
| `src/backend/alembic/versions/003_add_benchmark_results_table.py` | Migration file. |
| `src/backend/tests/db/test_benchmark_results_schema.py` | Schema/constraint tests. |

**How to test:** Run migration and DB tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 27: Benchmark mode registry - deterministic evaluation modes

**Single goal:** Define stable benchmark mode registry.

**Details:**
- Modes: `baseline_retrieve_then_answer`, `agentic_default`, `agentic_no_rerank`, `agentic_single_query_no_decompose`.
- Reject unknown modes at validation time.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_modes.py` | Mode definitions and overrides. |
| `src/backend/schemas/benchmark.py` | Mode enums/validators. |
| `src/backend/tests/services/test_benchmark_modes.py` | Registry tests. |

**How to test:** Run benchmark mode tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 28: Benchmark execution adapter - SDK boundary isolation

**Single goal:** Add adapter layer so benchmark runner depends only on SDK public API boundary.

**Details:**
- Runner calls adapter, adapter calls `agent_search.public_api` sync/async.
- Prevent direct dependency on legacy service internals.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_execution_adapter.py` | SDK-boundary execution adapter. |
| `src/backend/tests/services/test_benchmark_execution_adapter.py` | Adapter contract tests. |

**How to test:** Run adapter tests with mocked SDK public API.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 29: Benchmark runner core - synchronous evaluation engine

**Single goal:** Implement core runner iterating mode x question and persisting raw outputs.

**Details:**
- Load dataset by version.
- Execute through benchmark execution adapter.
- Persist incremental results for crash-safe partial progress.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_runner.py` | Core benchmark execution loop. |
| `src/backend/tests/services/test_benchmark_runner.py` | Iteration/persistence tests. |

**How to test:** Run runner tests and smoke run on small dataset.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 30: Benchmark run lifecycle API - manual orchestration endpoints

**Single goal:** Expose manual benchmark create/list/get/cancel APIs.

**Details:**
- Endpoints: create/list/get/cancel for runs.
- Async job lifecycle semantics mirror existing agent async behavior.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/routers/benchmarks.py` | Benchmark lifecycle endpoints. |
| `src/backend/services/benchmark_jobs.py` | Benchmark job manager. |
| `src/backend/main.py` | Router registration. |
| `src/backend/tests/api/test_benchmark_runs_api.py` | Lifecycle API tests. |

**How to test:** Run benchmark lifecycle API tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 31: Correctness judge integration - OpenAI rubric scoring

**Single goal:** Score benchmark outputs for correctness via OpenAI judge.

**Details:**
- Deterministic judge settings.
- Structured outputs: score, coverage, major errors, rationale.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): use existing `langchain-openai`.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_judge_service.py` | Judge integration service. |
| `src/backend/models.py` | `benchmark_judgments` model. |
| `src/backend/alembic/versions/004_add_benchmark_judgments_table.py` | Migration file. |
| `src/backend/prompts/benchmark_judge_v1.txt` | Judge rubric prompt. |
| `src/backend/tests/services/test_benchmark_judge_service.py` | Judge service tests. |

**How to test:** Run judge unit tests and small manual judged run.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 32: Latency instrumentation - end-to-end and stage timings

**Single goal:** Capture per-result end-to-end and stage-level latency.

**Details:**
- Persist e2e latency and optional stage timing blocks.
- Distinguish timeout/cancel timing outcomes.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration if new fields/tables required.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_runner.py` | Timing checkpoint instrumentation. |
| `src/backend/models.py` | Timing model/fields. |
| `src/backend/alembic/versions/005_add_benchmark_timing_fields.py` | Timing migration. |
| `src/backend/tests/services/test_benchmark_latency_capture.py` | Timing tests. |

**How to test:** Run timing tests and verify DB timing fields after run.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 33: Retrieval diagnostics - benchmark retrieval quality signals

**Single goal:** Add retrieval diagnostics for failure analysis.

**Details:**
- Persist `recall@k`, `mrr`, `ndcg`, and retrieved IDs where labels allow.
- Expose diagnostics in run detail payloads.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): Alembic migration.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/models.py` | `benchmark_retrieval_metrics` model. |
| `src/backend/alembic/versions/006_add_benchmark_retrieval_metrics_table.py` | Migration file. |
| `src/backend/services/benchmark_retrieval_metrics_service.py` | Metrics service. |
| `src/backend/tests/services/test_benchmark_retrieval_metrics_service.py` | Retrieval diagnostics tests. |

**How to test:** Run retrieval diagnostics tests and inspect saved metrics.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 34: Benchmark aggregation service - run and mode summaries

**Single goal:** Compute run-level and mode-level summary metrics.

**Details:**
- Aggregate correctness and latency percentiles.
- Produce deterministic pass/fail summaries.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/benchmark_metrics_service.py` | Aggregation logic. |
| `src/backend/services/benchmark_summary_service.py` | Summary payload assembly. |
| `src/backend/tests/services/test_benchmark_metrics_service.py` | Aggregation tests. |

**How to test:** Run metric aggregation tests and SQL spot checks.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 35: Benchmark compare API - mode delta endpoint

**Single goal:** Add run-level mode comparison endpoint.

**Details:**
- Endpoint: `GET /api/benchmarks/runs/{run_id}/compare`.
- Report correctness and p95 latency deltas vs baseline mode.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/routers/benchmarks.py` | Compare endpoint. |
| `src/backend/schemas/benchmark.py` | Compare response models. |
| `src/backend/tests/api/test_benchmark_compare_api.py` | Compare API tests. |

**How to test:** Run compare API tests.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 36: Benchmark admin controls - benchmark-only wipe and retention

**Single goal:** Add safe benchmark maintenance controls.

**Details:**
- Add benchmark-only wipe endpoint/utility.
- Add retention command for old benchmark runs.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/common/db/benchmark_wipe.py` | Benchmark-only cleanup utility. |
| `src/backend/benchmarks/retention.py` | Retention command utility. |
| `src/backend/tests/db/test_benchmark_wipe.py` | Cleanup safety tests. |

**How to test:** Run cleanup tests and verify non-benchmark tables untouched.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 37: Manual benchmark operator CLI - run and export

**Single goal:** Provide CLI commands for manual benchmark runs and artifact export.

**Details:**
- Add run command with dataset/mode flags.
- Add export command for JSON results.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): optional `typer`; argparse acceptable.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/benchmarks/run.py` | Benchmark run CLI entrypoint. |
| `src/backend/benchmarks/export.py` | Benchmark export CLI entrypoint. |
| `README.md` | CLI usage documentation. |

**How to test:** Run CLI help and manual smoke run/export.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 38: Frontend benchmark run list - historical visibility

**Single goal:** Add frontend run-list view for benchmark history and KPIs.

**Details:**
- Show status, dataset, modes, correctness, p95 latency, start time, duration.
- Display pass/fail badge from threshold contract.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/components/BenchmarkRunList.tsx` | Run history table view. |
| `src/frontend/src/utils/api.ts` | Run list API client/types. |
| `src/frontend/src/App.tsx` | Run list integration. |
| `src/frontend/src/components/BenchmarkRunList.test.tsx` | Run list UI tests. |

**How to test:** Run frontend typecheck/tests and manual UI check.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 39: Frontend benchmark detail view - per-mode and per-question insights

**Single goal:** Add run detail UI with mode deltas and question-level outcomes.

**Details:**
- Show mode scorecards and compare deltas.
- Show question rows with correctness, latency, and error status.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/components/BenchmarkRunDetail.tsx` | Benchmark run detail view. |
| `src/frontend/src/utils/api.ts` | Detail/compare API client methods. |
| `src/frontend/src/components/BenchmarkRunDetail.test.tsx` | Detail view tests. |

**How to test:** Run frontend tests and manual detail page check.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 40: OpenAPI synchronization - canonical contract refresh (final)

**Single goal:** Regenerate and commit final OpenAPI after both SDK and benchmark routes are in place.

**Details:**
- Ensure agent async/sync and benchmark endpoints are present.
- Avoid intermediate spec churn before final endpoint set stabilizes.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): use existing OpenAPI export workflow.

**Files and purpose**

| File | Purpose |
|------|--------|
| `openapi.json` | Final canonical OpenAPI artifact. |
| `scripts/export_openapi.py` | Spec generation utility. |

**How to test:** Regenerate spec and verify path inventory includes benchmark + agent routes.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 41: Generated HTTP client refresh - post-contract artifact alignment

**Single goal:** Regenerate Python OpenAPI client from final spec.

**Details:**
- Refresh generated methods/models including benchmark endpoints.
- Keep generated client secondary to in-process SDK.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new runtime dependencies.
- Tooling (uv, poetry, Docker): use existing generation scripts.

**Files and purpose**

| File | Purpose |
|------|--------|
| `sdk/python/openapi_client/**` | Refreshed generated client code. |
| `sdk/python/docs/**` | Refreshed generated docs. |
| `sdk/README.md` | Artifact role clarification. |

**How to test:** Regenerate and verify benchmark endpoints in generated classes.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 42: SDK packaging workspace - distributable boundary

**Single goal:** Create dedicated package workspace for core in-process SDK distribution.

**Details:**
- Separate SDK package metadata from backend app packaging.
- Exclude backend-only web/db dependencies from SDK package.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): packaging metadata updates.
- Tooling (uv, poetry, Docker): add package build commands for SDK workspace.

**Files and purpose**

| File | Purpose |
|------|--------|
| `sdk/core/pyproject.toml` | Core SDK package metadata. |
| `sdk/core/README.md` | Package-local long description source. |
| `sdk/core/src/agent_search/__init__.py` | SDK package root. |

**How to test:** Build wheel/sdist and inspect dependency boundary.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 43: PyPI metadata and release workflow - publishable SDK

**Single goal:** Finalize publish metadata and repeatable release workflow for SDK.

**Details:**
- Configure package identity/versioning/classifiers.
- Add reproducible release commands and optional workflow automation.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): build/publish tooling as needed.
- Tooling (uv, poetry, Docker): add release helper script/workflow.

**Files and purpose**

| File | Purpose |
|------|--------|
| `scripts/release_sdk.sh` | Local release helper flow. |
| `.github/workflows/release-sdk.yml` | Tagged release workflow. |
| `README.md` | Release/versioning docs. |

**How to test:** Run build/check dry-run (`python -m build`, `twine check`).

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 44: SDK-first documentation and CI drift gates - long-term safety

**Single goal:** Complete docs and CI checks to prevent API/SDK/spec drift after integration.

**Details:**
- Publish SDK-first quickstart and benchmark usage docs.
- Add CI gates for OpenAPI parity and generated client freshness.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new runtime dependencies.
- Tooling (uv, poetry, Docker): add CI validation steps.

**Files and purpose**

| File | Purpose |
|------|--------|
| `README.md` | SDK-first and benchmark operator docs. |
| `docs/SYSTEM_ARCHITECTURE.md` | Updated architecture boundary docs. |
| `scripts/validate_openapi.sh` | OpenAPI drift gate script. |
| `.github/workflows/ci.yml` | CI checks for spec/client parity. |

**How to test:** Run CI-equivalent checks locally and verify intentional drift fails.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 45: End-to-end integrated acceptance - full system completion gate

**Single goal:** Validate full integrated system from SDK runtime through benchmark dashboard.

**Details:**
- Required path: corpus load -> benchmark run create -> completion -> compare endpoint -> dashboard list/detail verification.
- Include negative paths: invalid mode, dataset missing, judge timeout/failure, cancellation.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): use existing docker compose test flows.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tests/e2e/test_benchmark_pipeline.py` | Backend E2E acceptance flow. |
| `src/backend/tests/sdk/test_sdk_run_e2e.py` | SDK E2E sync acceptance. |
| `src/backend/tests/sdk/test_sdk_async_e2e.py` | SDK E2E async acceptance. |
| `src/frontend/src/components/BenchmarkRunList.test.tsx` | Frontend benchmark list acceptance. |
| `src/frontend/src/components/BenchmarkRunDetail.test.tsx` | Frontend benchmark detail acceptance. |
| `test_completed.md` | Final integrated test command/results log. |

**How to test:**
- `docker compose exec backend uv run pytest`
- `docker compose exec frontend npm run test`
- Manual end-to-end verification at `http://localhost:5173`.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 46: Langfuse foundation - SDK/runtime observability configuration

**Single goal:** Add configuration and client bootstrap for Langfuse across SDK runtime and benchmark services.

**Details:**
- Define environment-backed Langfuse settings (host, public key, secret key, enabled flag, sampling controls).
- Initialize a shared Langfuse client utility used by SDK runtime and benchmark services.
- Ensure observability can be disabled cleanly without affecting runtime behavior.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): reuse existing `langfuse` dependency in backend.
- Tooling (uv, poetry, Docker): add env var docs and compose env pass-through if needed.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/config.py` | Langfuse configuration fields and defaults. |
| `src/backend/utils/langfuse_tracing.py` | Shared Langfuse client/bootstrap helpers. |
| `.env.example` | Langfuse env variable documentation. |
| `src/backend/tests/utils/test_langfuse_tracing.py` | Langfuse bootstrap/config tests. |

**How to test:** Run Langfuse utility tests with enabled/disabled modes and verify no-op fallback behavior.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 47: Langfuse instrumentation - runtime and benchmark traces

**Single goal:** Instrument SDK runtime stages and benchmark lifecycle with consistent Langfuse traces and scores.

**Details:**
- Emit traces/spans for SDK runtime stages (`decompose`, `expand`, `search`, `rerank`, `answer`, `final`).
- Emit benchmark run spans for dataset load, mode execution, question execution, judge scoring, and aggregation.
- Attach run metadata (run_id, mode, question_id, correctness score, latency) to trace attributes.
- Record benchmark correctness/latency outputs as Langfuse scores where appropriate.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): reuse existing `langfuse` dependency.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agent_search/runtime/runner.py` | Stage-level runtime tracing instrumentation. |
| `src/backend/services/benchmark_runner.py` | Benchmark execution tracing instrumentation. |
| `src/backend/services/benchmark_judge_service.py` | Judge call tracing and score logging. |
| `src/backend/tests/sdk/test_sdk_run_e2e.py` | Verify runtime trace hooks do not break behavior. |
| `src/backend/tests/services/test_benchmark_runner.py` | Verify benchmark trace metadata propagation. |

**How to test:** Run SDK and benchmark tests with Langfuse enabled in test mode and verify expected trace payload hooks are called.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 48: Documentation refresh - SDK, benchmark, README, and run-flow assets

**Single goal:** Update all user-facing and developer-facing documentation to reflect the integrated SDK + benchmark + Langfuse system.

**Details:**
- Update top-level `README.md` with SDK usage, benchmark operation, and Langfuse setup.
- Update SDK docs (`sdk/README.md` and package docs) with sync/async usage, error taxonomy, and vectorstore adapter guidance.
- Update architecture docs for runtime boundaries and benchmark pipeline.
- Update frontend visualization artifact `src/frontend/public/run-flow.html` to include benchmark and observability flow.
- Ensure docs reference real commands from Docker Compose/uv workflows used in this repo.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `README.md` | Primary setup and operations guide for SDK + benchmark + Langfuse. |
| `sdk/README.md` | SDK consumer guide and generated-client positioning. |
| `sdk/core/README.md` | Core package usage and release notes guidance. |
| `docs/SYSTEM_ARCHITECTURE.md` | Updated architecture and flow boundaries. |
| `src/frontend/public/run-flow.html` | Updated runtime/benchmark flow visualization. |

**How to test:** Manually execute documented commands end-to-end and verify docs match actual outputs and paths.

**Test results:** (Add when section is complete.)
- Pending.

---

## Section 49: Final acceptance rerun - full system with observability and docs parity

**Single goal:** Re-run final acceptance after Langfuse and documentation updates to confirm production readiness.

**Details:**
- Repeat end-to-end verification for SDK runtime, benchmark APIs, dashboard, and compare endpoints.
- Verify Langfuse traces/spans/scores are emitted for at least one complete benchmark run.
- Verify all documentation paths and commands are accurate by executing them in a clean flow.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): existing test and compose workflows.

**Files and purpose**

| File | Purpose |
|------|--------|
| `test_completed.md` | Final integrated validation record including Langfuse + docs checks. |
| `src/backend/tests/e2e/test_benchmark_pipeline.py` | Final backend E2E regression check. |
| `src/backend/tests/sdk/test_sdk_async_e2e.py` | Final SDK async regression check. |
| `src/frontend/src/components/BenchmarkRunDetail.test.tsx` | Final frontend regression coverage touchpoint. |

**How to test:**
- `docker compose exec backend uv run pytest`
- `docker compose exec frontend npm run test`
- Manual: run one benchmark and confirm Langfuse traces plus documentation command parity.

**Test results:** (Add when section is complete.)
- Pending.

---

## Ordering rationale

- Sections 1-19: establish SDK runtime as the single execution path.
- Sections 20-39: build benchmark system on top of stable SDK boundaries.
- Sections 40-44: regenerate artifacts, package, and enforce drift gates after APIs stabilize.
- Section 45: first full integration acceptance gate (SDK + benchmark product flow).
- Sections 46-47: integrate Langfuse observability after core functionality is stable.
- Section 48: complete cross-surface documentation updates, including `run-flow.html`.
- Section 49: final acceptance rerun with observability and docs parity included.
