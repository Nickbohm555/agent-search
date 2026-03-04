# Web Search (Onyx-style) — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** Web search is implemented as two tools (search for links/snippets, open_url for full page) so the agent can choose what to read.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: the design and contract of web search as two tools — (1) search returning relevant links and snippets, (2) open_url returning full page content — with the agent deciding what to read (and in what order/parallel). Pattern follows [Onyx’s approach](https://onyx.app/blog/building-internet-search). It does not cover tool selection (tool-selection-per-subquery.md), validation (retrieval-validation.md), or which search API/provider to use (implementation detail).
</scope>

<requirements>
## Requirements

### Tool 1: web.search (or equivalent name)
- Input: search query (e.g. subquery or derived query).
- Output: list of relevant links with snippets/metadata (e.g. title, URL, snippet). No full page content.

### Tool 2: web.open_url (or equivalent name)
- Input: URL.
- Output: full text (or main content) of the page at that URL.

### Agent behavior
- The agent has access to both tools and chooses when to search and which URLs to open (like a human: search first, then read selected pages; can run multiple opens in parallel if desired).

### Codex's Discretion
- Search API provider (e.g. Google, Serper, Exa) and snippet format.
- How full page content is obtained (scraper, Firecrawl, etc.).
- Naming of tools (web.search / web.open_url or project-specific names).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- The system exposes a search tool that returns links and snippets for a query (no full page content).
- The system exposes an open_url (or equivalent) tool that returns full page content for a given URL.
- The agent can use search then open_url to decide what to read; behavior is observable (e.g. which URLs were opened) for logging or streaming.
- Web search is usable as the “web” option when tool selection assigns a subquery to web search.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Deciding which subqueries use web vs internal → tool-selection-per-subquery.md
- Validating web retrieval sufficiency → retrieval-validation.md
- Orchestration and deep agents → orchestration-langgraph.md
</boundaries>

---
*Topic: web-search-onyx-style*
*Spec created: 2025-03-03*
