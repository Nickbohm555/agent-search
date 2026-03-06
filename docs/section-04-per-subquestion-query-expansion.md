# Section 4 Architecture: Per-subquestion query expansion

## Purpose
For each decomposed sub-question, create and carry an `expanded_query` (synonyms/reformulations) so retrieval and later ranking can use a broader but still focused query representation.

## Components
- Subagent prompt contract: `_RAG_SUBAGENT_PROMPT` in `src/backend/agents/coordinator.py`.
- Retriever tool API: `search_database(...)` in `src/backend/tools/retriever_tool.py`.
- Runtime extraction/parsing:
  - `_parse_tool_input_for_expanded_query(...)` in `src/backend/services/agent_service.py`.
  - `_extract_sub_qa(...)` in `src/backend/services/agent_service.py`.
- Response schema field: `SubQuestionAnswer.expanded_query` in `src/backend/schemas/agent.py`.
- Downstream query consumer in reranking: `_apply_reranking_to_sub_qa(...)` in `src/backend/services/agent_service.py`.

## Data Flow
### Inputs
- Sub-question text produced by coordinator decomposition/delegation (`task()` output).
- Subagent instruction requiring two tool inputs:
  - `query`: exact sub-question.
  - `expanded_query`: expanded variant; fallback to original when no useful expansion exists.

### Transformations and movement
1. Coordinator delegates one atomic sub-question to `rag_retriever`.
2. `rag_retriever` generates an expansion in-model and calls `search_database(query, expanded_query, ...)`.
3. Retriever tool computes the effective retrieval text:
- `retrieval_query = (expanded_query or "").strip() or query`
- This enforces a deterministic fallback path to the original sub-question.
4. Retriever executes vector search with `retrieval_query` and returns formatted document lines.
5. Callback/message capture in `run_runtime_agent(...)` records tool-call input/output.
6. `_extract_sub_qa(...)` parses each tool-call payload and stores:
- `sub_question` (from `query`/description),
- raw `tool_call_input`,
- parsed `expanded_query`,
- retrieval output as `sub_answer`.
7. `SubQuestionAnswer` objects flow through later per-subquestion stages.
8. During reranking, `_apply_reranking_to_sub_qa(...)` uses:
- `rerank_query = item.expanded_query.strip() or item.sub_question`
- This reuses expansion data instead of losing it after retrieval.
9. Final API response includes `sub_qa[*].expanded_query` for observability/debugging.

### Outputs
- Functional output: retrieval and reranking query text may differ from the literal sub-question when expansion exists.
- Data artifact: `expanded_query` persisted per `SubQuestionAnswer`.
- Operational output: logs include `query`, `expanded_query`, and effective `retrieval_query`.

### Data boundaries
- Boundary A: LLM subagent-generated expansion -> retriever tool-call JSON args.
- Boundary B: tool-call JSON args -> typed backend model (`SubQuestionAnswer.expanded_query`).
- Boundary C: per-subquestion model -> downstream ranking/answer pipeline and API response payload.

## Key Interfaces and APIs
- `search_database(query: str, expanded_query: str | None = None, limit: int = 10, wiki_source_filter: str | None = None) -> str`
- `_parse_tool_input_for_expanded_query(input_str: str) -> str`
- `SubQuestionAnswer` schema field: `expanded_query: str = ""`
- `run_runtime_agent(payload, db) -> RuntimeAgentRunResponse` (propagates `expanded_query` in `sub_qa`)

## Fit With Adjacent Sections
- Upstream (Section 3): consumes atomic sub-questions produced by context-aware decomposition.
- Downstream (Section 5): directly controls what text is used for per-subquestion retrieval.
- Downstream (Section 7): influences reranker scoring query via `expanded_query` fallback logic.
- Cross-section impact: better expansion can improve recall; poor expansion can introduce semantic drift that later validation/reranking must correct.

## Tradeoffs
### Chosen design
Expansion is generated inside the retrieval subagent prompt and passed as an explicit optional retriever argument, with deterministic fallback to original `query`.

### Benefits
- Low implementation overhead: no extra service boundary or new dependency.
- High transparency: expanded text is visible in tool payloads, logs, and API response.
- Safe fallback behavior: empty/invalid expansion does not break retrieval.
- Reusability: same field can be consumed by reranking and diagnostics.

### Costs
- Expansion quality depends on LLM prompt adherence and may vary by model behavior.
- No hard quality gate in this section; noisy expansions can reduce precision.
- Additional prompt/tool tokens increase runtime cost and latency.

### Alternatives considered or rejected
- Dedicated `query_expansion_service` (separate model/rules step):
- Pros: clearer ownership, easier independent testing and policy controls.
- Cons: extra orchestration complexity and likely additional model latency.
- Rule-based expansion only (thesaurus/keyword heuristics):
- Pros: deterministic and cheap.
- Cons: weaker semantic coverage for domain phrasing and paraphrases.
- Multi-expanded-query retrieval (union across several expansions):
- Pros: potentially higher recall.
- Cons: larger result sets, more downstream noise, and higher compute/token cost.
