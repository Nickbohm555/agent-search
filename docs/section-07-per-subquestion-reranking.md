# Section 7 Architecture: Per-subquestion reranking

## Purpose
Reorder each sub-question's validated document set so the most relevant evidence appears first before subanswer generation.

## Components
- Reranking configuration and scoring models in `src/backend/services/reranker_service.py`:
- `RerankerConfig`
- `RerankedDocumentScore`
- `build_reranker_config_from_env()`
- Lexical reranker implementation in `src/backend/services/reranker_service.py`:
- `_tokenize(...)`
- `_overlap_ratio(...)`
- `_score_document(...)`
- `rerank_documents(...)`
- Pipeline integration step in `src/backend/services/agent_service.py`:
- `_RERANKER_CONFIG`
- `_apply_reranking_to_sub_qa(...)`
- Retrieval text contract reused from validation in `src/backend/services/document_validation_service.py`:
- `parse_retrieved_documents(...)`
- `format_retrieved_documents(...)`
- Pipeline data model in `src/backend/schemas/agent.py`:
- `SubQuestionAnswer`

## Data Flow
### Inputs
1. From Section 6, each `SubQuestionAnswer` contains:
- `sub_question` (human-readable sub-question)
- `expanded_query` (query-expansion output if available)
- `sub_answer` containing validated retrieval rows in line format:
- `N. title=... source=... content=...`
2. Environment-driven reranker knobs:
- `RERANK_TOP_N`
- `RERANK_TITLE_WEIGHT`
- `RERANK_CONTENT_WEIGHT`
- `RERANK_SOURCE_WEIGHT`
- `RERANK_ORIGINAL_RANK_BIAS`

### Transformations and movement
1. At module load, `agent_service` initializes `_RERANKER_CONFIG = build_reranker_config_from_env()`.
2. `_apply_reranking_to_sub_qa(sub_qa)` iterates per sub-question item.
3. `parse_retrieved_documents(item.sub_answer)` converts retrieval text into typed `RetrievedDocument` objects.
4. Query selection chooses `item.expanded_query.strip()` when present, otherwise `item.sub_question`.
5. `rerank_documents(...)` computes a per-document score:
- title overlap ratio * `title_weight`
- content overlap ratio * `content_weight`
- source overlap ratio * `source_weight`
- plus `original_rank_bias / original_rank` to keep slight preference for earlier retriever results
6. Documents are sorted by descending score (then original rank for deterministic tie-breaking).
7. Optional truncation applies if `top_n` is configured.
8. Reranker rewrites ranks to a fresh contiguous order (`1..N`) and returns `RerankedDocumentScore` entries.
9. Pipeline extracts reranked `document` values and serializes them back with `format_retrieved_documents(...)` into `item.sub_answer`.
10. Updated `SubQuestionAnswer` objects continue to Section 8.

### Outputs
- Per-subquestion `sub_answer` remains a retrieval-row string but now in reranked order (and optionally reduced count via `top_n`).
- Reranking observability in logs:
- run-level config values
- per-subquestion `docs_before`, `docs_after`, selected query, and top document
- Stable data contract for downstream consumers because output format is unchanged.

### Data boundaries
- Boundary A: Section 6 validated retrieval text -> parsed typed `RetrievedDocument` list.
- Boundary B: typed docs + query + config -> scored/reranked typed docs.
- Boundary C: reranked typed docs -> retrieval text written back to `SubQuestionAnswer.sub_answer`.
- Boundary D: Section 7 output -> Section 8 subanswer generation input.

## Key Interfaces and APIs
- `build_reranker_config_from_env() -> RerankerConfig`
- `rerank_documents(query: str, documents: list[RetrievedDocument], config: RerankerConfig) -> list[RerankedDocumentScore]`
- `_apply_reranking_to_sub_qa(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]`
- `parse_retrieved_documents(retrieved_output: str) -> list[RetrievedDocument]`
- `format_retrieved_documents(documents: list[RetrievedDocument]) -> str`

## Fit With Adjacent Sections
- Upstream: Section 6 filters noisy documents but keeps retrieval ordering mostly unchanged.
- Current section: Section 7 optimizes ordering (and optional cut-down) without changing the retrieval text schema.
- Downstream: Section 8 consumes reranked evidence from `sub_answer` to generate subanswers.
- Downstream: Section 9 verifies generated subanswers against this reranked evidence snapshot.
- Pipeline placement: In `agent_service`, reranking is executed after validation and before subanswer generation inside `_run_pipeline_for_single_subquestion(...)`.

## Tradeoffs
### Chosen design
A deterministic lexical reranker with configurable weights and optional top-N cutoff, operating on already-validated documents.

### Benefits
- Fast, local, and low-cost reranking with no extra model/network dependency.
- Deterministic behavior helps testing and debugging.
- Reuses existing retrieval line format, minimizing integration surface.
- Weight and top-N tuning are runtime-configurable via environment variables.

### Costs
- Lexical overlap can miss semantically relevant documents with low token overlap.
- Mutating `sub_answer` in place means the pre-rerank ordering is not retained on the object unless separately captured.
- If retrieval formatting drifts, parsing may fail and reranking is skipped.
- Global env-based config is coarse-grained (same behavior for all queries/tenants).

### Alternatives considered or rejected
1. Cross-encoder reranker model (e.g., sentence-transformers reranking).
Pros: stronger semantic ordering quality.
Cons: higher latency/resource cost; extra dependency/runtime complexity.
2. LLM-as-reranker.
Pros: better handling of nuanced relevance and intent.
Cons: nondeterminism, token cost, and slower response times.
3. Keep retriever order only (no reranking stage).
Pros: simplest pipeline and fewer moving parts.
Cons: downstream answer quality depends entirely on initial retrieval rank quality.
4. Switch pipeline to structured JSON docs end-to-end instead of formatted strings.
Pros: safer contracts and less parsing fragility.
Cons: larger refactor across extraction, validation, reranking, generation, and API serialization.

## Verification Coverage
- Unit tests in `src/backend/tests/services/test_reranker_service.py` cover relevance-based reorder and `top_n` truncation.
- Pipeline tests in `src/backend/tests/services/test_agent_service.py` verify `_apply_reranking_to_sub_qa(...)` updates order and feeds later stages.
