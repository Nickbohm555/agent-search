# Data Loading & Vectorization — Spec

**JTBD:** When I have a complex question, I want the system to decompose it into sub-queries (one tool per subquery), choose internal RAG or web search per subquery, run retrieval with validation, and synthesize a final answer — with a simple TypeScript demo UI, streaming heartbeat, and MCP exposure; web search uses search + open_url (Onyx-style).

**Scope (one sentence, no "and"):** The system supports loading and vectorizing data (e.g. internal Google Docs) for internal RAG.

**Status:** Draft

**Priority (wiki path):** Wiki loading MUST use **LARGE** sources (1000+ chars), a **curated dropdown list** only, **check-before-load** (already vectorized?), and a **LangChain document loader with metadata**. See IMPLEMENTATION_PLAN.md (priority box) and specs/wiki-ingestion.md.

<scope>
## Topic Boundary

This spec covers: ingesting a data source (e.g. Google Docs), processing it into chunks, and indexing those chunks in a vector store used by internal RAG. It does not cover the retrieval API (per-subquery-retrieval.md), the demo UI’s “load” button (demo-ui-typescript.md), or orchestration (orchestration-langgraph.md).
</scope>

<requirements>
## Requirements

### Data sources
- Support at least one source of “internal” documents; primary example: Google Docs (e.g. selected docs or folder).
- "Load" means: fetch/content → chunk (LangChain, see langchain-chunking.md) → embed → write to vector store (pgvector, see pgvector-storage.md) used by per-subquery retrieval.

### Output
- Vector store is populated so that internal RAG retrieval can run queries against it.
- UI or API can trigger a load (see demo-ui-typescript.md for UI surface).

### Codex's Discretion
- Embedding model and pgvector index parameters (see pgvector-storage.md).
- Google Docs integration (API, auth, scope).
- Support for other sources (e.g. local files, Notion) in addition to Google Docs and wiki.
- Exact LangChain splitter and defaults (see langchain-chunking.md).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- User (or UI) can trigger loading/vectorizing of at least one supported data source (e.g. Google Docs).
- After a successful load, internal RAG retrieval returns results from the loaded documents for relevant sub-queries.
- Load outcome is observable (e.g. success/failure, doc count or chunk count) so UI can show status.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Running retrieval over the store → per-subquery-retrieval.md
- UI for triggering load → demo-ui-typescript.md
- Orchestration and tool selection → orchestration-langgraph.md
- Wiki ingestion details → wiki-ingestion.md
- LangChain chunking details → langchain-chunking.md
- pgvector storage and similarity search → pgvector-storage.md
</boundaries>

---
*Topic: data-loading-vectorization*
*Spec created: 2025-03-03*
