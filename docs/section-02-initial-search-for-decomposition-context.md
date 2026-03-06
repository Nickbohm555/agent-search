# Section 2 Architecture: Initial search for decomposition context

## Purpose
Run one retrieval pass on the raw user question before decomposition, then pass a compact, structured context payload into the coordinator so decomposition is grounded in real indexed content.

## Components
- Runtime entrypoint: `run_runtime_agent(...)` in `src/backend/services/agent_service.py`.
- Context retrieval function: `search_documents_for_context(...)` in `src/backend/services/vector_store_service.py`.
- Context shaping function: `build_initial_search_context(...)` in `src/backend/services/vector_store_service.py`.
- Coordinator input serializer: `_build_coordinator_input_message(...)` in `src/backend/services/agent_service.py`.
- Vector store provider: `get_vector_store(...)` in `src/backend/services/vector_store_service.py`.
- Config knobs:
  - `INITIAL_SEARCH_CONTEXT_K` (default `5`)
  - `INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD` (optional)

## Data Flow
### Inputs
- External: `RuntimeAgentRunRequest.query` from `POST /api/agents/run`.
- Infra: PGVector-backed collection (`agent_search_internal_data` by default).
- Config: `k` and optional `score_threshold` from environment.

### Transformations
1. `run_runtime_agent(...)` creates/loads the vector store via `get_vector_store(...)`.
2. It calls `search_documents_for_context(vector_store, query, k, score_threshold)`.
3. `search_documents_for_context(...)` chooses retrieval mode:
- If threshold is set and the store supports it, use `similarity_search_with_relevance_scores(...)` and strip scores.
- Otherwise use `similarity_search(...)`.
4. Returned `Document` objects are transformed by `build_initial_search_context(...)` into bounded JSON-safe items:
- `rank`
- `document_id`
- `title`
- `source`
- `snippet` (newline-normalized, max 500 chars)
5. `_build_coordinator_input_message(...)` embeds this structured list (serialized JSON) into the first `HumanMessage` under “Initial retrieval context for decomposition”.
6. Coordinator receives this message and starts decomposition using both the question and the retrieved context.

### Outputs
- Primary output of this section: `initial_search_context: list[dict]` injected into coordinator input.
- Secondary outputs: logs for retrieval mode, result count, and context-build stats.

## Key Interfaces / APIs
- `search_documents_for_context(vector_store, query, *, k, score_threshold=None) -> list[Document]`
- `build_initial_search_context(documents) -> list[dict[str, str | int]]`
- `_build_coordinator_input_message(query, initial_search_context) -> str`
- `run_runtime_agent(payload, db) -> RuntimeAgentRunResponse`

## Fit With Adjacent Sections
- Upstream:
- Depends on indexed internal documents/chunks already present in PGVector.
- Downstream:
- Feeds Section 3 decomposition by providing grounding context in the coordinator’s first message.
- Also reused later by answer generation (`generate_initial_answer(...)`) as contextual evidence alongside `sub_qa`.

## Tradeoffs
### Chosen design
Perform exactly one pre-decomposition retrieval on the original user query, then pass a compact structured context block to the coordinator prompt.

### Benefits
- Simple control flow and low latency overhead versus multi-pass prefetch.
- Keeps decomposition grounded in available corpus entities/terms.
- Clear observability via explicit logs and deterministic context schema.

### Costs
- Single-pass retrieval can miss relevant facets for ambiguous multi-part questions.
- Snippet truncation (500 chars) may omit key qualifiers.
- Prompt-embedded JSON increases token usage and can dilute instruction salience if `k` is too high.

### Alternatives considered/rejected
- No pre-decomposition retrieval:
- Pro: lowest cost/latency.
- Con: decomposition is less corpus-aware and may branch into unsupported sub-questions.
- Multi-query or iterative retrieval before decomposition:
- Pro: broader recall and better disambiguation.
- Con: higher latency, complexity, and more moving parts before first agent step.
- Passing full documents instead of compact context objects:
- Pro: richer evidence.
- Con: much higher prompt size and noisier decomposition input.
