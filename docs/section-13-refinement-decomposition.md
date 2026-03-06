# Section 13 Architecture: Refinement decomposition

## Purpose
Generate a focused set of refined sub-questions when Section 12 decides refinement is needed. This section does not retrieve documents or synthesize a final answer; it transforms failure/gap signals from the initial pass into new questions for Section 14.

## Components
- Refinement decomposition service: `refine_subquestions(...)` in `src/backend/services/refinement_decomposition_service.py`
- Sanitization helpers:
- `_normalize_question(...)`
- `_sanitize_refined_subquestions(...)`
- `_extract_llm_subquestions(...)`
- `_fallback_refined_subquestions(...)`
- Orchestration call site: `run_runtime_agent(...)` in `src/backend/services/agent_service.py`
- Input schema dependency: `SubQuestionAnswer` in `src/backend/schemas/agent.py`

## Data Flow
### Inputs
1. `question: str`
- Original user query from runtime request.

2. `initial_answer: str`
- Initial synthesized answer from Section 11.
- Used to inform where coverage is incomplete.

3. `sub_qa: list[SubQuestionAnswer]`
- Verified per-subquestion outcomes from Section 10.
- Fields used directly:
- `sub_question`
- `answerable`
- `verification_reason`
- `sub_answer`

4. Runtime/env controls
- `REFINEMENT_DECOMPOSITION_MODEL` (default `gpt-4.1-mini`)
- `REFINEMENT_DECOMPOSITION_TEMPERATURE` (default `0`)
- `REFINEMENT_DECOMPOSITION_MAX_SUBQUESTIONS` (default `6`, min `1`)
- `OPENAI_API_KEY` (chooses LLM path vs fallback)

### Transformations
1. Section 12 sets `refinement_needed=True`, and `run_runtime_agent(...)` calls:
`refine_subquestions(question=payload.query, initial_answer=output, sub_qa=sub_qa)`.

2. `refine_subquestions(...)` logs input shape (question length, initial answer length, sub_qa count), then chooses a generation path:
- LLM path when `OPENAI_API_KEY` exists.
- Deterministic fallback path when no key, LLM failure, or empty/invalid LLM output.

3. LLM path transformation details:
- Build a prompt with the main question, initial answer, and formatted `sub_qa` list.
- Enforce output contract in prompt: JSON array of complete questions ending with `?`, no repeats of existing sub-questions, max count cap.
- Parse response content using `_extract_llm_subquestions(...)`:
- Accept native list output.
- Else try JSON parse from text.
- Else line-based extraction.
- Sanitize extracted candidates with `_sanitize_refined_subquestions(...)`.

4. Fallback path transformation details:
- Select unresolved items: `answerable == False`.
- Generate candidate questions from each unresolved item:
- Ask for missing evidence specific to the original sub-question.
- If `verification_reason` exists, ask what sources can resolve that reason.
- If no unresolved items, generate one generic evidence-gap question from the main question.
- Sanitize candidates with `_sanitize_refined_subquestions(...)`.

5. Sanitization stage (shared by both paths):
- Normalize punctuation/spacing and force trailing `?`.
- Remove empty strings.
- Deduplicate case-insensitively.
- Exclude questions that match existing initial sub-questions.
- Apply hard cap (`REFINEMENT_DECOMPOSITION_MAX_SUBQUESTIONS`).

### Outputs
- `list[str]` refined sub-questions, normalized and de-duplicated.
- No retrieved documents, no answers, and no verification flags are produced in this section.

### Data Movement Summary
1. Section 10 and 11 produce evidence-quality signals (`sub_qa`) and synthesized answer (`initial_answer`).
2. Section 12 turns those signals into a binary control signal (`refinement_needed`).
3. Section 13 transforms that state into a new question set, preserving only question text.
4. Section 14 consumes those questions to start a new retrieval/validation/rerank/answer/verify pass.

## Key Interfaces and APIs
- `refine_subquestions(*, question: str, initial_answer: str, sub_qa: list[SubQuestionAnswer]) -> list[str]`
- `SubQuestionAnswer` fields consumed:
- `sub_question: str`
- `answerable: bool`
- `verification_reason: str`
- `sub_answer: str`

Runtime orchestration interface:
- In `run_runtime_agent(...)`, refinement branch logs each refined question and passes the list to Section 14 seeding (`_seed_refined_sub_qa_from_retrieval(...)`).

## Fit With Adjacent Sections
- Upstream:
- Section 11 provides `initial_answer` (first synthesis output).
- Section 12 decides if refinement is required and why.
- Section 10 provides structured per-subquestion outcomes used as gap signals.

- Current section role:
- Section 13 is a decomposition-only re-planning layer. It converts gap signals into actionable refined sub-questions but does not do retrieval or synthesis.

- Downstream:
- Section 14 takes refined sub-questions and runs the full per-subquestion pipeline again.
- Final runtime output may be replaced by the refined path result when Section 14 succeeds.

## Tradeoffs
### Chosen design
LLM-first refined question generation with deterministic fallback and strict post-sanitization.

### Benefits
- Better gap targeting than purely template-based rules when model path is available.
- Stable behavior in local/CI/offline environments due to deterministic fallback.
- Strong output hygiene (question normalization, dedupe, exclusion of already-asked questions, max cap).
- Clear operational observability through explicit logs for LLM vs fallback execution.

### Costs
- LLM output quality is prompt-sensitive and may still generate weak or generic questions before sanitization.
- Fallback questions are reliable but less semantically rich, especially for complex domains.
- This section drops richer context (for example, ranking/confidence structures) and emits only question strings.
- Duplicate detection is text-normalization based, so semantic duplicates with different wording can pass.

### Alternatives considered or rejected
1. Deterministic-only decomposition (no LLM path).
- Pros: fully reproducible, no API latency/cost.
- Cons: lower quality for nuanced gap identification and reformulation.

2. LLM-only decomposition (no fallback).
- Pros: potentially best semantic quality.
- Cons: hard runtime dependency on API key and model availability; brittle failure mode.

3. Re-run original decomposition from scratch instead of targeted refinement.
- Pros: simpler implementation, uniform behavior.
- Cons: wastes work and tends to re-ask already explored sub-questions.

4. Emit structured refinement plan objects (priority, rationale, expected evidence types) instead of plain strings.
- Pros: richer downstream control and traceability.
- Cons: larger schema/API surface area and added orchestration complexity beyond this iteration.

## Verification Coverage
- `src/backend/tests/services/test_refinement_decomposition_service.py`
- verifies sanitization removes duplicates and existing questions.
- verifies fallback generates question-shaped, gap-targeting outputs and excludes original sub-questions.

- `src/backend/tests/services/test_agent_service.py`
- `test_run_runtime_agent_flags_refinement_path_when_decision_true` verifies Section 13 is called when refinement is required and refined questions are handed off to the Section 14 path.
