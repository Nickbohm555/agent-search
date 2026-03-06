# Section 8 Architecture: Per-Subquestion Subanswer Generation

## Purpose
Convert each sub-question's reranked evidence rows into one concise, source-attributed subanswer string that downstream stages can verify and synthesize.

## Components
- Subanswer generation service:
[`src/backend/services/subanswer_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/subanswer_service.py)
- Pipeline stage integration:
[`src/backend/services/agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/agent_service.py)
- Shared `SubQuestionAnswer` runtime shape:
[`src/backend/schemas/agent.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/schemas/agent.py)
- API boundary that returns generated subanswers to UI:
[`src/backend/routers/agent.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/routers/agent.py)
- Frontend response contract/rendering of `sub_qa[*].sub_answer`:
[`src/frontend/src/utils/api.ts`](/Users/nickbohm/Desktop/worktree/agent-search/src/frontend/src/utils/api.ts),
[`src/frontend/src/App.tsx`](/Users/nickbohm/Desktop/worktree/agent-search/src/frontend/src/App.tsx)
- Tests for generation behavior and pipeline wiring:
[`src/backend/tests/services/test_subanswer_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_subanswer_service.py),
[`src/backend/tests/services/test_agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_agent_service.py)

## Flow Diagram
```text
+----------------------------------------------------------------------------------------------------------------------+
| Section 7 Output                                                                                                     |
|  SubQuestionAnswer[] where sub_answer is reranked evidence rows:                                                     |
|  "1. title=... source=... content=..."                                                                               |
+----------------------------------------------------+-----------------------------------------------------------------+
                                                     |
                                                     v
+----------------------------------------------------------------------------------------------------------------------+
| Per-Subquestion Pipeline Worker (agent_service._run_pipeline_for_single_subquestion)                                |
|  +----------------------------------------------------------------------------------------------------------------+  |
|  | ... document_validation -> reranking -> _apply_subanswer_generation_to_sub_qa([item]) -> verification ...     |  |
|  +----------------------------------------------------------------------------------------------------------------+  |
+----------------------------------------------------+-----------------------------------------------------------------+
                                                     |
                                                     v
+----------------------------------------------------------------------------------------------------------------------+
| Generation Stage Adapter (agent_service._apply_subanswer_generation_to_sub_qa)                                      |
|  +----------------------------------------------------------------------------------------------------------------+  |
|  | prior_output = item.sub_answer                                                                                  |  |
|  | item.sub_answer = generate_subanswer(sub_question=item.sub_question, reranked_retrieved_output=prior_output)  |  |
|  | emits per-item logs with generated length                                                                        |  |
|  +----------------------------------------------------------------------------------------------------------------+  |
+----------------------------------------------------+-----------------------------------------------------------------+
                                                     |
                                                     v
+----------------------------------------------------------------------------------------------------------------------+
| Subanswer Service (subanswer_service.generate_subanswer)                                                             |
|  +----------------------------------------------------------------------------------------------------------------+  |
|  | parse_retrieved_documents(reranked_retrieved_output) -> RetrievedDocument[]                                     |  |
|  | if docs missing: "No relevant evidence found in reranked documents."                                            |  |
|  | else build context block from top N docs (SUBANSWER_MAX_CONTEXT_DOCS)                                           |  |
|  | if OPENAI_API_KEY missing: deterministic fallback from top doc + source                                          |  |
|  | else LLM call (ChatOpenAI) with concise/attributed prompt                                                        |  |
|  | on empty/error: fallback to deterministic top-doc answer                                                         |  |
|  +----------------------------------------------------------------------------------------------------------------+  |
+----------------------------------------------------+-----------------------------------------------------------------+
                                                     |
                                                     v
+----------------------------------------------------------------------------------------------------------------------+
| Section 9 Input                                                                                                      |
|  SubQuestionAnswer.sub_answer now contains generated natural-language subanswer, ready for verification             |
+----------------------------------------------------------------------------------------------------------------------+
```

## Data Flow
Inputs:
- `SubQuestionAnswer.sub_question`: question being answered.
- `SubQuestionAnswer.sub_answer`: reranked evidence text rows from Section 7.
- Environment:
`OPENAI_API_KEY`,
`SUBANSWER_MODEL` (default `gpt-4.1-mini`),
`SUBANSWER_TEMPERATURE` (default `0`),
`SUBANSWER_MAX_CONTEXT_DOCS` (default `3`).

