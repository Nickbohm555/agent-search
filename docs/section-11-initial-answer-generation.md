# Section 11 Architecture: Initial Answer Generation

## Purpose
Generate one initial answer from two evidence streams: initial retrieval context from the original user question (Section 2) and processed per-subquestion outputs (Section 10). This stage produces the first full answer candidate that Section 12 evaluates for potential refinement.

## Components
- Orchestration and call site:
`src/backend/services/agent_service.py`
- Initial answer synthesis service:
`src/backend/services/initial_answer_service.py`
- Data contract for subquestion evidence:
`src/backend/schemas/agent.py`
- Upstream context builder used as Section 11 input:
`src/backend/services/vector_store_service.py`
- Section 11 behavior tests:
`src/backend/tests/services/test_initial_answer_service.py`,
`src/backend/tests/services/test_agent_service.py`

## Flow Diagram
```text
+-------------------------------------------------------------------------------------------------------------------+
| Section 11 Inputs (from run_runtime_agent)                                                                        |
|                                                                                                                   |
|  A) main_question: str                                                                                             |
|  B) initial_search_context: list[dict] from Section 2                                                             |
|     +-----------------------------------------------+                                                             |
|     | each item: rank, document_id, title, source, |                                                             |
|     | snippet                                        |                                                             |
|     +-----------------------------------------------+                                                             |
|  C) sub_qa: list[SubQuestionAnswer] from Section 10                                                               |
|     +-------------------------------------------------------------------------------------------+                 |
|     | each item: sub_question, sub_answer, answerable, verification_reason, expanded_query, ...|                 |
|     +-------------------------------------------------------------------------------------------+                 |
+--------------------------------------------------------------+----------------------------------------------------+
                                                               |
                                                               v
+-------------------------------------------------------------------------------------------------------------------+
| generate_initial_answer(main_question, initial_search_context, sub_qa)                                           |
|  +-------------------------------------------------------------------------------------------------------------+  |
|  | 1) Build deterministic fallback answer                                                                        |  |
|  |    +-----------------------------------------------------------------------------------------------+          |  |
|  |    | priority order:                                                                               |          |  |
|  |    | - answerable subanswers                                                                       |          |  |
|  |    | - any subanswers                                                                               |          |  |
|  |    | - top initial context snippet                                                                  |          |  |
|  |    | - explicit insufficient-evidence sentence                                                      |          |  |
|  |    +-----------------------------------------------------------------------------------------------+          |  |
|  | 2) If OPENAI_API_KEY missing -> return fallback immediately                                                   |  |
|  | 3) If key present -> format bounded inputs and invoke ChatOpenAI                                            |  |
|  |    +-----------------------------------------------------------------------------------------------+          |  |
|  |    | _format_initial_context: limit by INITIAL_ANSWER_MAX_CONTEXT_ITEMS                            |          |  |
|  |    | _format_sub_qa: limit by INITIAL_ANSWER_MAX_SUBQAS + include verification fields             |          |  |
|  |    +-----------------------------------------------------------------------------------------------+          |  |
|  | 4) If LLM returns empty or errors -> fallback                                                                   |  |
|  +-------------------------------------------------------------------------------------------------------------+  |
+--------------------------------------------------------------+----------------------------------------------------+
                                                               |
                                                               v
+-------------------------------------------------------------------------------------------------------------------+
| Section 11 Output                                                                                                 |
|  output: str (initial synthesized answer candidate)                                                               |
+-------------------------------------------------------------------------------------------------------------------+
```

## Data Flow
Inputs:
- `main_question` from `RuntimeAgentRunRequest.query`.
- `initial_search_context` (bounded structured retrieval context built from initial vector search results).
- `sub_qa` list where each item carries generated answer content plus verification status (`answerable`, `verification_reason`).

