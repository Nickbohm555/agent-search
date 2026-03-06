# Section 7 Architecture: Per-Subquestion Reranking

## Purpose
Reorder each sub-question's validated documents so the most query-relevant evidence is first before subanswer generation.

## Components
- Reranking logic and config:
[`src/backend/services/reranker_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/reranker_service.py)
- Pipeline integration stage:
[`src/backend/services/agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/agent_service.py)
- Shared retrieval row parser/formatter and document type:
[`src/backend/services/document_validation_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/document_validation_service.py)
- Pipeline state model:
[`src/backend/schemas/agent.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/schemas/agent.py)
- Reranking tests:
[`src/backend/tests/services/test_reranker_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_reranker_service.py),
[`src/backend/tests/services/test_agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_agent_service.py)

## Flow Diagram
```text
+------------------------------------------------------------------------------------------------------+
| Section 6 Output                                                                                     |
|  SubQuestionAnswer[] where sub_answer contains validated rows:                                       |
|  "N. title=... source=... content=..."                                                               |
+----------------------------------------------+-------------------------------------------------------+
                                               |
                                               v
+------------------------------------------------------------------------------------------------------+
| Pipeline Worker (agent_service._run_pipeline_for_single_subquestion)                                 |
|  +------------------------------------------------------------------------------------------------+  |
|  | Step 2 for this item: _apply_reranking_to_sub_qa([item])                                       |  |
|  +------------------------------------------------------------------------------------------------+  |
+----------------------------------------------+-------------------------------------------------------+
                                               |
                                               v
+------------------------------------------------------------------------------------------------------+
| Reranking Stage (agent_service._apply_reranking_to_sub_qa)                                           |
|  +------------------------------------------------------------------------------------------------+  |
|  | parse_retrieved_documents(item.sub_answer) -> RetrievedDocument[]                               |  |
|  | rerank_query = item.expanded_query or item.sub_question                                         |  |
|  | rerank_documents(query, docs, _RERANKER_CONFIG)                                                 |  |
|  | item.sub_answer = format_retrieved_documents(reranked docs with reset ranks)                    |  |
|  +------------------------------------------------------------------------------------------------+  |
+----------------------------------------------+-------------------------------------------------------+
                                               |
                                               v
+------------------------------------------------------------------------------------------------------+
| Reranker Internals (reranker_service)                                                                 |
|  +------------------------------------------------------------------------------------------------+  |
|  | build_reranker_config_from_env()                                                                |  |
|  | _score_document = weighted lexical overlap(title/content/source) + original-rank bias          |  |
|  | scored docs sorted by (-score, original rank)                                                   |  |
|  | optional top_n truncation                                                                        |  |
|  | output: RerankedDocumentScore[] with new rank order                                              |  |
|  +------------------------------------------------------------------------------------------------+  |
+----------------------------------------------+-------------------------------------------------------+
                                               |
                                               v
+------------------------------------------------------------------------------------------------------+
| Section 8 Handoff                                                                                     |
|  sub_answer now carries reranked evidence rows for subanswer generation                               |
+------------------------------------------------------------------------------------------------------+
```

## Data Flow
Inputs:
- `SubQuestionAnswer.sub_answer`: validated document rows from Section 6.
- `SubQuestionAnswer.expanded_query`: preferred reranking query when available.
- `SubQuestionAnswer.sub_question`: fallback reranking query.
- Environment configuration:
`RERANK_TOP_N`,
`RERANK_TITLE_WEIGHT`,
`RERANK_CONTENT_WEIGHT`,
`RERANK_SOURCE_WEIGHT`,
`RERANK_ORIGINAL_RANK_BIAS`.

