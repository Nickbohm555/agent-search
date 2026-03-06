# Section 14 Architecture: Refinement answer path

## Purpose
Execute a second-pass answer pipeline only when Section 12 marks the initial answer as insufficient. Section 14 runs refined sub-questions through the same per-subquestion processing flow, then replaces the runtime output with a refined synthesized answer.

## Components
- Runtime orchestrator: `run_runtime_agent(...)` in `src/backend/services/agent_service.py`
- Refinement retrieval seeding: `_seed_refined_sub_qa_from_retrieval(...)` in `src/backend/services/agent_service.py`
- Retrieval-output formatter: `_format_retrieved_documents_for_pipeline(...)` in `src/backend/services/agent_service.py`
- Shared parallel per-subquestion pipeline: `run_pipeline_for_subquestions(...)` and `_run_pipeline_for_single_subquestion(...)` in `src/backend/services/agent_service.py`
- Final synthesis for refinement pass: `generate_initial_answer(...)` in `src/backend/services/initial_answer_service.py`
- Input/output models: `SubQuestionAnswer`, `RuntimeAgentRunResponse` in `src/backend/schemas/agent.py`

## Data Flow
### Inputs
1. `refined_subquestions: list[str]`
- Produced by Section 13 (`refine_subquestions(...)`).
- Each entry is a narrowed follow-up question targeting missing evidence.

2. Shared runtime state from the first pass
- `vector_store`: created once in `run_runtime_agent(...)` and reused.
- `initial_search_context`: context retrieved from the original user question (Section 2).
- `payload.query`: original user question.

3. Runtime/env controls
- `SUBQUESTION_PIPELINE_MAX_WORKERS` (parallelism for retrieval seeding and per-subquestion pipeline)
- `REFINEMENT_RETRIEVAL_K` (top-k retrieval size for each refined sub-question)
- Synthesis controls from `initial_answer_service.py` (model, temperature, context/sub_qa caps, API key)

### Transformations
1. Refinement gate
- `run_runtime_agent(...)` reaches Section 14 only when Section 12 returned `refinement_needed=True` and Section 13 returned a non-empty refined sub-question list.

2. Refined retrieval seeding (`_seed_refined_sub_qa_from_retrieval`)
- For each refined sub-question, the system calls `search_documents_for_context(...)` with `k=REFINEMENT_RETRIEVAL_K`.
- Calls are run in parallel with `ThreadPoolExecutor`.
- Retrieved documents are normalized into the pipeline format:
`N. title=... source=... content=...`
- Each refined question is converted into an initial `SubQuestionAnswer` record:
- `sub_question`: refined question text
- `sub_answer`: formatted retrieved docs (not a final answer yet)
- `tool_call_input`: JSON string of retrieval inputs
- `expanded_query`: empty string (refinement path does direct query=refined sub-question)
- `sub_agent_response`: empty string

3. Shared per-subquestion processing (`run_pipeline_for_subquestions`)
- Refined `SubQuestionAnswer` items are processed in parallel and index-preserved.
- Each item runs the same stages used in Section 10:
- document validation
- reranking
- subanswer generation
- subanswer verification (`answerable`, `verification_reason`)
- Output is a refined `sub_qa` list with generated/verified answers per refined question.

4. Refined synthesis
- `generate_initial_answer(...)` is called again, now with:
- `main_question=payload.query`
- same `initial_search_context`
- `sub_qa=refined_sub_qa`
- This produces `refined_output` (LLM path or deterministic fallback).

5. Final output override
- On successful refinement pass:
- `output = refined_output`
- `sub_qa = refined_sub_qa`
- `RuntimeAgentRunResponse` returns refined outputs as the final response.

### Outputs
- Final `RuntimeAgentRunResponse.output` is the refined synthesized answer when refinement path runs.
- Final `RuntimeAgentRunResponse.sub_qa` contains refined sub-question answers (not initial-pass sub-questions).

### Data Movement Summary
1. Section 13 emits refined question strings.
2. Section 14 maps each string -> retrieved documents (`SubQuestionAnswer` seed objects).
3. Seed objects flow through the same parallel validation/rerank/answer/verify pipeline as the first pass.
4. Refined `sub_qa` + original question/context flow into synthesis.
5. Refined synthesis output replaces initial output before returning to API caller.

## Key Interfaces and APIs
- `run_runtime_agent(payload: RuntimeAgentRunRequest, db: Session) -> RuntimeAgentRunResponse`
- `_seed_refined_sub_qa_from_retrieval(*, vector_store: Any, refined_subquestions: list[str]) -> list[SubQuestionAnswer]`
- `run_pipeline_for_subquestions(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]`
- `generate_initial_answer(*, main_question: str, initial_search_context: list[dict[str, Any]], sub_qa: list[SubQuestionAnswer]) -> str`

Core data contract used in refinement pass:
- `SubQuestionAnswer.sub_question`: refined question to resolve a gap
- `SubQuestionAnswer.sub_answer`: transitions from retrieved-doc text -> generated answer text
- `SubQuestionAnswer.answerable` and `verification_reason`: verification outputs used by synthesis and observability

## Fit With Adjacent Sections
- Upstream:
- Section 12 decides whether to refine.
- Section 13 generates the refined sub-question set.

- Current section role:
- Section 14 is the execution and synthesis layer for refinement. It performs retrieval-through-verification and produces the replacement final answer.

- Downstream:
- No further processing section in this loop; this section determines the final returned answer when refinement runs.

## Tradeoffs
### Chosen design
Reuse the existing Section 10 per-subquestion pipeline and Section 11 synthesizer for refined sub-questions, with explicit retrieval seeding and final response override.

### Benefits
- High consistency: refined pass uses the same validation/reranking/verification logic as initial pass.
- Lower implementation risk: no duplicate pipeline implementation to keep in sync.
- Good runtime performance: refined retrieval and subquestion processing are parallelized.
- Clean API behavior: caller still receives one `output` and one `sub_qa` list.

### Costs
- Final response drops initial-pass `sub_qa` details once refinement overrides output/state.
- Synthesis function is reused for both initial and refined passes, so role semantics are shared rather than specialized.
- `expanded_query` is not populated on refinement retrieval seed objects, which reduces query-expansion observability on this path.
- Two synthesis calls can add latency when refinement is taken.

### Alternatives considered or rejected
1. Keep both initial and refined outputs in response schema.
- Pros: better client-side traceability and comparison.
- Cons: larger API contract and more UI complexity.

2. Build a separate refinement-specific pipeline.
- Pros: could optimize stages specifically for refinement.
- Cons: duplicates logic from Section 10 and increases maintenance burden.

3. Skip retrieval seeding and use coordinator tool-calls again for refined sub-questions.
- Pros: single orchestration style.
- Cons: less deterministic control of refined execution and harder structured observability.

4. Apply query expansion explicitly on refinement retrieval seeding.
- Pros: potentially better recall for refined queries.
- Cons: extra stage/cost and less predictable direct mapping from refined question text to retrieval input.

## Verification Coverage
- `src/backend/tests/services/test_agent_service.py`
- `test_seed_refined_sub_qa_from_retrieval_builds_retrieved_payloads` verifies refined sub-questions are converted into parseable retrieved-doc `SubQuestionAnswer` seeds with expected retrieval metadata.
- `test_run_runtime_agent_flags_refinement_path_when_decision_true` verifies refinement branch executes end-to-end, invokes second synthesis pass, and returns refined output/refined sub-questions.
