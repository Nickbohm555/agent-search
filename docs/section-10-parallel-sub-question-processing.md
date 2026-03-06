# Section 10 Architecture: Parallel sub-question processing

## Purpose
Execute the per-subquestion post-retrieval pipeline concurrently so each sub-question is processed independently (validation -> rerank -> subanswer -> verification) while preserving deterministic output order for downstream synthesis.

## Components
- Orchestration entrypoint: `src/backend/services/agent_service.py`
- `run_pipeline_for_subquestions(sub_qa)`
- Per-item worker: `_run_pipeline_for_single_subquestion(item)`
- Parallel runtime primitive: `ThreadPoolExecutor` + `as_completed`
- Stage functions (called in-sequence per item):
- `_apply_document_validation_to_sub_qa(...)`
- `_apply_reranking_to_sub_qa(...)`
- `_apply_subanswer_generation_to_sub_qa(...)`
- `_apply_subanswer_verification_to_sub_qa(...)`
- Shared data model: `src/backend/schemas/agent.py`
- `SubQuestionAnswer`
- Upstream producer in same module:
- `_extract_sub_qa(...)` converts coordinator tool-call traces into `SubQuestionAnswer` rows.
- Downstream consumers in same module:
- `generate_initial_answer(...)` (Section 11)
- `should_refine(...)` and refinement path (Sections 12-14)

## Data Flow
### Inputs
1. `list[SubQuestionAnswer]` where each item already has:
- `sub_question`: decomposed question text.
- `sub_answer`: retrieval payload string from earlier search stages (ranked `N. title=... source=... content=...` rows).
- `expanded_query`, `tool_call_input`, `sub_agent_response`: metadata captured from tool traces.
2. Runtime config:
- `_SUBQUESTION_PIPELINE_MAX_WORKERS` (env-backed, default `4`).

### Transformations
1. `run_runtime_agent(...)` gets raw sub-question retrieval outputs and calls `run_pipeline_for_subquestions(sub_qa)`.
2. `run_pipeline_for_subquestions(...)`:
- Computes `effective_workers = min(configured_workers, len(sub_qa))`.
- Submits one future per `SubQuestionAnswer` to `_run_pipeline_for_single_subquestion(...)`.
- Stores each completed result back into a pre-sized output list by original index.
3. `_run_pipeline_for_single_subquestion(...)` performs a strict in-item sequence:
- Deep-copy input item (`model_copy(deep=True)`) to avoid shared mutable state between threads.
- Document validation filters parseable retrieval rows.
- Reranking reorders/limits validated rows using lexical scoring.
- Snapshot reranked retrieval string for grounding checks.
- Subanswer generation rewrites `sub_answer` from retrieval rows into answer text.
- Subanswer verification writes `answerable` + `verification_reason` using generated answer + reranked snapshot.
4. `run_pipeline_for_subquestions(...)` returns fully processed items in original input order.

### Outputs
- `list[SubQuestionAnswer]` (same cardinality/order as input) with updated fields:
- `sub_answer` now contains generated sub-answer text.
- `answerable` and `verification_reason` are set.
- Metadata fields (`sub_question`, `expanded_query`, `tool_call_input`, `sub_agent_response`) are retained.
- Stage-level logs for observability:
- parallel start/complete with worker counts
- per-item start/complete with verification status

### Data Movement Boundaries
- Boundary A (Sections 4-5 -> Section 10): retrieval-formatted text enters as `sub_answer` from `_extract_sub_qa(...)`.
- Boundary B (inside Section 10): `sub_answer` changes representation from retrieval rows to generated prose after subanswer generation.
- Boundary C (Section 10 -> Section 11): processed `sub_qa` list is consumed by initial answer synthesis.
- Boundary D (Section 10 -> Section 12): verification fields drive refinement decision logic.

## Key Interfaces and APIs
- `run_pipeline_for_subquestions(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]`
- `_run_pipeline_for_single_subquestion(item: SubQuestionAnswer) -> SubQuestionAnswer`
- `SubQuestionAnswer` fields relevant to this section:
- Input-oriented: `sub_question`, `sub_answer`, `expanded_query`, `tool_call_input`, `sub_agent_response`
- Output-oriented: `sub_answer`, `answerable`, `verification_reason`
- Stage service APIs used per item:
- `validate_subquestion_documents(...)`
- `rerank_documents(...)`
- `generate_subanswer(...)`
- `verify_subanswer(...)`

## Fit With Adjacent Sections
- Upstream:
- Section 3 produces sub-questions.
- Sections 4-5 currently run through coordinator/subagent tool usage and are materialized into `SubQuestionAnswer` before this section.
- Sections 6-9 define the stage logic this section orchestrates.
- Current section:
- Section 10 is the concurrency/orchestration layer around those stage services.
- Downstream:
- Section 11 synthesizes the user-facing initial answer from processed `sub_qa`.
- Section 12 uses verification outcomes to decide whether refinement is required.
- Sections 13-14 may run the same parallel pipeline again on refined sub-questions.

## Tradeoffs
### Chosen design
Use thread-based parallelism (`ThreadPoolExecutor`) at sub-question granularity, with sequential stage execution inside each worker.

### Benefits
- Minimal implementation complexity using Python stdlib concurrency.
- Isolates state per sub-question via deep copies, reducing race-condition risk.
- Preserves deterministic output ordering even with out-of-order completion.
- Reuses existing Section 6-9 stage functions without rewriting service contracts.

### Costs
- Threading adds overhead for very small batches; limited benefit when only one sub-question exists.
- If downstream stages are heavily CPU-bound, Python threading may not scale due to GIL constraints.
- Fail-fast behavior: an exception in one future currently propagates and aborts the run.
- Data representation churn (`sub_answer` changes from retrieval rows to prose) requires careful stage ordering.

### Alternatives considered or rejected
1. Sequential loop over sub-questions.
Pros: simplest control flow, easiest debugging.
Cons: higher end-to-end latency as sub-question count grows.
2. `asyncio` task orchestration.
Pros: strong fit for async I/O-bound stages and cancellation control.
Cons: would require broader async refactor across synchronous stage services.
3. Process pool parallelism.
Pros: better for CPU-bound workloads.
Cons: serialization overhead and more complex model/object transfer.
4. Graph/workflow orchestrator-level fan-out.
Pros: richer retries, visibility, and per-stage policies.
Cons: larger architectural footprint than needed for current scope.

## Verification Coverage
- `src/backend/tests/services/test_agent_service.py`
- `test_run_pipeline_for_subquestions_runs_in_parallel_and_preserves_order`
- validates concurrent execution (`elapsed < 0.35` for two 0.2s tasks) and stable output ordering.
- `test_run_runtime_agent_populates_multiple_subquestions_with_verification`
- validates multi-subquestion pipeline population and verification fields in runtime response.
