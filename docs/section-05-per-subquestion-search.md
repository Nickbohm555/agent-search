# Section 5 Architecture: Per-Subquestion Search

## Purpose
Execute retrieval for each sub-question using the expanded query from Section 4, and return a ranked document list per sub-question as the input artifact for downstream processing.

## Components
- Subagent retrieval contract (must call retriever with `query` + `expanded_query`): [`src/backend/agents/coordinator.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/agents/coordinator.py)
- Retriever tool execution and ranked text formatting: [`src/backend/tools/retriever_tool.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tools/retriever_tool.py)
- Tool-call capture callback for `search_database` inputs/outputs: [`src/backend/utils/agent_callbacks.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/utils/agent_callbacks.py)
- Runtime extraction of per-subquestion retrieval outputs into typed objects: [`src/backend/services/agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/services/agent_service.py)
- Per-subquestion runtime shape: [`src/backend/schemas/agent.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/schemas/agent.py)
- Behavior tests:
[`src/backend/tests/tools/test_retriever_tool.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/tools/test_retriever_tool.py),
[`src/backend/tests/services/test_agent_service.py`](/Users/nickbohm/Desktop/worktree/agent-search/src/backend/tests/services/test_agent_service.py)

## Flow Diagram
```text
+--------------------------------------------------------------------------------------+
| Section 4 Output                                                                      |
|  sub-question + expanded_query                                                        |
+----------------------------------------------+---------------------------------------+
                                               |
                                               v
+--------------------------------------------------------------------------------------+
| Coordinator Subagent Execution                                                        |
|  +--------------------------------------------------------------------------------+  |
|  | subagent tool call:                                                            |  |
|  | search_database(query=<sub-question>, expanded_query=<expanded>, limit=...)    |  |
|  +--------------------------------------------------------------------------------+  |
+----------------------------------------------+---------------------------------------+
                                               |
                                               v
+--------------------------------------------------------------------------------------+
| Retriever Tool (retriever_tool.py::search_database)                                  |
|  +--------------------------------------------------------------------------------+  |
|  | retrieval_query = expanded_query.strip() or query                               |  |
|  | vector_store.similarity_search(retrieval_query, k=limit, filter=wiki_source)   |  |
|  | _format_results(...) -> numbered rows:                                          |  |
|  | "1. title=... source=... content=..."                                           |  |
|  +--------------------------------------------------------------------------------+  |
+----------------------------------------------+---------------------------------------+
                                               |
                                               v
+--------------------------------------------------------------------------------------+
| Callback Capture (SearchDatabaseCaptureCallback)                                     |
|  +--------------------------------------------------------------------------------+  |
|  | on_tool_start: store input by run_id                                            |  |
|  | on_tool_end: pair with output, append (input_str, output_str) in call order    |  |
|  +--------------------------------------------------------------------------------+  |
+----------------------------------------------+---------------------------------------+
                                               |
                                               v
+--------------------------------------------------------------------------------------+
| Agent Service Extraction (_extract_sub_qa)                                           |
|  +--------------------------------------------------------------------------------+  |
|  | parse query + expanded_query from input_str                                      |  |
|  | estimate docs via ranked-row regex                                               |  |
|  | build SubQuestionAnswer per call:                                                |  |
|  |   sub_question, sub_answer(retrieval rows), tool_call_input, expanded_query     |  |
|  +--------------------------------------------------------------------------------+  |
+----------------------------------------------+---------------------------------------+
                                               |
                                               v
+--------------------------------------------------------------------------------------+
| Section 6 Handoff                                                                     |
|  SubQuestionAnswer.sub_answer carries ranked retrieval output for validation         |
+--------------------------------------------------------------------------------------+
```

## Data Flow
Inputs:
- `query` from delegated sub-question text.
- `expanded_query` from Section 4 expansion stage.
- Optional retrieval controls (`limit`, optional `wiki_source_filter`).