Transformations:
1. `run_runtime_agent(...)` in `agent_service.py` runs Sections 2-10 first, then passes `main_question`, `initial_search_context`, and processed `sub_qa` into `generate_initial_answer(...)`.
2. `generate_initial_answer(...)` computes a deterministic fallback first. This guarantees output even if no API key is configured or model invocation fails.
3. If `OPENAI_API_KEY` is present, the service formats a constrained synthesis prompt:
- initial context is truncated to `INITIAL_ANSWER_MAX_CONTEXT_ITEMS`.
- subquestion evidence is truncated to `INITIAL_ANSWER_MAX_SUBQAS`.
- verification fields remain in the prompt so synthesis can prefer answerable evidence.
4. The service invokes `ChatOpenAI` with `INITIAL_ANSWER_MODEL` and `INITIAL_ANSWER_TEMPERATURE`.
5. Output handling:
- non-empty LLM response -> returned as initial answer.
- empty/exceptional response -> deterministic fallback returned.

Outputs:
- One `str` assigned to `output` in `run_runtime_agent(...)`.
- This output becomes:
- input to Section 12 (`should_refine(...)` decision), and
- final response when refinement is not needed.

Data movement and boundaries:
- All Section 11 data movement is in-memory within backend process boundaries.
- No direct database writes occur in this stage.
- External boundary exists only when LLM path is active (OpenAI API call).

## Key Interfaces / APIs
- Main synthesis API:
`generate_initial_answer(*, main_question: str, initial_search_context: list[dict[str, Any]], sub_qa: list[SubQuestionAnswer]) -> str`
- Orchestration call site:
`run_runtime_agent(payload: RuntimeAgentRunRequest, db: Session) -> RuntimeAgentRunResponse`
- Input schema consumed by synthesis:
`SubQuestionAnswer` (`sub_question`, `sub_answer`, `answerable`, `verification_reason`, etc.)
- Relevant environment controls:
`OPENAI_API_KEY`, `INITIAL_ANSWER_MODEL`, `INITIAL_ANSWER_TEMPERATURE`, `INITIAL_ANSWER_MAX_CONTEXT_ITEMS`, `INITIAL_ANSWER_MAX_SUBQAS`

## How It Fits Adjacent Sections
- Upstream dependencies:
- Section 2 provides `initial_search_context` (broad question-level grounding).
- Section 10 provides verified per-subquestion outputs (`sub_qa`) after validation, reranking, generation, and verification.
- Downstream consumers:
- Section 12 evaluates this initial answer plus `sub_qa` to decide if refinement is necessary.
- If refinement is triggered, Section 14 reuses the same synthesis function to produce the refined final answer.

## Tradeoffs
1. Single synthesis service reused across initial and refined paths vs separate synthesizers
- Chosen: one `generate_initial_answer(...)` function reused for both Section 11 and Section 14.
- Pros: consistent behavior, less duplicated prompt logic, simpler maintenance.
- Cons: naming can be misleading because function also synthesizes refined outputs.
- Alternative considered: dedicated `generate_refined_answer(...)` service.
- Why rejected: duplicate logic and drift risk.

2. Fallback-first reliability strategy vs strict LLM-only requirement
- Chosen: always compute deterministic fallback before optional LLM call.
- Pros: predictable availability, resilient in missing-key/offline/error scenarios.
- Cons: fallback quality is lower and less nuanced than model synthesis.
- Alternative considered: fail request when LLM unavailable.
- Why rejected: poorer runtime reliability and user experience.

3. Bounded prompt inputs vs full-context prompt
- Chosen: cap context and subquestion entries via env-based maxima.
- Pros: lower token usage, controlled latency/cost, reduced prompt bloat.
- Cons: potentially drops useful long-tail evidence.
- Alternative considered: include all context and all subanswers.
- Why rejected: unbounded cost and noisier synthesis input.

4. Verification-aware synthesis weighting vs neutral aggregation
- Chosen: prompt explicitly prefers answerable/verified subanswers.
- Pros: better grounding and alignment with pipeline confidence signals.
- Cons: may underuse partially useful unverified content.
- Alternative considered: treat all subanswers equally.
- Why rejected: higher hallucination risk from low-confidence evidence.

5. In-memory orchestration data handoff vs persisting intermediate synthesis inputs
- Chosen: pass data directly in-memory inside `run_runtime_agent(...)`.
- Pros: minimal complexity and lower IO overhead.
- Cons: limited post-hoc replay/debug unless logs are sufficient.
- Alternative considered: persist per-stage snapshots in DB.
- Why rejected: additional schema/storage complexity not required for current runtime contract.
