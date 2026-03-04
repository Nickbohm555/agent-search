# Retrieval Validation — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** The system checks whether retrieved info for a subquery is sufficient and triggers more retrieval or deeper search when not.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: after retrieval for a subquery, deciding if the retrieved docs/info are enough to answer it; if not, triggering more retrieval or diving deeper into docs. It does not cover running the initial retrieval (per-subquery-retrieval.md), web search behavior (web-search-onyx-style.md), or synthesis (answer-synthesis.md).
</scope>

<requirements>
## Requirements

### Validation question
- For each subquery’s retrieval result, ask: “Is the retrieved info sufficient to answer this subquery?”

### When not sufficient
- Trigger one or more of: search more docs (e.g. more chunks or different query), or dive deeper into already-retrieved docs (e.g. expand or re-retrieve with focus).
- Loop until sufficient or a stopping condition (e.g. max iterations, user timeout).

### Codex's Discretion
- How “sufficient” is determined (LLM, heuristics, or hybrid).
- Max validation iterations per subquery.
- What “dive deeper” means concretely (re-retrieve with subquery, expand chunk context, etc.).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- After retrieval for a subquery, the system evaluates whether the retrieved info is enough to answer that subquery.
- If not enough, the system triggers at least one follow-up action (more retrieval or deeper use of docs).
- The validation loop eventually stops (sufficient or stopping condition) and passes a result to synthesis.
- Behavior is observable (e.g. “validated” vs “retried”) so streaming/UI can reflect validation state if desired.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Running retrieval → per-subquery-retrieval.md
- Combining validated results → answer-synthesis.md
- Web search tool behavior → web-search-onyx-style.md
</boundaries>

---
*Topic: retrieval-validation*
*Spec created: 2025-03-03*
