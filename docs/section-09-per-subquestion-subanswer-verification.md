# Section 9 Architecture: Per-Subquestion Subanswer Verification

## Purpose
Determine whether each generated subanswer is actually supported by its reranked evidence, and persist a machine-usable verification result (`answerable` + `verification_reason`) for downstream refinement decisions.

## Components
- Verification service and decision rules:
[`src/backend/services/subanswer_verification_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/subanswer_verification_service.py)
- Pipeline integration stage (verification wiring):
[`src/backend/services/agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/agent_service.py)
- Shared schema fields carrying verification output:
[`src/backend/schemas/agent.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/schemas/agent.py)
- Verification-focused unit tests:
[`src/backend/tests/services/test_subanswer_verification_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_subanswer_verification_service.py),
[`src/backend/tests/services/test_agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_agent_service.py)
- API response contract coverage for verification fields:
[`src/backend/tests/api/test_agent_run.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/api/test_agent_run.py)

## Flow Diagram
```text
+------------------------------------------------------------------------------------------------------------------+
| Section 8 Output                                                                                                 |
|  SubQuestionAnswer[] per item:                                                                                   |
|  - sub_question                                                                                                  |
|  - sub_answer (generated NL answer text)                                                                         |
|  - reranked evidence is still available in worker-local snapshot                                                  |
+------------------------------------------------------+-----------------------------------------------------------+
                                                       |
                                                       v
+------------------------------------------------------------------------------------------------------------------+
| Per-Subquestion Worker (agent_service._run_pipeline_for_single_subquestion)                                     |
|  +------------------------------------------------------------------------------------------------------------+  |
|  | 1) _apply_document_validation_to_sub_qa([item])                                                            |  |
|  | 2) _apply_reranking_to_sub_qa([item])                                                                       |  |
|  | 3) reranked_output = working_item.sub_answer   (snapshot evidence rows)                                     |  |
|  | 4) _apply_subanswer_generation_to_sub_qa([item])  -> item.sub_answer becomes generated answer text         |  |
|  | 5) _apply_subanswer_verification_to_sub_qa([item], reranked_output_by_sub_question={...})                 |  |
|  +------------------------------------------------------------------------------------------------------------+  |
+------------------------------------------------------+-----------------------------------------------------------+
                                                       |
                                                       v
+------------------------------------------------------------------------------------------------------------------+
| Verification Stage Adapter (agent_service._apply_subanswer_verification_to_sub_qa)                              |
|  +------------------------------------------------------------------------------------------------------------+  |
|  | verification = verify_subanswer(sub_question, sub_answer, reranked_retrieved_output)                       |  |
|  | item.answerable = verification.answerable                                                                    |  |
|  | item.verification_reason = verification.reason                                                               |  |
|  +------------------------------------------------------------------------------------------------------------+  |
+------------------------------------------------------+-----------------------------------------------------------+
                                                       |
                                                       v
+------------------------------------------------------------------------------------------------------------------+
| Verification Engine (subanswer_verification_service.verify_subanswer)                                            |
|  +------------------------------------------------------------------------------------------------------------+  |
|  | A) Empty answer check -> empty_subanswer                                                                     |  |
|  | B) Explicit "insufficient evidence" phrase check -> subanswer_reports_insufficient_evidence                |  |
|  | C) parse_retrieved_documents(reranked_retrieved_output)                                                      |  |
|  |    - none parseable -> no_parseable_reranked_documents                                                       |  |
|  | D) Token grounding check (answer tokens ∩ evidence tokens)                                                   |  |
|  |    - overlap < 2 -> insufficient_evidence_overlap                                                            |  |
|  | E) Otherwise -> grounded_in_reranked_documents (answerable=True)                                             |  |
|  +------------------------------------------------------------------------------------------------------------+  |
+------------------------------------------------------+-----------------------------------------------------------+
                                                       |
                                                       v
+------------------------------------------------------------------------------------------------------------------+
| Section 12 Input                                                                                                 |
|  Each SubQuestionAnswer now includes verification outputs used by refinement decision logic                      |
+------------------------------------------------------------------------------------------------------------------+
```