Transformations:
1. Coordinator subagent issues `search_database(...)` tool call for each sub-question.
2. Retriever tool computes one effective retrieval string: prefer `expanded_query`, fallback to `query`.
3. Vector store returns semantically similar chunks ordered by similarity for that query.
4. Tool formats chunks into a deterministic ranked plain-text list (one line per result with title/source/content).
5. Callback path stores ordered `(input_str, output_str)` pairs for each `search_database` call.
6. `agent_service._extract_sub_qa(...)` parses input payloads, binds retrieval output to the corresponding sub-question, and materializes `SubQuestionAnswer`.
7. `agent_service._estimate_retrieved_doc_count(...)` counts ranked rows for observability logs without mutating payloads.

Outputs:
- Per-subquestion ranked retrieval payload in `SubQuestionAnswer.sub_answer`.
- Preserved retrieval provenance in `SubQuestionAnswer.tool_call_input`.
- Propagated `SubQuestionAnswer.expanded_query` for later ranking and debugging.

Data movement and boundaries:
- Agent boundary: natural-language planning -> structured tool args (`query`, `expanded_query`, `limit`).
- Tool boundary: structured args -> vector DB similarity call -> normalized ranked string.
- Callback boundary: runtime tool events -> ordered captured call list.
- Service boundary: mixed message/callback events -> typed `SubQuestionAnswer[]` pipeline state.

## Key Interfaces / APIs
- Retriever tool:
`search_database(query: str, expanded_query: str | None = None, limit: int = 10, wiki_source_filter: str | None = None) -> str`
- Callback capture:
`SearchDatabaseCaptureCallback.get_calls() -> list[tuple[str, str]]`
- Extraction:
`_extract_sub_qa(messages, search_database_calls=None) -> list[SubQuestionAnswer]`
- Observability helper:
`_estimate_retrieved_doc_count(search_output: str) -> int`
- Runtime model:
`SubQuestionAnswer{sub_question, sub_answer, tool_call_input, expanded_query, ...}`

## How It Fits Adjacent Sections
- Upstream dependency (Section 4): consumes `expanded_query` generated per sub-question.
- Immediate downstream (Section 6): passes ranked per-subquestion docs to validation logic.
- Later sections (7-9): reranking, answer generation, and verification all depend on this section’s retrieval payload format and fidelity.

## Tradeoffs
1. Capture retrieval via callback stream vs only parsing final message list
- Chosen: callback capture is preferred (`search_database_calls`) with message parsing fallback.
- Pros: preserves exact retriever input/output pairs in call order; better observability for UI and logs.
- Cons: additional callback state management (`run_id` pending map).
- Rejected alternative: parse only final LangChain message list.
- Why rejected: can lose or ambiguously pair subagent tool I/O depending on runtime message shape.

2. Return ranked docs as formatted text rows vs typed document objects at this stage
- Chosen: keep retriever output as deterministic numbered text.
- Pros: simple tool contract, easy to inspect in logs/tests, compatible with existing agent messaging.
- Cons: downstream steps must parse text back into structured records.
- Rejected alternative: structured JSON document payload through the whole pipeline.
- Why rejected: would require broader contract changes across agent/tool wiring in this iteration.

3. Single retrieval query (`expanded_query` fallback to `query`) vs multi-query merge
- Chosen: one effective query per sub-question.
- Pros: bounded latency/cost and straightforward ranking semantics.
- Cons: can miss recall improvements from unioning multiple reformulations.
- Rejected alternative: run several expansions and merge/deduplicate.
- Why rejected: higher complexity and more expensive retrieval per sub-question.

4. Keep retrieval formatting logic inside the tool vs move it to service layer
- Chosen: format in `retriever_tool` before returning to agent runtime.
- Pros: keeps tool self-contained and predictable for agent consumption.
- Cons: couples textual output format to downstream parser expectations.
- Rejected alternative: tool returns raw docs and service formats later.
- Why rejected: current deep-agent tool flow expects string outputs, and this keeps minimal surface changes.
