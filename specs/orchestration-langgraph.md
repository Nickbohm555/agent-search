# Orchestration (DeepAgent) — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** The pipeline runs using the DeepAgent library only (no LangGraph/StateGraph).

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: implementing the end-to-end flow (decomposition → tool selection → per-subquery retrieval → validation → synthesis) using the DeepAgent library. It does not define the behavior of each step (those are other specs) but how they are wired and executed.
</scope>

<requirements>
## Requirements

### Framework
- Use the **DeepAgent library only** for orchestration (no LangGraph or StateGraph).
- Use “deep agents” (subgraphs or agent units from DeepAgent) for subquery handling and tool use.

### Flow
- Query enters → decomposition → for each subquery: tool selection → retrieval → validation (loop until sufficient or stop) → synthesis → final answer.
- State is passed between steps so streaming and MCP can consume progress (see streaming-agent-heartbeat.md, mcp-exposure.md).

### Codex's Discretion
- Exact flow shape (linear vs parallel subquery branches), checkpointing, and error/retry behavior.
- How deep agents are modeled (one agent per subquery vs shared agent with tool routing).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- The full pipeline (decomposition through synthesis) runs via the DeepAgent library.
- It should have its own filesystem with store and subagents as provided by DeepAgent.
- Each logical step (decomposition, tool selection, retrieval, validation, synthesis) executes in the intended order (with validation loop per subquery).
- Deep agents are used where specified (e.g. for subquery handling or tool execution).
- Execution state (or a projection of it) can be used by the streaming service for UI heartbeat.
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
