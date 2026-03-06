# Section 6 Architecture: Per-Subquestion Document Validation (Parallel)

## Purpose
Filter retrieved documents for each sub-question before reranking so downstream stages only process documents that satisfy explicit constraints (relevance, source, and optional year window).

## Components
- Validation service and rules engine: [`src/backend/services/document_validation_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/document_validation_service.py)
- Runtime pipeline stage that applies validation per sub-question: [`src/backend/services/agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/agent_service.py)
- Runtime sub-question state model: [`src/backend/schemas/agent.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/schemas/agent.py)
- Validation-focused tests:
[`src/backend/tests/services/test_document_validation_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_document_validation_service.py),
[`src/backend/tests/services/test_agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_agent_service.py)

## Flow Diagram
```text
+-------------------------------------------------------------------------------------------------------+
| Section 5 Output                                                                                      |
|  SubQuestionAnswer[] with sub_answer as ranked rows: "N. title=... source=... content=..."           |
+-----------------------------------------------+-------------------------------------------------------+
                                                |
                                                v
+-------------------------------------------------------------------------------------------------------+
| Pipeline Worker (agent_service._run_pipeline_for_single_subquestion)                                  |
|  +-------------------------------------------------------------------------------------------------+  |
|  | Step 1 for this item: _apply_document_validation_to_sub_qa([item])                              |  |
|  +-------------------------------------------------------------------------------------------------+  |
+-----------------------------------------------+-------------------------------------------------------+
                                                |
                                                v
+-------------------------------------------------------------------------------------------------------+
| Validation Stage (agent_service._apply_document_validation_to_sub_qa)                                 |
|  +-------------------------------------------------------------------------------------------------+  |
|  | validate_subquestion_documents(sub_question, sub_answer, config_from_env)                       |  |
|  | if parseable docs exist: item.sub_answer = format_retrieved_documents(valid_documents)          |  |
|  | else: keep original item.sub_answer and log "skipped"                                            |  |
|  +-------------------------------------------------------------------------------------------------+  |
+-----------------------------------------------+-------------------------------------------------------+
                                                |
                                                v
+-------------------------------------------------------------------------------------------------------+
| Validation Service Internals (document_validation_service)                                             |
|  +-------------------------------------------------------------------------------------------------+  |
|  | parse_retrieved_documents(...) -> RetrievedDocument[]                                             |  |
|  | ThreadPoolExecutor(max_workers=min(config.max_workers, len(docs)))                               |  |
|  |   _validate_document(...) per doc:                                                                |  |
|  |     - relevance overlap score >= min_relevance_score?                                             |  |
|  |     - source in allowlist (if allowlist configured)?                                              |  |
|  |     - any extracted year in [min_year, max_year] (if range configured)?                          |  |
|  | return SubQuestionValidationResult(total, valid_documents, validation_results)                   |  |
|  +-------------------------------------------------------------------------------------------------+  |
+-----------------------------------------------+-------------------------------------------------------+
                                                |
                                                v
+-------------------------------------------------------------------------------------------------------+
| Section 7 Handoff                                                                                     |
|  item.sub_answer now carries validated subset (same ranked-row text format) for reranking            |
+-------------------------------------------------------------------------------------------------------+
```

## Data Flow
Inputs:
- `SubQuestionAnswer.sub_question`: the question text used for relevance scoring.
- `SubQuestionAnswer.sub_answer`: ranked retrieval rows from Section 5.
- Environment-driven validation config:
`DOCUMENT_VALIDATION_MIN_RELEVANCE_SCORE`,
`DOCUMENT_VALIDATION_SOURCE_ALLOWLIST`,
`DOCUMENT_VALIDATION_MIN_YEAR`,
`DOCUMENT_VALIDATION_MAX_YEAR`,
`DOCUMENT_VALIDATION_REQUIRE_YEAR_WHEN_RANGE_SET`,
`DOCUMENT_VALIDATION_MAX_WORKERS`.

Transformations:
1. `agent_service` reads config once at module load (`_DOCUMENT_VALIDATION_CONFIG`).
2. For each sub-question item, `validate_subquestion_documents(...)` parses raw row text into `RetrievedDocument` objects.
3. Validation runs in parallel per document with `ThreadPoolExecutor`.
4. Each document is scored and checked against configured constraints; failures are collected as typed rejection reasons.
5. Passing documents are reformatted into the same deterministic row format.
6. `SubQuestionAnswer.sub_answer` is overwritten with only validated rows (or left unchanged when no parseable rows were found).

Outputs:
- `SubQuestionAnswer.sub_answer`: validated document subset serialized as ranked rows.
- Internal observability data:
`SubQuestionValidationResult.total_documents`,
`valid_documents`,
`validation_results` with `relevance_score` and `rejection_reasons`.
- Structured logs with before/after/rejected counts per sub-question.

Data movement and boundaries:
- Pipeline boundary: `SubQuestionAnswer` object enters the stage and exits with mutated `sub_answer`.
- Parsing boundary: plain text rows -> typed `RetrievedDocument[]`.
- Concurrency boundary: sequential pipeline item -> parallel per-document validation tasks.
- Serialization boundary: typed valid docs -> plain text rows for compatibility with Section 7.

## Key Interfaces / APIs
- Config builder:
`build_document_validation_config_from_env() -> DocumentValidationConfig`
- Parse and format helpers:
`parse_retrieved_documents(retrieved_output: str) -> list[RetrievedDocument]`
`format_retrieved_documents(documents: list[RetrievedDocument]) -> str`
- Core validator:
`validate_subquestion_documents(sub_question: str, retrieved_output: str, config: DocumentValidationConfig) -> SubQuestionValidationResult`
- Pipeline integration point:
`_apply_document_validation_to_sub_qa(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]`
- Runtime state carrying this stage's output:
`SubQuestionAnswer{sub_question, sub_answer, tool_call_input, expanded_query, ...}`

## How It Fits Adjacent Sections
- Upstream dependency (Section 5): consumes retrieval rows produced per sub-question.
- Immediate downstream (Section 7): passes forward only validated rows for reranking.
- Downstream impact (Sections 8-9): subanswer generation/verification quality depends on what this stage filtered in or out.

## Tradeoffs
1. Rule-based lexical validation vs LLM-based semantic validation
- Chosen: deterministic rule-based validation.
- Pros: fast, cheap, predictable, easy to test; explicit rejection reasons.
- Cons: token-overlap relevance can miss semantic matches and synonym-heavy phrasing.
- Rejected alternative: LLM judge per document.
- Why rejected: higher latency/cost and less deterministic outputs for this stage.

2. Keep text row contract between stages vs switch to typed document payloads end-to-end
- Chosen: parse rows into typed docs internally, then serialize validated subset back to row text.
- Pros: minimal contract change with existing pipeline and logging.
- Cons: repeated parse/format work across stages and tighter coupling to row syntax.
- Rejected alternative: propagate typed documents through all stages.
- Why rejected: larger cross-section refactor outside this iteration scope.

3. Parallel validation per document vs sequential loop
- Chosen: per-subquestion document validation uses `ThreadPoolExecutor`.
- Pros: lower wall-clock time when per-document checks become slower; backed by timing test.
- Cons: thread overhead and less benefit for tiny doc counts or very cheap checks.
- Rejected alternative: always sequential.
- Why rejected: unnecessary latency when candidate document count grows.

4. Config read at service import time vs dynamic per-request config
- Chosen: build `_DOCUMENT_VALIDATION_CONFIG` once at module load.
- Pros: simpler runtime path and stable behavior within process lifetime.
- Cons: env changes require process restart to take effect.
- Rejected alternative: rebuild config on every request/sub-question.
- Why rejected: extra overhead and less predictable run-to-run behavior within a single process.
