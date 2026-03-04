# Streaming Agent Heartbeat — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** A streaming service delivers agent state and progress (e.g. sub-queries) to the UI in real time.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: a backend streaming service that receives or observes pipeline state (e.g. from LangGraph) and pushes updates (sub-queries, progress, validation status, final answer) to clients (e.g. the demo UI). It does not define the UI (demo-ui-typescript.md) or the pipeline (orchestration-langgraph.md), only the streaming contract and delivery.
</scope>

<requirements>
## Requirements

### Source of truth
- Stream is driven by pipeline/orchestration state (e.g. LangGraph state or events).
- At minimum: sub-queries as they are produced; optional: validation steps, retrieval events, synthesis start/done.

### Delivery
- Updates are pushed to the client in real time (e.g. SSE, WebSocket, or similar).
- Acts as the “heartbeat” so the UI can show live progress (sub-queries, status).

### Codex's Discretion
- Protocol (SSE vs WebSocket), message shape, and granularity of events.
- How orchestration is instrumented to emit events (callbacks, middleware, graph hooks).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- When a query is run, the client (e.g. demo UI) receives streaming updates that include sub-queries as they are generated.
- The stream delivers enough information for the UI to show a live view of agent progress (e.g. sub-queries listed, current step, or final answer).
- Streaming is reliable enough that users observe sub-queries and progress during a typical run (observable in the UI).
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Rendering the stream in the UI → demo-ui-typescript.md
- Pipeline implementation and state shape → orchestration-langgraph.md
- MCP exposure of the pipeline → mcp-exposure.md
</boundaries>

---
*Topic: streaming-agent-heartbeat*
*Spec created: 2025-03-03*
