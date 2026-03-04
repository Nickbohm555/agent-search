# IMPLEMENTATION_PLAN

## Findings (2026-03-04)
- The repository was scaffold-only for agent behavior: no decomposition or per-subquery tool-selection API existed.
- Existing agent tests were placeholders and did not verify trajectory/outcome behavior tied to spec acceptance criteria.
- Highest-priority foundational slice is query decomposition + exclusive tool selection because downstream retrieval, validation, synthesis, streaming, and MCP all depend on this contract.

## Priority Backlog
1. Query decomposition + exclusive tool selection API contract.
2. Per-subquery retrieval execution (internal vector store vs web tool interface).
3. Retrieval validation loop with observable retry state.
4. Synthesis of validated subquery outputs.
5. Streaming heartbeat events from orchestration state.
6. Demo UI wiring for load/run/stream.
7. MCP wrapper exposure.

## Task Status
- [x] Item 1 complete: Implemented `POST /api/agent/plan` to produce ordered subqueries with exactly one tool assignment (`internal_rag` or `web_search`) and observable trajectory/events.
- [x] Added required tests for this slice:
  - API smoke test for `/api/agent/plan` response contract and exclusive tool assignment.
  - Agent trajectory-level test (multi-step decomposition -> tool_selection).
  - Agent outcome-level test (one valid tool per produced subquery).
- [ ] Items 2-7 pending.
