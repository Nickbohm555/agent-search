# Section 3 Architecture: Coordinator Consumes Provided Sub-Questions Only

## Purpose
Keep decomposition isolated from execution. Sections 1-2 produce the normalized sub-question list; the coordinator receives only that list and delegates each item.

## Components
- Coordinator prompt and subagent contract: [`src/backend/agents/coordinator.py`](/Users/nickbohm/Desktop/Tinkering/agent-search/src/backend/agents/coordinator.py)
- Runtime orchestration and coordinator message assembly: [`src/backend/services/agent_service.py`](/Users/nickbohm/Desktop/Tinkering/agent-search/src/backend/services/agent_service.py)
- Runtime response schema carrying per-subquestion outputs downstream: [`src/backend/schemas/agent.py`](/Users/nickbohm/Desktop/Tinkering/agent-search/src/backend/schemas/agent.py)

## Flow Diagram
```text
+----------------------------------------------+
| Sections 1-2 Output                          |
| decomposition_sub_questions = ["...?", ...]  |
+----------------------+-----------------------+
                       |
                       v
+----------------------------------------------+
| Agent Service                                |
| _build_coordinator_input_message(subqs)      |
| - serializes provided list only              |
| - no decomposition context passthrough       |
+----------------------+-----------------------+
                       |
                       v
+----------------------------------------------+
| Coordinator Agent                            |
| - consumes provided list                     |
| - delegates each via task(description=...)   |
| - no decomposition in this same context      |
+----------------------+-----------------------+
                       |
                       v
+----------------------------------------------+
| Downstream Pipeline                          |
| _extract_sub_qa + per-subquestion stages     |
+----------------------------------------------+
```

## Contract
- Coordinator input is the normalized sub-question list from Sections 1-2.
- Each sub-question is already atomic and ends with `?`.
- Coordinator must delegate each provided entry in order, without rewriting or inventing new initial sub-questions.
- Refinement-generated sub-questions remain a later-stage exception.

## Notes
- This section intentionally separates planning from execution per the RAG architecture goals.
- Initial retrieval context is used only by the decomposition-only call in Sections 1-2, not by the coordinator input message in Section 3.