Transformations:
1. Pipeline stage receives `sub_qa` items after reranking and snapshots each item's current `sub_answer` as `prior_output`.
2. `generate_subanswer(...)` parses `prior_output` into typed `RetrievedDocument[]` using the shared row parser.
3. Context shaping narrows payload to top `N` docs and normalizes each row into `[index] title/source/content` lines.
4. Decision branch:
- no parseable docs: fixed insufficient-evidence message.
- parseable docs + no API key: deterministic fallback answer from top doc content plus source attribution.
- parseable docs + API key: LLM prompt constrained to provided evidence only, 1-3 sentences, with attribution.
5. Failure handling branch for LLM path:
- if LLM response is empty or raises an exception, service logs and falls back to deterministic top-doc answer.
6. Stage writes the final answer string back to `SubQuestionAnswer.sub_answer`.

Outputs:
- Updated `SubQuestionAnswer.sub_answer`: concise answer text, ideally with `(source: ...)`.
- Logs for observability:
`Per-subquestion subanswer generation start`,
`Per-subquestion subanswer generated`,
fallback/skip reasons from `subanswer_service`.
- API response carries these generated values in `RuntimeAgentRunResponse.sub_qa`, which frontend displays in the "Subquestions & subanswers" panel.

Data movement and boundaries:
- In-memory only for this stage: no database writes and no schema migration.
- Format boundary: evidence row text -> typed docs -> prompt/fallback output text.
- Contract boundary: same `sub_answer` field is reused across stages with changing semantics:
Section 7 = reranked evidence rows, Section 8 = generated answer text.

## Key Interfaces / APIs
- Generation entrypoint:
`generate_subanswer(sub_question: str, reranked_retrieved_output: str) -> str`
- Pipeline integration point:
`_apply_subanswer_generation_to_sub_qa(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]`
- Pipeline ordering in single-item worker:
`document_validation -> reranking -> subanswer_generation -> subanswer_verification`
- API endpoint returning generated subanswers:
`POST /api/agents/run` via `runtime_agent_run(...)` / `run_runtime_agent(...)`
- Frontend runtime contract:
`RuntimeAgentRunResponse.sub_qa[].sub_answer`

## How It Fits Adjacent Sections
- Upstream (Section 7 reranking): Section 8 depends on reranked order to decide which evidence is most salient in prompt/fallback context.
- Downstream (Section 9 verification): verification compares generated subanswer text against preserved reranked evidence to set `answerable` and `verification_reason`.
- Downstream synthesis (Section 11 initial answer): generated (and later verified) subanswers are aggregated into the final user-facing answer.
- Cross-cutting with Section 10: this stage runs inside each parallel sub-question worker, so latency behavior scales with worker count and LLM/fallback branch used.

## Tradeoffs
1. Reuse `sub_answer` field for both evidence rows and generated answer text vs introduce separate fields
- Chosen: reuse `SubQuestionAnswer.sub_answer`.
- Pros: no schema/API expansion, minimal churn across backend and frontend, faster iteration.
- Cons: same field meaning changes between stages, which can confuse debugging and future extensions.
- Alternative considered: add dedicated fields like `reranked_evidence` and `generated_subanswer`.
- Why not chosen here: broader refactor across extraction/reranking/verification/UI contracts.

2. LLM-first generation with deterministic fallback vs deterministic-only summarization
- Chosen: LLM generation when key is available, fallback otherwise.
- Pros: better fluency and synthesis when model is present; resilient behavior without credentials.
- Cons: variable output quality/latency/cost when LLM path is active; branch-dependent behavior across environments.
- Alternative considered: always deterministic top-document extraction.
- Why not chosen here: produces brittle low-quality answers for multi-document evidence.

3. Top-N context truncation (`SUBANSWER_MAX_CONTEXT_DOCS`) vs sending all reranked docs
- Chosen: bounded context window from highest-ranked docs.
- Pros: predictable token usage and latency, stronger focus on highest-signal evidence.
- Cons: lower-ranked but important evidence may be omitted from generation context.
- Alternative considered: include all reranked docs.
- Why not chosen here: higher prompt cost and noisier generation with long evidence lists.

4. Strict "evidence-only" prompt constraints vs allowing model prior knowledge
- Chosen: explicit prompt instruction to use only provided evidence.
- Pros: reduces hallucination risk and aligns with later verification requirements.
- Cons: can produce "insufficient evidence" even when the model knows background facts.
- Alternative considered: permit general world knowledge to fill gaps.
- Why not chosen here: weakens traceability to retrieved sources and conflicts with verification stage intent.

5. Fallback answer from top document only vs multi-document fallback synthesis
- Chosen: deterministic top-document content with source.
- Pros: simple, predictable, and robust under failure paths.
- Cons: may ignore corroborating or contradictory lower-ranked documents.
- Alternative considered: merge multiple documents in fallback algorithm.
- Why not chosen here: extra complexity for edge path and higher risk of heuristic errors.
