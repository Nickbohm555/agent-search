# LangChain Chunking — Spec

**JTBD:** Extend "load documents" so internal docs can be loaded from a geopolitics wiki page, chunked via LangChain, and vectorized in pgvector for RAG.

**Scope (one sentence, no "and"):** The system chunks loaded document content using LangChain text splitters before embedding and storage.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: taking raw document content (from inline docs, wiki ingestion, or other sources) and producing a sequence of text chunks via LangChain (e.g. RecursiveCharacterTextSplitter or equivalent). It does not cover where content comes from (wiki-ingestion.md, inline payload), how chunks are embedded or stored (pgvector-storage.md), or retrieval (per-subquery-retrieval.md).
</scope>

<requirements>
## Requirements

### Input
- Accept document content **and metadata** from the load pipeline. For wiki sources, input MUST come from a **LangChain document loader** (e.g. `WikipediaLoader`) that provides Document objects with metadata (e.g. `title`, `source`, `summary`). Support at least inline documents and wiki-sourced documents.

### Chunking
- Use LangChain to produce chunks (e.g. RecursiveCharacterTextSplitter or equivalent). **Document loader output (with metadata) must flow into the chunking step** so that metadata can be preserved per chunk for attribution.
- Chunks are deterministic and reproducible for the same input and configuration.
- Chunk boundaries and size/overlap are configurable (e.g. chunk size, overlap, separators).

### Output
- Emit a list of chunks per document (order preserved) so the vectorization step can embed and store each chunk.
- **Preserve document metadata** (from LangChain Document) on chunks or documents so retrieval responses can attribute results (source_ref, title, etc.).
- Preserve link to source document (document_id or equivalent) for attribution in retrieval.

### Claude's Discretion
- Which LangChain splitter(s) and default parameters (chunk_size, overlap, separators).
- Handling of very short or empty documents (e.g. single chunk, or skip).
- Character vs token-based sizing if applicable.
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- When loading documents (inline or from wiki), **wiki path uses LangChain document loader output (Documents with metadata)**; chunks are produced by LangChain text splitting; chunk count and content reflect the chosen strategy.
- **Metadata from the LangChain Document** (e.g. title, source) is preserved and visible in retrieval results for attribution.
- Chunks are ordered and associated with their source document so retrieval results show correct document attribution.
- After a load, internal RAG retrieval returns results from the LangChain-chunked content for relevant queries.
- Chunking behavior is configurable (e.g. chunk size or overlap) and observable (e.g. chunks_created in load response).
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Wiki or other document sources → wiki-ingestion.md
- Embedding and pgvector storage → pgvector-storage.md
- Similarity search at query time → pgvector-storage.md, per-subquery-retrieval.md
</boundaries>

---
*Topic: langchain-chunking*
*Spec created: 2026-03-04*
