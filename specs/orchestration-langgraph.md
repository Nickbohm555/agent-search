# Orchestration (LangGraph) — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** The pipeline runs as a LangGraph flow with deep agents.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: implementing the end-to-end flow (decomposition → tool selection → per-subquery retrieval → validation → synthesis) as a LangGraph graph using deep agents (subgraphs or agent nodes). It does not define the behavior of each step (those are other specs) but how they are wired and executed.
</scope>

<requirements>
## Requirements

### Framework
- Use LangGraph to define nodes and edges for: decomposition, tool selection, retrieval, validation, synthesis.
- Use “deep agents” (nested or reusable agent subgraphs) where appropriate for subquery handling or tool use.

### Flow
- Query enters → decomposition → for each subquery: tool selection → retrieval → validation (loop until sufficient or stop) → synthesis → final answer.
- State is passed between nodes so streaming and MCP can consume progress (see streaming-agent-heartbeat.md, mcp-exposure.md).

### Codex's Discretion
- Exact graph shape (linear vs parallel subquery branches), checkpointing, and error/retry behavior.
- How deep agents are modeled (one agent per subquery vs shared agent with tool routing).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- The full pipeline (decomposition through synthesis) runs as a LangGraph graph.
- Each logical step (decomposition, tool selection, retrieval, validation, synthesis) is represented in the graph and executes in the intended order (with validation loop per subquery).
- Deep agents are used where specified (e.g. for subquery handling or tool execution).
- Graph state (or a projection of it) can be used by the streaming service for UI heartbeat.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Behavior of decomposition, tool selection, retrieval, validation, synthesis → their respective specs.
- Pushing state to UI → streaming-agent-heartbeat.md
- Exposing the pipeline via MCP → mcp-exposure.md
</boundaries>

---
*Topic: orchestration-langgraph*
*Spec created: 2025-03-03*
