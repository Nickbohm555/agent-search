# Section 2 Architecture: Initial Search for Decomposition Context

## Purpose
Run one retrieval on the raw user question before decomposition so the coordinator starts with grounded context instead of decomposing from the question alone.

## Components
- Runtime orchestration: [`src/backend/services/agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/agent_service.py)
- Context retrieval and shaping: [`src/backend/services/vector_store_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/vector_store_service.py)
- Request/response schema boundary: [`src/backend/schemas/agent.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/schemas/agent.py)
- Tests for wiring and formatting:
[`src/backend/tests/services/test_agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_agent_service.py),
[`src/backend/tests/services/test_vector_store_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_vector_store_service.py)

## Flow Diagram
```text
+----------------------------------------------------------------+
| Client                                                         |
|  - POST /api/agents/run { query }                              |
+-------------------------------+--------------------------------+
                                |
                                v
+----------------------------------------------------------------+
| Agent Service: run_runtime_agent(payload, db)                  |
|  +----------------------------------------------------------+  |
|  | 1) get_vector_store(...)                                 |  |
|  +----------------------------------------------------------+  |
|  +----------------------------------------------------------+  |
|  | 2) search_documents_for_context(                         |  |
|  |      vector_store,                                       |  |
|  |      query=payload.query,                                |  |
|  |      k=INITIAL_SEARCH_CONTEXT_K,                         |  |
|  |      score_threshold=INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD)| |
|  +----------------------------------------------------------+  |
|  +----------------------------------------------------------+  |
|  | 3) build_initial_search_context(documents)               |  |
|  |    -> [{rank, document_id, title, source, snippet}, ...]|  |
|  +----------------------------------------------------------+  |
|  +----------------------------------------------------------+  |
|  | 4) _build_coordinator_input_message(query, context)      |  |
|  |    embeds serialized context JSON into HumanMessage      |  |
|  +----------------------------------------------------------+  |
+-------------------------------+--------------------------------+
                                |
                                v
+----------------------------------------------------------------+
| Coordinator Agent Invocation                                   |
|  - agent.invoke({messages: [HumanMessage(content=...)]})       |
|  - decomposition sees initial retrieval context in first turn  |
+-------------------------------+--------------------------------+
                                |
                                v
+----------------------------------------------------------------+
| Downstream Sections                                            |
|  - Section 3 decomposition uses context signals                |
|  - Later stages consume sub-questions produced from this input |
+----------------------------------------------------------------+
```

## Data Flow
Inputs:
- `payload.query` from `RuntimeAgentRunRequest`
- Runtime config from env:
- `INITIAL_SEARCH_CONTEXT_K` (default `5`)
- `INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD` (optional float)

Transformations:
1. `run_runtime_agent(...)` loads a PGVector-backed store via `get_vector_store(...)`.
2. `search_documents_for_context(...)` executes one search pass:
- Uses `similarity_search_with_relevance_scores(...)` when threshold is provided and supported.
- Falls back to `similarity_search(...)` otherwise.
- Enforces `k >= 1` (`safe_k`).
3. `build_initial_search_context(...)` converts LangChain `Document` objects into bounded context records:
- `rank`: result order (1-based)
- `document_id`: stringified document id
- `title`: `metadata.title` or `metadata.wiki_page`
- `source`: `metadata.source` or `metadata.wiki_url`
- `snippet`: newline-normalized `page_content`, truncated to 500 chars
4. `_build_coordinator_input_message(...)` serializes this list as JSON and injects it into the first coordinator `HumanMessage` under “Initial retrieval context for decomposition”.

Outputs:
- In-memory `initial_search_context: list[dict[str, str | int]]`
- Coordinator input message containing both:
- raw user question
- structured retrieval context
- Log events showing query, `k`, threshold, and number of retrieved/context items

Data movement boundaries:
- HTTP boundary: query enters at API request.
- Retrieval boundary: query and config cross into vector store search.
- Prompt boundary: structured retrieval results are converted into LLM-readable JSON text.

## Key Interfaces / APIs
- `run_runtime_agent(payload: RuntimeAgentRunRequest, db: Session) -> RuntimeAgentRunResponse`
- `search_documents_for_context(vector_store: Any, query: str, *, k: int, score_threshold: float | None) -> list[Document]`
- `build_initial_search_context(documents: list[Document]) -> list[dict[str, str | int]]`
- `_build_coordinator_input_message(query: str, initial_search_context: list[dict[str, Any]]) -> str`

Relevant config surface:
- `INITIAL_SEARCH_CONTEXT_K`
- `INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD`

## How It Fits Adjacent Sections
- Depends on Section 1 orchestration entrypoint (`run_runtime_agent`) and coordinator invocation path.
- Supplies decomposition context to Section 3 so sub-question generation can anchor on retrieved entities and claims.
- Improves later sections indirectly (query expansion, retrieval, reranking, subanswers) by improving sub-question quality at the source.

## Tradeoffs
1. One pre-decomposition retrieval vs no pre-retrieval
- Chosen: one initial search before decomposition.
- Pros: decomposition is grounded in real corpus signals; fewer abstract or off-target sub-questions.
- Cons: adds latency and one extra vector search per run.

2. Structured compact context vs passing raw full documents
- Chosen: pass bounded fields (`rank`, ids, title/source, 500-char snippet).
- Pros: predictable prompt size and cleaner decomposition cues.
- Cons: truncation can hide details needed for nuanced decomposition.

3. Optional relevance-threshold mode vs fixed top-k only
- Chosen: configurable threshold when backend supports relevance-score API.
- Pros: can reduce low-quality context items in noisy corpora.
- Cons: threshold tuning is corpus-dependent; unsupported stores fall back to unthresholded search.

4. Embedding context as JSON in prompt text vs separate tool/state channel
- Chosen: inline JSON in first `HumanMessage`.
- Pros: simple wiring with existing coordinator contract and no extra agent tooling.
- Cons: context becomes token payload; large contexts directly increase model cost.

5. Runtime env-configured `k` and threshold vs hardcoded constants
- Chosen: environment variables.
- Pros: fast operational tuning without code changes.
- Cons: configuration drift risk across environments if not standardized.
