# Section 10 Architecture: Parallel Sub-Question Processing

## Purpose
Execute the per-subquestion pipeline in parallel so each decomposed sub-question independently flows through validation, reranking, subanswer generation, and verification, producing one `SubQuestionAnswer` per input question with deterministic output ordering.

## Components
- Parallel orchestrator and worker stages:
[`src/backend/services/agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/agent_service.py)
- Shared per-item contract:
[`src/backend/schemas/agent.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/schemas/agent.py)
- Stage services executed inside each worker:
[`src/backend/services/document_validation_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/document_validation_service.py),
[`src/backend/services/reranker_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/reranker_service.py),
[`src/backend/services/subanswer_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/subanswer_service.py),
[`src/backend/services/subanswer_verification_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/subanswer_verification_service.py)
- Parallel behavior tests:
[`src/backend/tests/services/test_agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_agent_service.py)

## Flow Diagram
```text
+--------------------------------------------------------------------------------------------------------------------+
| Section 5 Output (post retrieval extraction)                                                                       |
|  sub_qa[]: each item has sub_question, sub_answer(retrieved docs text), expanded_query, tool_call_input           |
+--------------------------------------------------------------+-----------------------------------------------------+
                                                               |
                                                               v
+--------------------------------------------------------------------------------------------------------------------+
| run_pipeline_for_subquestions(sub_qa)                                                                            |
|  +--------------------------------------------------------------------------------------------------------------+  |
|  | configured_workers = max(1, SUBQUESTION_PIPELINE_MAX_WORKERS)                                                |  |
|  | effective_workers = min(configured_workers, len(sub_qa))                                                     |  |
|  | submit one future per item with index                                                                         |  |
|  | collect futures via as_completed                                                                              |  |
|  | write each result into output[index] (order restoration)                                                      |  |
|  +--------------------------------------------------------------------------------------------------------------+  |
+-----------------------------------------+------------------------------+-------------------------------------------+
                                          |                              |
                                          | parallel futures             |
                                          v                              v
+----------------------------------------------------+     +----------------------------------------------------+
| Worker A: _run_pipeline_for_single_subquestion     | ... | Worker N: _run_pipeline_for_single_subquestion     |
|  +------------------------------------------------+ |     |  +------------------------------------------------+ |
|  | 1) _apply_document_validation_to_sub_qa([item])| |     |  | 1) _apply_document_validation_to_sub_qa([item])| |
|  | 2) _apply_reranking_to_sub_qa([item])          | |     |  | 2) _apply_reranking_to_sub_qa([item])          | |
|  | 3) snapshot reranked_output                    | |     |  | 3) snapshot reranked_output                    | |
|  | 4) _apply_subanswer_generation_to_sub_qa([item])| |     |  | 4) _apply_subanswer_generation_to_sub_qa([item])| |
|  | 5) _apply_subanswer_verification_to_sub_qa(...)| |     |  | 5) _apply_subanswer_verification_to_sub_qa(...)| |
|  +------------------------------------------------+ |     |  +------------------------------------------------+ |
+----------------------------------------------------+     +----------------------------------------------------+
                                          |
                                          v
+--------------------------------------------------------------------------------------------------------------------+
| Section 10 Output                                                                                                  |
|  processed_sub_qa[] (same input order): each item now includes final sub_answer + answerable + verification_reason|
+--------------------------------------------------------------------------------------------------------------------+
```

## Data Flow
Inputs:
- `sub_qa: list[SubQuestionAnswer]` from upstream extraction/search stages.
- Each item typically carries:
- `sub_question` (identity key for logs and verification mapping)
- `sub_answer` (retrieved document rows before generation)
- `expanded_query` (preferred rerank query when present)

Transformations:
1. `run_pipeline_for_subquestions(...)` computes worker count from env (`SUBQUESTION_PIPELINE_MAX_WORKERS`) and input size.
2. Each input item is submitted to `_run_pipeline_for_single_subquestion(...)` with its index.
3. Worker deep-copies the item (`model_copy(deep=True)`) to prevent shared mutable state across threads.
4. Inside the worker, data moves through stage sequence:
- document validation filters/reformats retrieved docs
- reranking reorders docs, then snapshot is retained for verification grounding
- subanswer generation overwrites `sub_answer` with synthesized text
- verification uses both synthesized text and snapped reranked evidence, writing `answerable` and `verification_reason`
5. Futures complete out of order, but results are written to `output[index]`, then compacted into ordered `processed`.

Outputs:
- `list[SubQuestionAnswer]` where each item contains:
- final generated `sub_answer`
- `answerable: bool`
- `verification_reason: str`
- original identifying fields (`sub_question`, `expanded_query`, etc.)

Data movement boundaries:
- Entire Section 10 processing is in-memory within backend service runtime.
- No direct DB writes occur in this stage.
- Parallel boundary is at sub-question granularity; each worker owns a single item pipeline.

## Key Interfaces / APIs
- Parallel entrypoint:
`run_pipeline_for_subquestions(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]`
- Single-item worker:
`_run_pipeline_for_single_subquestion(item: SubQuestionAnswer) -> SubQuestionAnswer`
- Supporting stage adapters (called in worker order):
`_apply_document_validation_to_sub_qa(...)`
`_apply_reranking_to_sub_qa(...)`
`_apply_subanswer_generation_to_sub_qa(...)`
`_apply_subanswer_verification_to_sub_qa(...)`
- Runtime caller:
`run_runtime_agent(...)` invokes this function after extraction and before initial-answer synthesis.

## How It Fits Adjacent Sections
- Upstream:
- Section 3 decomposition provides sub-question set.
- Sections 4-5 provide expansion/retrieval artifacts that seed `sub_qa`.
- Section 6-9 logic is executed per item inside this section’s worker.
- Downstream:
- Section 11 consumes the full processed `sub_qa` to synthesize the initial answer.
- Section 12 consumes verification fields to decide whether refinement is required.
- Section 14 reuses the same parallel function for refined sub-questions.

## Tradeoffs
1. ThreadPoolExecutor parallelism vs sequential loop
- Chosen: `ThreadPoolExecutor` with `as_completed`.
- Pros: lower wall-clock latency for multiple sub-questions; simple stdlib dependency.
- Cons: thread scheduling overhead; limited gains if stages are CPU-bound under GIL.
- Alternative considered: sequential processing.
- Why not chosen: linear latency growth with sub-question count.

2. Preserve deterministic output order vs emit completion order
- Chosen: map futures to original indexes and reconstruct ordered output.
- Pros: stable API response ordering and easier test assertions.
- Cons: small memory overhead for indexed output buffer.
- Alternative considered: append results as futures finish.
- Why not chosen: nondeterministic ordering would make downstream/UI behavior noisier.

3. Deep copy per-item state vs mutate shared objects
- Chosen: `model_copy(deep=True)` inside each worker.
- Pros: avoids thread-safety bugs and cross-item contamination.
- Cons: additional allocation/copy cost.
- Alternative considered: mutate original objects directly.
- Why not chosen: unsafe with concurrent execution and harder debugging.

4. Coarse-grained parallelism at sub-question level vs stage-level parallelism
- Chosen: parallelize complete per-item pipelines.
- Pros: clear ownership per worker and minimal synchronization complexity.
- Cons: does not parallelize work inside each stage.
- Alternative considered: parallelize documents/stages globally.
- Why not chosen: higher orchestration complexity and increased shared-state risk.
