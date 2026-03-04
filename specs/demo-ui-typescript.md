# Demo UI (TypeScript) — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** A simple TypeScript demo UI lets users load/vectorize data and view sub-queries and agent progress via streaming.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: a simple, sleek TypeScript front end that (1) provides an area to trigger loading/vectorizing data (e.g. Google Docs), (2) shows sub-queries as they are streamed, and (3) uses the streaming service as the UI heartbeat for agent progress. It does not implement the streaming backend (streaming-agent-heartbeat.md), data loading backend (data-loading-vectorization.md), or pipeline (orchestration-langgraph.md).
</scope>

<requirements>
## Requirements

### Load / vectorize
- An area (e.g. button + status) to “load” data — i.e. trigger vectorization of a supported source (e.g. internal Google Docs).
- User can initiate load and see feedback (e.g. loading, success, error).

### Sub-queries and progress
- Display sub-queries as they arrive via the streaming heartbeat (e.g. list or timeline).
- Show agent progress (e.g. which step is active, when synthesis is done) using the same stream.

### UX
- Simple and sleek; TypeScript codebase.
- Input for the user query and a way to start a run; display of final answer when available.

### Codex's Discretion
- Framework (React, Vue, Svelte, etc.), styling approach, and exact layout.
- Whether “load” is per-session or persisted; query history.
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- User can trigger a data load (e.g. vectorize Google Docs) from the UI and see a clear outcome (success or error).
- When a query is run, sub-queries appear on the front end as they are streamed (real-time or near real-time).
- User sees agent progress (e.g. sub-queries, then final answer) via the streaming heartbeat.
- The UI is simple and sleek and implemented in TypeScript.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Streaming service implementation → streaming-agent-heartbeat.md
- Backend data loading and vectorization → data-loading-vectorization.md
- Pipeline and orchestration → orchestration-langgraph.md
- MCP exposure → mcp-exposure.md
</boundaries>

---
*Topic: demo-ui-typescript*
*Spec created: 2025-03-03*
