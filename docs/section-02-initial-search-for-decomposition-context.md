# Section 2 Architecture: Initial Search for Decomposition Context

## Purpose
Run one retrieval on the raw user question before decomposition to build a bounded context bundle for later synthesis and diagnostics (not injected into the decomposition-only LLM call).

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
|  | 4) _run_decomposition_only_llm_call(query)               |  |
|  |    question-only decomposition input (no context)        |  |
|  +----------------------------------------------------------+  |
+-------------------------------+--------------------------------+
                                |
                                v
+----------------------------------------------------------------+
| Coordinator Agent Invocation                                   |
|  - agent.invoke({messages: [HumanMessage(content=...)]})       |
|  - coordinator consumes provided sub-questions only            |
+-------------------------------+--------------------------------+
                                |
                                v
+----------------------------------------------------------------+
| Downstream Sections                                            |
|  - Section 3 consumes provided sub-questions                   |
|  - Initial search context is used in later synthesis           |
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
- `snippet`: newline-normalized `page_content`, truncated to 250 chars
4. `initial_search_context` is retained for later answer synthesis; decomposition input uses only the user question.

Outputs:
- In-memory `initial_search_context: list[dict[str, str | int]]`
- Structured initial context bundle retained for downstream synthesis.
- Log events showing query, `k`, threshold, and number of retrieved/context items

Data movement boundaries:
- HTTP boundary: query enters at API request.
- Retrieval boundary: query and config cross into vector store search.
- Synthesis boundary: structured retrieval results are converted into LLM-readable JSON text for initial answer.

## Key Interfaces / APIs
- `run_runtime_agent(payload: RuntimeAgentRunRequest, db: Session) -> RuntimeAgentRunResponse`
- `search_documents_for_context(vector_store: Any, query: str, *, k: int, score_threshold: float | None) -> list[Document]`
- `build_initial_search_context(documents: list[Document]) -> list[dict[str, str | int]]`
- `_build_decomposition_only_input_message(query: str) -> str`

Relevant config surface:
- `INITIAL_SEARCH_CONTEXT_K`
- `INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD`

## How It Fits Adjacent Sections
- Depends on Section 1 orchestration entrypoint (`run_runtime_agent`) and coordinator invocation path.
- Supplies initial context to later synthesis (initial answer and refinement paths).
- Sub-question quality depends on the decomposition-only call, which now sees question-only input.

## Tradeoffs
1. One early retrieval vs fully deferred retrieval
- Chosen: one initial search before decomposition (for later synthesis).
- Pros: initial answer has a grounded context bundle even if downstream retrieval is sparse.
- Cons: adds latency and one extra vector search per run.

2. Structured compact context vs passing raw full documents
- Chosen: keep bounded fields (`rank`, ids, title/source, 250-char snippet).
- Pros: predictable prompt size and concise synthesis context.
- Cons: truncation can hide details needed for nuanced answers.

3. Optional relevance-threshold mode vs fixed top-k only
- Chosen: configurable threshold when backend supports relevance-score API.
- Pros: can reduce low-quality context items in noisy corpora.
- Cons: threshold tuning is corpus-dependent; unsupported stores fall back to unthresholded search.

4. Embedding context as JSON in synthesis prompt vs separate tool/state channel
- Chosen: inline JSON for the initial answer step.
- Pros: simple wiring with existing service contracts and no extra tooling.
- Cons: context becomes token payload; large contexts directly increase model cost.

5. Runtime env-configured `k` and threshold vs hardcoded constants
- Chosen: environment variables.
- Pros: fast operational tuning without code changes.
- Cons: configuration drift risk across environments if not standardized.
