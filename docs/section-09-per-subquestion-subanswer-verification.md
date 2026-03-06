# Section 9 Architecture: Per-subquestion subanswer verification

## Purpose
Determine whether each generated sub-answer is grounded in the reranked evidence for that same sub-question, then persist verification results for downstream refinement decisions.

## Components
- Schema model: `src/backend/schemas/agent.py`
- `SubQuestionAnswer.answerable: bool`
- `SubQuestionAnswer.verification_reason: str`
- Verification service: `src/backend/services/subanswer_verification_service.py`
- `verify_subanswer(sub_question, sub_answer, reranked_retrieved_output)`
- `_extract_tokens(...)` token normalization and stopword filtering
- `SubanswerVerificationResult(answerable, reason)`
- Pipeline integration: `src/backend/services/agent_service.py`
- `_apply_subanswer_verification_to_sub_qa(...)`
- `_run_pipeline_for_single_subquestion(...)` (passes reranked evidence snapshot into verification)
- Evidence parser dependency: `src/backend/services/document_validation_service.py`
- `parse_retrieved_documents(...)` parses `N. title=... source=... content=...` rows

## Data Flow
### Inputs
1. `SubQuestionAnswer.sub_question` from decomposition and per-subquestion execution.
2. `SubQuestionAnswer.sub_answer` after Section 8 generation (natural-language answer text).
3. Reranked evidence snapshot captured before Section 8 overwrites `sub_answer`:
- In `_run_pipeline_for_single_subquestion(...)`, `reranked_output = working_item.sub_answer` is stored after reranking and before generation.
- This snapshot is passed as `reranked_retrieved_output` into verification.

### Transformations
1. `_apply_subanswer_verification_to_sub_qa(...)` iterates each sub-question item and calls `verify_subanswer(...)`.
2. `verify_subanswer(...)` applies deterministic checks in order:
- Empty answer text -> `answerable=False`, reason `empty_subanswer`.
- Phrases like "insufficient evidence" or "cannot determine" -> `answerable=False`, reason `subanswer_reports_insufficient_evidence`.
- Unparseable or missing reranked evidence rows -> `answerable=False`, reason `no_parseable_reranked_documents`.
- Token-overlap grounding check between answer tokens and evidence tokens (title+content), with minimum overlap threshold (`_MIN_EVIDENCE_TOKENS=2`) -> fail gives `insufficient_evidence_overlap`.
- Otherwise -> `answerable=True`, reason `grounded_in_reranked_documents`.
3. Agent pipeline writes verification result back onto the mutable `SubQuestionAnswer`:
- `item.answerable = verification.answerable`
- `item.verification_reason = verification.reason`

### Outputs
- For each sub-question, enriched `SubQuestionAnswer` object with explicit verification status.
- Runtime logs at stage and per-item granularity:
- verification stage start count
- per-question `answerable` and `reason`
- run-end summary including verification fields

### Data Movement Boundaries
- Boundary A (Section 8 -> Section 9): generated answer text enters verification.
- Boundary B (Section 7 snapshot -> Section 9): reranked evidence text is passed separately so verification is based on retrieval evidence, not on generated prose.
- Boundary C (Section 9 -> Section 12): verification fields flow into refinement decision logic (`should_refine(...)`) as part of `sub_qa`.

## Key Interfaces and APIs
- `verify_subanswer(*, sub_question: str, sub_answer: str, reranked_retrieved_output: str) -> SubanswerVerificationResult`
- `SubanswerVerificationResult(answerable: bool, reason: str)`
- `_apply_subanswer_verification_to_sub_qa(sub_qa: list[SubQuestionAnswer], reranked_output_by_sub_question: dict[str, str]) -> list[SubQuestionAnswer]`
- `SubQuestionAnswer` response fields:
- `answerable`
- `verification_reason`

## Fit With Adjacent Sections
- Upstream:
- Section 7 reranking supplies higher-quality evidence rows.
- Section 8 generates one sub-answer from those rows.
- Current section:
- Section 9 verifies whether generated answer text is actually grounded in evidence rows.
- Downstream:
- Section 10 parallel execution runs this check independently per sub-question.
- Section 11 synthesis can prioritize answerable items.
- Section 12 refinement decision uses answerable ratio and reasons to decide whether to refine.

## Tradeoffs
### Chosen design
Use deterministic, rule-based verification (pattern checks + evidence parsing + token overlap), instead of an LLM verifier.

### Benefits
- Predictable and fast verification path with no model-call latency/cost.
- Fully testable and stable in CI/offline environments.
- Reason codes are explicit and machine-friendly for refinement logic.
- Tight data-flow control: verification consumes the exact reranked evidence snapshot used by generation.

### Costs
- Token overlap is a shallow grounding proxy and can produce false negatives on paraphrases.
- Evidence parser depends on strict retrieval-line formatting; format drift can cause `no_parseable_reranked_documents`.
- Hard-coded phrase patterns for "insufficient evidence" are brittle and language-specific.
- No calibrated confidence score; only boolean + reason.

### Alternatives considered or rejected
1. LLM-as-judge verification.
Pros: better semantic grounding checks and paraphrase tolerance.
Cons: extra cost/latency, non-deterministic outcomes, more operational complexity.
2. Citation-required generation and strict citation parsing.
Pros: tighter provenance linkage from answer claims to evidence.
Cons: stronger prompt coupling and brittle parsing if citation format drifts.
3. Embedding-based semantic entailment score.
Pros: richer grounding signal than token overlap.
Cons: more compute, additional thresholds to tune, still imperfect for factual contradiction detection.
4. Store verification as confidence float only.
Pros: finer ranking for downstream decisions.
Cons: requires calibration; boolean gates for refinement become less explicit.

## Verification Coverage
- `src/backend/tests/services/test_subanswer_verification_service.py`
- insufficient-evidence phrase detection
- not-grounded answer detection via overlap failure
- grounded answer success path
- `src/backend/tests/services/test_agent_service.py`
- pipeline writes `answerable` and `verification_reason` onto `SubQuestionAnswer`
- verification receives preserved reranked evidence snapshot
- `src/backend/tests/api/test_agent_run.py`
- API response shape includes verification fields in `sub_qa` items
