# Wiki Ingestion — Spec

**JTBD:** Extend "load documents" so internal docs can be loaded from a geopolitics wiki page, chunked via LangChain, and vectorized in pgvector for RAG.

**Scope (one sentence, no "and"):** The system fetches and extracts document content from a geopolitics wiki page for use by the load pipeline.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: resolving a wiki page URL (e.g. a specific geopolitics article), fetching its HTML/content, and extracting plain text (and optional metadata such as title) so that downstream chunking and vectorization can consume it. It does not cover chunking (langchain-chunking.md), embedding or storing in pgvector (pgvector-storage.md), or the UI that triggers load (demo-ui-typescript.md).
</scope>

<requirements>
## Requirements

### Source
- Support loading from at least one geopolitics wiki page (e.g. a fixed or configurable URL).
- "Load from wiki" means: fetch the page, extract main article text, and produce one or more document-like inputs (title + content) for the existing load pipeline.

### Output
- Extracted content is available as structured document(s) (e.g. title, content, source_ref) suitable for chunking and vectorization.
- Source type or ref should identify the wiki origin so retrieval can attribute results.

### Claude's Discretion
- Which wiki (e.g. Wikipedia, Fandom, or other) and exact URL(s).
- Parsing strategy (e.g. HTML parser, readability-style extraction, or wiki-specific API).
- Handling of sections, tables, or references (include as text vs strip).
- Caching or rate limiting for repeated loads.
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- User (or UI/API) can trigger a load that uses a geopolitics wiki page as the source.
- After a successful wiki load, the system has extracted at least one document (title + content) from that page; content is non-empty and suitable for chunking.
- Load outcome is observable (e.g. success/failure, document count or byte count) so UI or API can show status.
- Retrieved internal RAG results can be attributed to the wiki source (e.g. source_ref or source_type indicates wiki).
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Chunking extracted content → langchain-chunking.md
- Storing embeddings in pgvector → pgvector-storage.md
- UI for triggering load → demo-ui-typescript.md
- Per-subquery retrieval over the store → per-subquery-retrieval.md
</boundaries>

---
*Topic: wiki-ingestion*
*Spec created: 2026-03-04*