## Data Flow
Inputs:
- `sub_question`: identity key for each sub-pipeline item.
- `sub_answer`: generated answer text from Section 8.
- `reranked_retrieved_output`: evidence rows captured before generation overwrites `sub_answer`.

Transformations:
1. In `_run_pipeline_for_single_subquestion(...)`, reranked evidence rows are snapshotted in `reranked_output` before generation mutates `sub_answer`.
2. `_apply_subanswer_verification_to_sub_qa(...)` passes `(sub_question, generated sub_answer, reranked_output)` into `verify_subanswer(...)`.
3. `verify_subanswer(...)` performs deterministic checks in order:
- answer text presence;
- insufficient-evidence phrase detection;
- parseability of reranked evidence rows;
- lexical grounding overlap between answer tokens and evidence tokens.
4. Service returns `SubanswerVerificationResult(answerable, reason)`.
5. Pipeline writes results back onto each `SubQuestionAnswer` as `answerable` and `verification_reason`.

Outputs:
- `SubQuestionAnswer.answerable: bool`
- `SubQuestionAnswer.verification_reason: str`
- Structured logs per item from `agent_service` showing verification result and reason.

Data movement and boundaries:
- Entire Section 9 execution is in-memory inside backend service code; no direct database writes.
- Input contract boundary: generated free-form answer text + reranked row-formatted evidence text.
- Output contract boundary: explicit typed verification fields that later sections consume (`should_refine(...)`, refinement decomposition, and response payload).

## Key Interfaces / APIs
- Verification core:
`verify_subanswer(*, sub_question: str, sub_answer: str, reranked_retrieved_output: str) -> SubanswerVerificationResult`
- Verification result type:
`SubanswerVerificationResult(answerable: bool, reason: str)`
- Pipeline integration point:
`_apply_subanswer_verification_to_sub_qa(sub_qa: list[SubQuestionAnswer], *, reranked_output_by_sub_question: dict[str, str]) -> list[SubQuestionAnswer]`
- Schema contract returned by API:
`SubQuestionAnswer.answerable`, `SubQuestionAnswer.verification_reason`

## How It Fits Adjacent Sections
- Upstream dependency (Section 8): consumes generated subanswers; quality and phrasing of Section 8 outputs directly affect verification outcomes.
- Upstream dependency (Section 7): verification grounding relies on reranked evidence rows produced before generation.
- Downstream consumer (Section 10): runs as the last step in each parallel per-subquestion worker.
- Downstream consumer (Section 12): refinement decision uses aggregate answerable/unanswerable status and reasons to decide whether refinement is needed.
- API/UI impact: verification fields are part of the runtime response shape validated in API tests.

## Tradeoffs
1. Deterministic lexical grounding vs LLM-based verification
- Chosen: deterministic rule/token-overlap checks.
- Pros: predictable, cheap, fast, and testable.
- Cons: misses semantic equivalence/paraphrases where token overlap is low.
- Alternative considered: LLM judge over answer+evidence.
- Why not chosen: adds latency/cost and non-determinism at a critical gating stage.

2. Preserve reranked evidence snapshot in worker vs read current `sub_answer` during verification
- Chosen: snapshot reranked evidence before generation and pass separately.
- Pros: avoids losing evidence when `sub_answer` is overwritten by generated text.
- Cons: requires explicit mapping plumbing (`reranked_output_by_sub_question`).
- Alternative considered: add a dedicated `reranked_evidence` field to schema.
- Why not chosen: larger schema/API refactor across sections.

3. Binary `answerable` with reason codes vs probabilistic confidence score
- Chosen: boolean + categorical reason string.
- Pros: simple control flow for refinement decisions and easier debugging.
- Cons: lower granularity; borderline answers collapse into binary outcomes.
- Alternative considered: numeric confidence with thresholds.
- Why not chosen: would require calibration and broader downstream policy changes.

4. Phrase-based insufficient-evidence detection vs purely evidence-overlap detection
- Chosen: explicit phrase check plus overlap check.
- Pros: catches self-reported non-answers quickly and consistently.
- Cons: brittle to wording variations not in pattern list.
- Alternative considered: only overlap-based validation.
- Why not chosen: misses clear abstentions phrased as natural language.
