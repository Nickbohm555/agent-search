# Answer Synthesis — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** A main agent combines validated sub-query responses into a final answer.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: taking the validated results for all sub-queries and producing a single, coherent final answer to the original user query. It does not cover decomposition (query-decomposition.md), retrieval (per-subquery-retrieval.md), or validation (retrieval-validation.md).
</scope>

<requirements>
## Requirements

### Input
- Original user query.
- Validated responses (or references) for each sub-query, in order.

### Output
- One final answer (text or structured) that addresses the original query by synthesizing sub-query results.

### Codex's Discretion
- Synthesis model and prompt strategy.
- Handling missing or low-confidence sub-query results.
- Format of final answer (plain text, markdown, structured JSON, etc.).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- Given the original query and all validated sub-query responses, the system produces a single final answer.
- The final answer is coherent and addresses the original query (observable by human or rubric).
- The synthesis step consumes only validated sub-query outputs (no direct retrieval from this component).
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Producing sub-queries → query-decomposition.md
- Retrieving and validating per subquery → per-subquery-retrieval.md, retrieval-validation.md
- Streaming the final answer to UI → streaming-agent-heartbeat.md, demo-ui-typescript.md
</boundaries>

---
*Topic: answer-synthesis*
*Spec created: 2025-03-03*
