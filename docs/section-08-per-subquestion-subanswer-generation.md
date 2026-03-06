# Section 8 Architecture: Per-subquestion subanswer generation

## Purpose
Generate one concise, evidence-grounded sub-answer per sub-question using the reranked document set from Section 7.

## Components
- Subanswer generation service in `src/backend/services/subanswer_service.py`:
- `generate_subanswer(...)`
- `_build_context_block(...)`
- `_build_fallback_subanswer(...)`
- Pipeline integration in `src/backend/services/agent_service.py`:
- `_apply_subanswer_generation_to_sub_qa(...)`
- `_run_pipeline_for_single_subquestion(...)`
- Retrieval parsing contract from `src/backend/services/document_validation_service.py`:
- `parse_retrieved_documents(...)`
- `format_retrieved_documents(...)` (upstream producer used by Section 7)
- Data model in `src/backend/schemas/agent.py`:
- `SubQuestionAnswer` (`sub_question`, mutable `sub_answer` field)

## Data Flow
### Inputs
1. From Section 7, each `SubQuestionAnswer` arrives with:
- `sub_question`: natural-language question to answer.
- `sub_answer`: reranked retrieval rows in line format `N. title=... source=... content=...`.
2. Runtime config from environment:
- `SUBANSWER_MODEL` (default `gpt-4.1-mini`)
- `SUBANSWER_TEMPERATURE` (default `0`)
- `SUBANSWER_MAX_CONTEXT_DOCS` (default `3`)
- `OPENAI_API_KEY` (controls LLM vs fallback path)

### Transformations and movement
1. `agent_service._apply_subanswer_generation_to_sub_qa(...)` iterates through each sub-question item.
2. For each item, current `item.sub_answer` (reranked docs text) is copied to `prior_output` and passed into `generate_subanswer(sub_question, reranked_retrieved_output=prior_output)`.
3. `generate_subanswer(...)` parses the reranked text with `parse_retrieved_documents(...)`.
4. If parsing yields no docs, service returns deterministic fallback: `No relevant evidence found in reranked documents.`
5. If docs parse successfully:
- Build a bounded context block from top `SUBANSWER_MAX_CONTEXT_DOCS` docs.
- Build deterministic fallback answer from top doc content + source attribution.
6. LLM decision branch:
- If `OPENAI_API_KEY` missing, return fallback immediately.
- Otherwise call `ChatOpenAI(...).invoke(prompt)` with constraints: evidence-only, 1-3 sentences, include source attribution, admit insufficiency when needed.
7. Output handling:
- Non-empty LLM response becomes the sub-answer.
- Empty/exception path falls back to deterministic answer.
8. The generated answer replaces `item.sub_answer` in place.
9. In the per-item pipeline (`_run_pipeline_for_single_subquestion(...)`), a snapshot of reranked evidence is retained in local `reranked_output` before replacement, then passed to Section 9 verification so verification still evaluates against evidence, not against rewritten answer text.

### Outputs
- Per sub-question, `SubQuestionAnswer.sub_answer` changes from reranked evidence rows to concise answer text.
- Logs emitted for observability:
- stage start count
- per-question generation completion and answer length
- fallback reasons (missing API key, parse failure, LLM failure)

### Data boundaries
- Boundary A: Section 7 structured retrieval-text contract enters Section 8.
- Boundary B: retrieval text is parsed into `RetrievedDocument` objects for generation context.
- Boundary C: generation output is plain answer text written back onto `SubQuestionAnswer.sub_answer`.
- Boundary D: Section 9 consumes answer text plus separately preserved reranked evidence snapshot for verification.

## Key Interfaces and APIs
- `generate_subanswer(sub_question: str, reranked_retrieved_output: str) -> str`
- `_apply_subanswer_generation_to_sub_qa(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]`
- `parse_retrieved_documents(retrieved_output: str) -> list[RetrievedDocument]`
- `_run_pipeline_for_single_subquestion(item: SubQuestionAnswer) -> SubQuestionAnswer` (integration point keeping evidence snapshot)

## Fit With Adjacent Sections
- Upstream: Section 7 reranking provides better-ordered evidence and stable retrieval text format.
- Current section: Section 8 converts evidence into user-readable sub-answers with attribution/fallback behavior.
- Downstream: Section 9 verifies each generated sub-answer against the preserved reranked evidence.
- Pipeline order: validation -> reranking -> subanswer generation -> verification (implemented in `_run_pipeline_for_single_subquestion(...)`).

## Tradeoffs
### Chosen design
Use a dedicated subanswer service with LLM-first generation and deterministic fallback, operating on a text-based retrieval contract.

### Benefits
- Robust execution: produces an answer even without API key or when LLM call fails.
- Bounded context (`SUBANSWER_MAX_CONTEXT_DOCS`) keeps latency and token usage predictable.
- Clear stage responsibility: Section 8 only generates answers; Section 9 handles correctness/answerability checks.
- Prompt-level attribution requirement improves traceability of answer statements.

### Costs
- `SubQuestionAnswer.sub_answer` is overloaded across stages (docs text before Section 8, answer text after), increasing coupling and making type semantics less explicit.
- Module-level `_OPENAI_API_KEY` is read at import time; runtime env changes are not picked up until process restart.
- Fallback answer quality depends on first reranked document and can be terse or lossy for multi-source questions.
- Text parsing contract is brittle; formatting drift in upstream retrieval lines can force fallback path.

### Alternatives considered or rejected
1. Keep retrieval docs and generated answer in separate schema fields.
Pros: cleaner type contract and easier debugging across stages.
Cons: broader schema/API refactor across pipeline and tests.
2. Force LLM-only generation (no deterministic fallback).
Pros: potentially higher fluency and nuance.
Cons: fragile in offline/misconfigured environments; higher cost and latency.
3. Generate subanswers in coordinator/subagent only.
Pros: fewer backend pipeline functions.
Cons: weaker stage isolation and harder deterministic testing/observability.
4. Pass full reranked set to LLM without doc cap.
Pros: potentially more complete evidence coverage.
Cons: higher token cost, slower responses, and increased prompt noise.

## Verification Coverage
- `src/backend/tests/services/test_subanswer_service.py` covers:
- fallback when reranked docs are non-parseable
- LLM path behavior via monkeypatched `ChatOpenAI`
- `src/backend/tests/services/test_agent_service.py` verifies pipeline integration updates `SubQuestionAnswer.sub_answer` via subanswer generation stage.
