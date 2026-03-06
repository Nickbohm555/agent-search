# Section 11 Architecture: Initial answer generation

## Purpose
Produce the first user-facing answer by combining two evidence streams after the per-subquestion pipeline completes:
- initial retrieval context from the main question (Section 2)
- processed `sub_qa` items with verification signals from Section 10

## Components
- Orchestration caller: `run_runtime_agent(...)` in `src/backend/services/agent_service.py`
- Initial synthesis service: `generate_initial_answer(...)` in `src/backend/services/initial_answer_service.py`
- Data model: `SubQuestionAnswer` in `src/backend/schemas/agent.py`
- LLM adapter: `ChatOpenAI` (model from `INITIAL_ANSWER_MODEL`, default `gpt-4.1-mini`)
- Fallback synthesizer: `_build_fallback_initial_answer(...)` when no API key, LLM failure, or empty LLM output

## Data Flow
### Inputs
1. `main_question: str`
- Original runtime query from `RuntimeAgentRunRequest.query`.

2. `initial_search_context: list[dict[str, Any]]`
- Built earlier from vector retrieval (`build_initial_search_context(...)`).
- Each item can include `title`, `source`, `snippet`.

3. `sub_qa: list[SubQuestionAnswer]`
- Produced by Section 10 pipeline.
- Critical fields used here:
- `sub_answer` (generated subanswer text)
- `answerable` and `verification_reason` (verification outputs)
- `sub_question` (traceability)

### Transformations
1. In `run_runtime_agent(...)`, after `run_pipeline_for_subquestions(...)`, the service calls:
`generate_initial_answer(main_question=payload.query, initial_search_context=initial_search_context, sub_qa=sub_qa)`.

2. `generate_initial_answer(...)` prepares a deterministic fallback first:
- Prefer concatenating `sub_answer` from entries where `answerable=True`.
- If none are answerable, use any non-empty subanswers.
- If no subanswers, use top initial-context snippet + source.
- If no evidence exists, return an explicit insufficient-evidence message.

3. If `OPENAI_API_KEY` is set, the service builds an LLM prompt that includes:
- main question
- formatted initial context (capped by `INITIAL_ANSWER_MAX_CONTEXT_ITEMS`)
- formatted sub-question answers (capped by `INITIAL_ANSWER_MAX_SUBQAS`)
- synthesis rules (concise length, prefer verified evidence, include uncertainty and source attribution)

4. LLM execution path:
- `ChatOpenAI(...).invoke(prompt)` returns the synthesized answer if non-empty.
- On exception or empty response, control returns to fallback output.

### Outputs
- `output: str` initial answer for downstream runtime response.
- `run_runtime_agent(...)` sets this value as the answer state used by Section 12 refinement decision.

### Data Movement Summary
1. Section 2 retrieval summary (`initial_search_context`) and Section 10 verified subanswers (`sub_qa`) converge at one boundary: `generate_initial_answer(...)`.
2. The service merges evidence into one text answer, with explicit preference ordering (verified subanswers -> any subanswers -> initial context -> insufficient evidence).
3. That merged answer is passed to Section 12 (`should_refine(...)`) as `initial_answer`.

## Key Interfaces and APIs
- `generate_initial_answer(*, main_question: str, initial_search_context: list[dict[str, Any]], sub_qa: list[SubQuestionAnswer]) -> str`
- Internal formatting helpers:
- `_format_initial_context(...)`
- `_format_sub_qa(...)`
- Internal deterministic fallback helper:
- `_build_fallback_initial_answer(...)`

Environment-driven controls:
- `INITIAL_ANSWER_MODEL`
- `INITIAL_ANSWER_TEMPERATURE`
- `INITIAL_ANSWER_MAX_CONTEXT_ITEMS`
- `INITIAL_ANSWER_MAX_SUBQAS`
- `OPENAI_API_KEY`

## Fit With Adjacent Sections
- Upstream dependencies:
- Section 2 provides the initial retrieval context for broad grounding.
- Section 10 provides per-subquestion synthesized and verified evidence.

- Current section role:
- Section 11 is the first cross-stream synthesis point where broad context and decomposed evidence are merged into one user-facing answer.

- Downstream consumers:
- Section 12 uses this answer plus `sub_qa` to decide whether refinement is required.
- If refinement is needed (Sections 13-14), this same synthesis service is reused for refined subquestions.

## Tradeoffs
### Chosen design
Use a hybrid synthesis strategy: LLM-first when available, with deterministic fallback always precomputed.

### Benefits
- High resilience: answer generation still works without external LLM availability.
- Predictable minimum behavior in tests and offline environments.
- Clear data-priority policy: verified evidence is favored before weaker signals.
- Reusable synthesis interface for both initial and refined answer paths.

### Costs
- Fallback answer quality can be less coherent because it mostly concatenates evidence.
- Prompt-based synthesis depends on source text formatting quality from upstream stages.
- Hard caps (`MAX_CONTEXT_ITEMS`, `MAX_SUBQAS`) can omit potentially useful evidence in large runs.
- Service currently returns plain text only; no structured citation object is emitted.

### Alternatives considered or rejected
1. Use coordinator raw final message as the runtime output.
- Pros: less code, no extra synthesis step.
- Cons: weaker control over evidence priority and harder to guarantee consistent output behavior.

2. Always require LLM synthesis (no fallback).
- Pros: more fluent and consistent narrative quality.
- Cons: runtime hard dependency on API credentials/availability; brittle in local and CI contexts.

3. Template-only deterministic synthesis (no LLM path).
- Pros: fully reproducible and cheaper.
- Cons: lower answer quality for multi-evidence or ambiguous questions.

4. Structured output (answer + citations + confidence) instead of a single string.
- Pros: stronger downstream UX and auditability.
- Cons: requires schema/UI/API updates beyond this section scope.

## Verification Coverage
- `src/backend/tests/services/test_initial_answer_service.py`
- verifies fallback preference for answerable subanswers.
- verifies fallback uses initial context when subanswers are missing.

- `src/backend/tests/services/test_agent_service.py`
- `test_run_runtime_agent_generates_initial_answer_and_logs` verifies Section 11 synthesis hook, input handoff, and output assignment.
- refinement-path test confirms Section 11 synthesis is reused after refinement in Section 14.
