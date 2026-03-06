# Section 6 Architecture: Per-subquestion document validation (parallel)

## Purpose
Filter each sub-question's retrieved documents before reranking so downstream steps only process documents that pass configurable constraints (relevance, source, and date rules).

## Components
- Validation models and config:
- `RetrievedDocument`, `DocumentValidationConfig`, `ValidatedDocumentResult`, `SubQuestionValidationResult` in `src/backend/services/document_validation_service.py`.
- Environment-driven config loader:
- `build_document_validation_config_from_env()` in `src/backend/services/document_validation_service.py`.
- Retrieval row parsing/formatting contract:
- `parse_retrieved_documents(...)` and `format_retrieved_documents(...)` in `src/backend/services/document_validation_service.py`.
- Per-document validator:
- `_validate_document(...)` (relevance/source/year checks) in `src/backend/services/document_validation_service.py`.
- Parallel per-document executor:
- `validate_subquestion_documents(...)` using `ThreadPoolExecutor` in `src/backend/services/document_validation_service.py`.
- Pipeline integration point:
- `_apply_document_validation_to_sub_qa(...)` in `src/backend/services/agent_service.py`.
- Data carrier between stages:
- `SubQuestionAnswer` in `src/backend/schemas/agent.py`.

## Data Flow
### Inputs
- `SubQuestionAnswer` list from Section 5 where each item contains:
- `sub_question`: the question text to evaluate relevance against.
- `sub_answer`: retriever-formatted ranked rows (`N. title=... source=... content=...`).
- Validation config from environment variables:
- `DOCUMENT_VALIDATION_MIN_RELEVANCE_SCORE`
- `DOCUMENT_VALIDATION_SOURCE_ALLOWLIST`
- `DOCUMENT_VALIDATION_MIN_YEAR`
- `DOCUMENT_VALIDATION_MAX_YEAR`
- `DOCUMENT_VALIDATION_REQUIRE_YEAR_WHEN_RANGE_SET`
- `DOCUMENT_VALIDATION_MAX_WORKERS`

### Transformations and movement
1. Runtime pipeline enters `_apply_document_validation_to_sub_qa(sub_qa)` in `agent_service`.
2. For each sub-question item, `validate_subquestion_documents(...)` is called with:
- `sub_question=item.sub_question`
- `retrieved_output=item.sub_answer`
- `config=_DOCUMENT_VALIDATION_CONFIG`
3. `parse_retrieved_documents(...)` converts retriever text rows into typed `RetrievedDocument` objects.
4. `ThreadPoolExecutor` validates each parsed document concurrently through `_validate_document(...)`.
5. `_validate_document(...)` computes a relevance overlap score and checks:
- score threshold,
- source allowlist membership,
- year-range constraints (and optional required-year behavior).
6. Validation returns `SubQuestionValidationResult` containing:
- `total_documents`
- per-doc `validation_results` (score/pass/rejection reasons)
- `valid_documents` subset
7. If parseable docs were present (`total_documents > 0`), `agent_service` rewrites `item.sub_answer` with only valid docs using `format_retrieved_documents(...)`.
8. If no parseable rows exist, `item.sub_answer` is left unchanged and validation is logged as skipped.
9. Updated `sub_qa` moves to Section 7 reranking.

### Outputs
- Per-subquestion `sub_answer` mutated from "retrieved docs" to "validated docs" (same line format, filtered content).
- Validation metrics in logs (`docs_before`, `docs_after`, rejected count, config summary).
- Structured validation artifacts (`ValidatedDocumentResult`) available inside the validation step.

### Data boundaries
- Boundary A: text retrieval rows from Section 5 -> typed `RetrievedDocument` records.
- Boundary B: typed records -> parallel validator worker tasks.
- Boundary C: validation results -> filtered retrieval text persisted back onto `SubQuestionAnswer.sub_answer`.
- Boundary D: validated retrieval text -> Section 7 reranking input.

## Key Interfaces and APIs
- `build_document_validation_config_from_env() -> DocumentValidationConfig`
- `parse_retrieved_documents(retrieved_output: str) -> list[RetrievedDocument]`
- `validate_subquestion_documents(sub_question: str, retrieved_output: str, config: DocumentValidationConfig) -> SubQuestionValidationResult`
- `format_retrieved_documents(documents: list[RetrievedDocument]) -> str`
- `_apply_document_validation_to_sub_qa(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]`

## Fit With Adjacent Sections
- Upstream (Section 5: per-subquestion search): consumes retriever-formatted rows produced by `search_database(...)`.
- Downstream (Section 7: reranking): sends only validated documents to reranking, reducing noisy candidates.
- Downstream (Sections 8-9): subanswer generation/verification quality depends on validation recall-vs-precision tuning.
- Cross-stage pipeline detail: this stage runs before reranking inside per-subquestion processing in `run_pipeline_for_subquestions(...)`.

## Tradeoffs
### Chosen design
Apply rule-based validation over retriever text rows, with parallel per-document execution and environment-configurable constraints.

### Benefits
- Fast and deterministic filtering before heavier downstream reasoning.
- Operationally simple tuning through environment variables (no code redeploy for threshold/allowlist/year updates).
- Parallel document checks reduce latency when each sub-question returns multiple documents.
- Preserves existing retriever output format and `SubQuestionAnswer` contract.

### Costs
- Validation depends on parsing formatted text rows, so format drift can reduce parse reliability.
- Relevance scoring is token-overlap based, so semantic relevance can be under-estimated.
- In-place mutation of `sub_answer` removes direct access to pre-validation rows unless logs are retained.
- Two-layer concurrency exists in the system (per-subquestion parallel pipeline and per-document validation parallelism), which can increase thread contention if worker limits are misconfigured.

### Alternatives considered or rejected
- LLM-based validation per document:
- Pros: better semantic and policy-aware filtering.
- Cons: slower, costlier, and less deterministic than current rules.
- Structured retriever JSON output instead of line parsing:
- Pros: safer contracts, fewer parse edge cases.
- Cons: requires broader changes to tool-call payload handling and existing extraction flow.
- Sequential validation (no per-document parallelism):
- Pros: simpler execution model and easier debugging.
- Cons: higher latency as document count grows.
- Persist full validation audit in DB per run:
- Pros: stronger traceability and offline analysis.
- Cons: extra schema/write complexity not required for current runtime pipeline.
