# Tool Selection per Subquery — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** The system assigns each subquery to exactly one tool: internal RAG or web search.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: deciding, for each sub-query produced by decomposition, whether to use internal RAG (over vectorized docs) or web search. One tool per subquery; no subquery uses both. It does not cover decomposition (query-decomposition.md), running the chosen tool (per-subquery-retrieval.md, web-search-onyx-style.md), or orchestration (orchestration-langgraph.md).
</scope>

<requirements>
## Requirements

### Input
- One or more sub-queries from query decomposition.

### Output
- For each subquery, a single tool assignment: internal RAG or web search.

### Rule
- No subquery may be assigned both internal RAG and web search; assignment is exclusive.

### Codex's Discretion
- Decision model (LLM call, heuristics, or hybrid).
- Fallback when uncertain (default to internal vs web).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- For every sub-query, the system produces exactly one tool choice: internal RAG or web search.
- No sub-query is executed with both internal and web search for the same subquery.
- Tool assignments are available to the retrieval/orchestration layer and (optionally) to streaming for UI display.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Producing sub-queries → query-decomposition.md
- Executing internal RAG → per-subquery-retrieval.md
- Executing web search → web-search-onyx-style.md
- Orchestrating the flow → orchestration-langgraph.md
</boundaries>

---
*Topic: tool-selection-per-subquery*
*Spec created: 2025-03-03*