Transformations:
1. `agent_service` loads `_RERANKER_CONFIG` once at import from environment variables.
2. For each sub-question item, `parse_retrieved_documents(...)` converts row text into typed `RetrievedDocument` objects.
3. Query selection prefers `expanded_query` (from query-expansion stage) and falls back to the raw sub-question.
4. `rerank_documents(...)` computes a score per document:
- token overlap with title, content, and source weighted by config.
- plus a small bias favoring earlier original rank to stabilize ties/noisy scores.
5. Documents are sorted by score descending, optionally truncated to `top_n`, then ranks are reassigned starting from 1.
6. Reranked documents are serialized back into the standard row format and written to `SubQuestionAnswer.sub_answer`.

Outputs:
- `SubQuestionAnswer.sub_answer`: reranked (and possibly truncated) evidence rows for downstream generation.
- Per-document rerank metadata in-memory (`RerankedDocumentScore`): `score`, `original_rank`, `reranked_rank`.
- Observability logs: reranker config at stage start plus before/after counts and top document per sub-question.

Data movement and boundaries:
- Stage boundary: this step mutates only the evidence payload (`sub_answer`) on each `SubQuestionAnswer`.
- Type boundary: plain text rows -> typed docs for scoring -> plain text rows again for compatibility.
- Query boundary: query-expansion output directly influences reranking behavior and final evidence order.

## Key Interfaces / APIs
- Config builder:
`build_reranker_config_from_env() -> RerankerConfig`
- Core reranker:
`rerank_documents(query: str, documents: list[RetrievedDocument], config: RerankerConfig) -> list[RerankedDocumentScore]`
- Internal scorer:
`_score_document(query: str, document: RetrievedDocument, config: RerankerConfig) -> float`
- Pipeline integration point:
`_apply_reranking_to_sub_qa(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]`
- Parser/formatter contract used at boundaries:
`parse_retrieved_documents(...)` and `format_retrieved_documents(...)`

## How It Fits Adjacent Sections
- Upstream dependency (Section 6): consumes validated retrieval rows; quality of validation directly constrains reranking candidates.
- Downstream consumer (Section 8): subanswer generation reads reranked `sub_answer` as its evidence context.
- Follow-on effect (Section 9): subanswer verification checks answers against this reranked evidence, so ranking quality affects answerability outcomes.
- Cross-section linkage (Section 4): `expanded_query` from query expansion is reused as reranking query, coupling expansion quality to ranking quality.

## Tradeoffs
1. Heuristic lexical reranker vs cross-encoder/LLM reranker
- Chosen: weighted lexical overlap with deterministic tie handling.
- Pros: low latency, no extra model dependencies, stable and easily testable behavior.
- Cons: weaker semantic matching for paraphrases/synonyms; may miss intent-level relevance.
- Alternative considered: cross-encoder or LLM scoring per document.
- Why not chosen here: higher compute/cost/latency and operational complexity for this iteration.

2. Preserve row-text stage contract vs pass typed document objects end-to-end
- Chosen: parse row text at stage entry and reformat to row text at exit.
- Pros: minimal integration change with existing pipeline and tests.
- Cons: repeated parse/format overhead and tighter dependence on row syntax stability.
- Alternative considered: keep `RetrievedDocument[]` across all downstream stages.
- Why not chosen here: would require broader refactor across multiple already-implemented sections.

3. Use expanded query for reranking when available vs always use sub-question text
- Chosen: `expanded_query` preferred, `sub_question` fallback.
- Pros: reranking query is often more retrieval-oriented and explicit, improving term match.
- Cons: bad expansions can bias ranking away from true intent.
- Alternative considered: always rerank using the original sub-question.
- Why not chosen here: leaves useful expansion signal unused.

4. Add original-rank bias vs pure content-based reordering
- Chosen: small `original_rank_bias` contributes to score.
- Pros: stabilizes ordering when lexical scores are close; keeps retrieval ranking as a weak prior.
- Cons: can preserve mediocre early-ranked items when scoring signal is weak.
- Alternative considered: zero bias, fully override retrieval rank.
- Why not chosen here: increased tie instability and noisier output ordering.

