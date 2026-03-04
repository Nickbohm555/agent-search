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

### Source (priority: LARGE + curated list)
- **LARGE wiki sources only**: minimum ~1000+ characters per source. Content must be chunked into multiple documents/chunks; no tiny fixture-style snippets for the main wiki load path.
- **Curated list only**: user selects from a fixed list of allowed options (e.g. dropdown). Backend exposes this list (e.g. `GET /api/internal-data/wiki-sources`) and rejects any wiki identifier not in the list.
- **Check before load**: system must indicate whether a given wiki source is already vectorized/downloaded (e.g. by `source_ref` or document title). UI/API should prevent or warn on duplicate load.
- **MUST use LangChain document loader with metadata**: wiki ingestion MUST use a LangChain document loader (e.g. `WikipediaLoader` from `langchain_community`) that returns Document objects with metadata (e.g. `title`, `source`, `summary`). No ad-hoc HTTP scraping or fixture-only content for the main wiki path.
- "Load from wiki" means: resolve the selected option from the list, load via LangChain loader, and produce one or more document-like inputs (title, content, metadata, source_ref) for the existing load pipeline.

### Allowed wiki source list (dropdown options)
- Backend defines and exposes a fixed list; only these IDs are accepted. Example options: `geopolitics`, `strait_of_hormuz`, `nato`, `european_union`, `united_nations`, `foreign_policy_us`, `middle_east`, `cold_war`, `international_relations`, `balance_of_power` (or equivalent Wikipedia article queries). See IMPLEMENTATION_PLAN.md for the full table.

### Output
- Extracted content is available as structured document(s) (title, content, source_ref, and any loader metadata) suitable for chunking and vectorization.
- Source type or ref identifies the wiki origin so retrieval can attribute results; metadata from the LangChain Document must be persisted where needed for attribution.

### Claude's Discretion
- Exact mapping from option ID to Wikipedia (or other wiki) query; `doc_content_chars_max` or equivalent to ensure large content; `load_all_available_meta` for metadata. Caching or rate limiting for repeated loads.
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- User selects from a **dropdown of allowed wiki sources only**; only options from the curated list are loadable; unknown IDs are rejected.
- Wiki ingestion **uses a LangChain document loader** (e.g. `WikipediaLoader`); loaded Documents carry **metadata** that is persisted and visible in retrieval.
- **LARGE content**: after a successful wiki load, content is large enough to produce multiple chunks (e.g. 1000+ chars, multiple chunks created); no tiny single-chunk fixtures in main path.
- System indicates **whether a wiki source is already vectorized/downloaded** so the user can avoid duplicate load; UI/API reflects this.
- Retrieved internal RAG results can be attributed to the wiki source (source_ref, source_type, and any persisted loader metadata).
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
