# MCP Exposure — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** The pipeline is exposed via an MCP wrapper so clients (e.g. FAS MCP) can invoke it.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: exposing the RAG pipeline (query in → final answer out, and optionally streaming) as an MCP server or tool so that clients such as FAS MCP can call it. It does not define the pipeline behavior (orchestration-langgraph.md) or the demo UI (demo-ui-typescript.md).
</scope>

<requirements>
## Requirements

### MCP wrapper
- The pipeline is callable via MCP (e.g. as a tool or set of tools).
- User intends to use FAS MCP as the client; the wrapper must be compatible with how FAS MCP invokes MCP servers/tools.

### Invocation
- At minimum: client can send a query and receive a final answer (sync or async).
- Optional: client can subscribe to or receive streaming updates (sub-queries, progress) if the streaming service is integrated.

### Codex's Discretion
- Exact MCP transport (stdio, SSE, etc.) and tool naming.
- Whether streaming is exposed via MCP or only via the demo UI backend.
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- A client (e.g. FAS MCP) can invoke the pipeline through MCP and receive a final answer for a given query.
- The MCP wrapper correctly delegates to the LangGraph pipeline (orchestration) and returns the synthesized answer.
- Invocation contract is stable enough for the user to use with FAS MCP (observable by successful end-to-end call from the client).
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Pipeline implementation → orchestration-langgraph.md
- Demo UI and its backend → demo-ui-typescript.md, streaming-agent-heartbeat.md
- Internal RAG or web search implementation → per-subquery-retrieval.md, web-search-onyx-style.md
</boundaries>

---
*Topic: mcp-exposure*
*Spec created: 2025-03-03*
