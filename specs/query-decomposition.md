# Query Decomposition — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** The system breaks a user query into sub-queries suitable for retrieval.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: taking a single user query and producing a list of sub-queries that can each be answered by one retrieval path. It does not cover which tool (internal vs web) to use per subquery (tool-selection-per-subquery.md), running retrieval (per-subquery-retrieval.md), or synthesis (answer-synthesis.md).
</scope>

<requirements>
## Requirements

### Input
- Accept a single natural-language user query (string).

### Output
- Produce an ordered list of sub-queries such that each subquery is answerable by a single tool (internal RAG or web search).
- Sub-queries are simple enough that one tool suffices per subquery (no subquery that would require both internal and web search).

### Codex's Discretion
- Number of sub-queries (min/max or adaptive).
- Decomposition strategy (LLM-based, rule-based, or hybrid).
- Ordering of sub-queries (dependency-aware vs arbitrary).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- Given a complex user query, the system produces at least one sub-query and each sub-query is a single, focused question.
- Each produced sub-query can be reasonably answered by either internal RAG or web search alone (no subquery that inherently requires both).
- Sub-queries are exposed to the rest of the pipeline (and to streaming) so downstream steps and UI can consume them.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Which tool to use per subquery → tool-selection-per-subquery.md
- Running retrieval for each subquery → per-subquery-retrieval.md
- Validating or deepening retrieval → retrieval-validation.md
- Combining answers → answer-synthesis.md
- Streaming sub-queries to UI → streaming-agent-heartbeat.md, demo-ui-typescript.md
</boundaries>

---
*Topic: query-decomposition*
*Spec created: 2025-03-03*
