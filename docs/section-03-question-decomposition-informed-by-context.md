# Section 3 Architecture: Question Decomposition Informed by Context

## Purpose
Generate narrow, context-aware sub-questions from the user question by grounding decomposition in the initial retrieval context produced in Section 2.

## Components
- Coordinator prompt and subagent contract: [`src/backend/agents/coordinator.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/agents/coordinator.py)
- Runtime orchestration and decomposition input assembly: [`src/backend/services/agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/agent_service.py)
- Runtime response schema carrying per-subquestion outputs downstream: [`src/backend/schemas/agent.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/schemas/agent.py)
- Prompt/input contract tests:
[`src/backend/tests/agents/test_coordinator_agent.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/agents/test_coordinator_agent.py),
[`src/backend/tests/services/test_agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_agent_service.py)

## Flow Diagram
```text
+-------------------------------------------------------------------+
| Section 2 Output                                                   |
|  initial_search_context = [{rank, document_id, title, source, ...}]|
+-----------------------------------+-------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------+
| Agent Service: run_runtime_agent(payload, db)                     |
|  +-------------------------------------------------------------+  |
|  | _build_coordinator_input_message(query, context)            |  |
|  |  - User question                                             |  |
|  |  - "Initial retrieval context for decomposition" (JSON)     |  |
|  |  - decomposition constraints                                 |  |
|  +-------------------------------------------------------------+  |
|  +-------------------------------------------------------------+  |
|  | agent.invoke({messages:[HumanMessage(content=...)])         |  |
|  +-------------------------------------------------------------+  |
+-----------------------------------+-------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------+
| Coordinator Agent (deep-agents main agent)                        |
|  +-------------------------------------------------------------+  |
|  | Prompt rules (decomposition stage):                          |  |
|  |  - consume initial retrieval context                         |  |
|  |  - one concept per sub-question                              |  |
|  |  - each sub-question ends with '?'                           |  |
|  |  - delegate via task() with exact question text             |  |
|  +-------------------------------------------------------------+  |
+-----------------------------------+-------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------+
| Section 4+ Handoff                                                 |
|  task()-delegated sub-questions -> per-subquestion pipeline        |
|  (Expand -> Search -> Validate -> Rerank -> Answer -> Check)       |
+-------------------------------------------------------------------+
```

## Data Flow
Inputs:
- `payload.query` from `RuntimeAgentRunRequest`
- `initial_search_context` (Section 2 output): list of ranked context items with title/source/snippet signals

Transformations:
1. `run_runtime_agent(...)` receives raw user query and pre-built context list.
2. `_build_coordinator_input_message(query, initial_search_context)` serializes context as JSON and creates a structured decomposition message with constraints.
3. `create_coordinator_agent(...)` provides `_COORDINATOR_PROMPT` that explicitly requires context-aware decomposition and question-form delegation (`task()` with `?` suffix preserved).
4. `agent.invoke(...)` sends that message to the coordinator. The coordinator decomposes the question and delegates atomic sub-questions to the RAG subagent.

Outputs:
- Decomposition is represented operationally as ordered `task()` delegations containing sub-question descriptions.
- Downstream extraction (`_extract_sub_qa`) reads those delegated descriptions as `SubQuestionAnswer.sub_question` entries for the per-subquestion pipeline.

Data movement boundaries:
- Service boundary: Python runtime state to coordinator message text.
- Prompt boundary: structured JSON context converted into model-readable prompt tokens.
- Agent boundary: coordinator emits tool-call arguments (`task`) consumed by downstream extraction and processing.

## Key Interfaces / APIs
- `run_runtime_agent(payload: RuntimeAgentRunRequest, db: Session) -> RuntimeAgentRunResponse`
- `_build_coordinator_input_message(query: str, initial_search_context: list[dict[str, Any]]) -> str`
- `create_coordinator_agent(vector_store: Any, model: Any, ...) -> Any`
- Coordinator prompt contract in `_COORDINATOR_PROMPT`:
- recognizes `Initial retrieval context for decomposition`
- requires one-concept, context-aware, question-form sub-questions
- requires delegation through `task()`

## How It Fits Adjacent Sections
- Upstream dependency: Section 2 provides `initial_search_context`; this section consumes it as decomposition grounding input.
- Downstream impact: Section 4 (query expansion) and later stages depend on sub-question quality produced here. Better decomposition yields better retrieval precision and final synthesis quality.
- Section 1 relationship: this section lives inside coordinator-driven orchestration and follows the flow tracking/plan discipline established there.

## Tradeoffs
1. Context-aware decomposition vs question-only decomposition
- Chosen: include initial retrieval context in decomposition input.
- Pros: sub-questions stay aligned to corpus entities/concepts; less drift.
- Cons: decomposition can inherit retrieval bias from top-k context.

2. Prompt-level enforcement vs deterministic code-level decomposition rules
- Chosen: enforce decomposition behavior via coordinator prompt constraints.
- Pros: flexible for varied question types, minimal code complexity.
- Cons: relies on model compliance; occasional format drift still possible.

3. Inline JSON context in a single `HumanMessage` vs separate structured state channel
- Chosen: inline JSON in coordinator input message.
- Pros: simple interface and low integration overhead with existing deep-agents flow.
- Cons: token overhead and potential readability loss when context grows.

4. Delegation-first decomposition (`task()` for each sub-question) vs producing a static list only
- Chosen: decomposition is coupled to immediate delegation.
- Pros: direct handoff into per-subquestion pipeline, fewer translation steps.
- Cons: decomposition artifact is implicit in tool calls, not a dedicated typed object.

5. Strict question-form constraint (`?` suffix) vs flexible phrase chunks
- Chosen: enforce complete question strings ending in `?`.
- Pros: cleaner subagent inputs and easier consistency checks in tests/logs.
- Cons: may constrain edge cases where non-question labels could be shorter or clearer.
