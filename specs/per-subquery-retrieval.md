# Per-Subquery Retrieval — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** For each sub-query, the system runs a RAG retrieval step (internal or web).

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: executing retrieval for a single sub-query using the tool already assigned (internal RAG or web search). It does not cover assigning the tool (tool-selection-per-subquery.md), validating sufficiency or deepening (retrieval-validation.md), web search implementation details (web-search-onyx-style.md), or loading/vectorizing data (data-loading-vectorization.md).
</scope>

<requirements>
## Requirements

### Internal RAG path
- Run retrieval over the vectorized document store using the subquery as the query.
- Return retrieved chunks/documents (or references) for use by validation and synthesis.

### Web path
- Delegate to web search tools (search + open_url per web-search-onyx-style.md); this spec assumes that interface is available.

### Codex's Discretion
- Number of chunks/documents to retrieve for internal RAG.
- Embedding model and vector store implementation.
- How retrieved content is passed to validation (raw chunks vs formatted).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- Given a sub-query and tool assignment (internal or web), the system runs the corresponding retrieval and returns retrievable content (chunks or web snippets/pages).
- Internal RAG retrieval returns content from the loaded/vectorized data store only.
- Web retrieval follows the search + open_url pattern; the agent can choose which pages to read.
- Output is consumable by the validation step (and optionally streamed for UI).
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Tool assignment → tool-selection-per-subquery.md
- Sufficiency check and “search more / dive deeper” → retrieval-validation.md
- Web search API design → web-search-onyx-style.md
- Populating the vector store → data-loading-vectorization.md
</boundaries>

---
*Topic: per-subquery-retrieval*
*Spec created: 2025-03-03*
