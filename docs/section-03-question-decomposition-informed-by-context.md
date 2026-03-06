# Section 3 Architecture: Question decomposition informed by context

## Purpose
Create context-aware, narrow sub-questions from the user question by grounding decomposition in Section 2 retrieval output before any per-subquestion retrieval pipeline runs.

## Components
- Coordinator prompt contract: `_COORDINATOR_PROMPT` in `src/backend/agents/coordinator.py`.
- Decomposition message builder: `_build_coordinator_input_message(...)` in `src/backend/services/agent_service.py`.
- Runtime orchestration entrypoint: `run_runtime_agent(...)` in `src/backend/services/agent_service.py`.
- Initial context producer from Section 2: `build_initial_search_context(...)` output consumed here.
- Coordinator invocation channel: `agent.invoke({"messages": [HumanMessage(...)]}, config=...)`.

## Data Flow
### Inputs
- User question string from `RuntimeAgentRunRequest.query`.
- `initial_search_context` list of structured items (rank/document_id/title/source/snippet) from Section 2 retrieval.
- Prompt-level decomposition rules from `_COORDINATOR_PROMPT`.

### Transformations
1. `run_runtime_agent(...)` receives `payload.query` and calls Section 2 retrieval/context-shaping.
2. `_build_coordinator_input_message(query, initial_search_context)` serializes the context to JSON and builds a single decomposition payload with:
- `User question`
- `Initial retrieval context for decomposition (top-k from the original question)`
- decomposition constraints (narrow scope, one concept, trailing `?`, prefer context entities/concepts).
3. `run_runtime_agent(...)` sends that payload as the first `HumanMessage` to the coordinator agent.
4. Coordinator reads both the system prompt and decomposition payload, then performs decomposition via `task()` delegations under these rules:
- use provided context as grounding input,
- keep sub-questions atomic,
- preserve full question form ending with `?`.

### Outputs
- Primary output: decomposition represented as delegated sub-question tasks (later materialized into `SubQuestionAnswer.sub_question` during extraction).
- Secondary output: runtime log `Coordinator decomposition input prepared ... context_items=<n>` confirming context was injected.
- Downstream artifact: question strings that feed Section 4+ per-subquestion processing.

### Data Boundaries
- Boundary A: API request payload -> backend runtime service.
- Boundary B: backend service state -> coordinator LLM context window (JSON message payload).
- Boundary C: coordinator decomposition decisions -> task/tool-call trace used by extraction and downstream pipeline.

## Key Interfaces and APIs
- `_build_coordinator_input_message(query: str, initial_search_context: list[dict[str, Any]]) -> str`
- `create_coordinator_agent(vector_store, model, ...) -> runnable`
- `run_runtime_agent(payload: RuntimeAgentRunRequest, db: Session) -> RuntimeAgentRunResponse`
- Prompt contract lines in `_COORDINATOR_PROMPT`:
- context-aware decomposition requirement,
- exact `task()` delegation behavior,
- mandatory `?` suffix and one-concept-per-question constraint.

## Fit With Adjacent Sections
- Upstream (Section 2): consumes initial retrieval context generated from the raw user query.
- Downstream (Sections 4-10): decomposition outputs become the unit of work for expansion, search, validation, reranking, subanswer generation, and verification.
- Later synthesis/refinement (Sections 11-14): quality of decomposition directly controls answer completeness and whether refinement is needed.

## Tradeoffs
### Chosen design
Prompt-driven decomposition grounded by serialized retrieval context injected into the first coordinator message.

### Benefits
- Keeps decomposition aligned with indexed corpus reality instead of free-form brainstorming.
- Minimal implementation complexity: no separate decomposition service or schema migration required.
- Easy observability through explicit message construction and logs.

### Costs
- Reliability depends on prompt adherence by the model, not hard programmatic guarantees.
- JSON context in prompt consumes tokens and may lose salience if too large/noisy.
- Decomposition quality can degrade when initial retrieval misses key concepts.

### Alternatives considered or rejected
- Dedicated deterministic decomposition service (rule-based/parser-first):
- Pros: stronger guarantees on question format and count.
- Cons: weaker semantic flexibility, harder handling of ambiguous natural language.
- Separate LLM decomposition service outside coordinator:
- Pros: clearer separation of concerns and easier unit isolation.
- Cons: extra model call, more latency/cost, additional orchestration complexity.
- Passing raw documents instead of compact context JSON:
- Pros: richer grounding evidence.
- Cons: larger prompt footprint and higher risk of irrelevant detail dominating decomposition.
