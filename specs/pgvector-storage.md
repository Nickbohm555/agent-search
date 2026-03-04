# pgvector Storage & Similarity Search — Spec

**JTBD:** Extend "load documents" so internal docs can be loaded from a geopolitics wiki page, chunked via LangChain, and vectorized in pgvector for RAG.

**Scope (one sentence, no "and"):** The system stores chunk embeddings in pgvector and runs similarity search in the database for internal RAG retrieval.

**Status:** Draft

<scope>
## Topic Boundary

This spec covers: persisting chunk embeddings in Postgres using the pgvector extension (native vector column), and running similarity search (e.g. cosine or inner product) in the database when answering internal RAG queries. It does not cover chunking (langchain-chunking.md), wiki or other ingestion (wiki-ingestion.md), or orchestration (orchestration-langgraph.md).
</scope>

<requirements>
## Requirements

### Storage
- Use pgvector to store one embedding vector per chunk (dimension must match the embedding model in use).
- Migrate or replace the current embedding_json (text) approach with a native vector column so that similarity is computed in the database.
- Preserve chunk metadata (document_id, chunk_index, content, source_ref) for retrieval response shape.

### Indexing
- Support efficient similarity search (e.g. ivfflat or hnsw index on the vector column) so retrieval over large chunk sets is performant.

### Retrieval
- Internal RAG retrieval runs a similarity query in Postgres (e.g. ORDER BY embedding <=> query_embedding LIMIT n) and returns scored chunks with metadata.
- Query embedding is produced with the same model/dimension as stored embeddings.

### Claude's Discretion
- Embedding model and dimension (e.g. 384 or 1536); must be consistent for store and query.
- Index type and parameters (ivfflat lists, hnsw m/ef_construction).
- Exact similarity operator (<=> for cosine, <-> for L2, or inner product).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- After a load, chunk embeddings are stored in a pgvector vector column (not only in JSON text); schema and migrations reflect this.
- Internal RAG retrieval uses a database-side similarity query (e.g. pgvector operator) and returns top-k chunks with scores.
- Load response remains observable (e.g. documents_loaded, chunks_created); retrieval response shape (content, score, document_title, source_ref) is unchanged for consumers.
- For a given query, retrieval returns the same or better relevance compared to the previous in-memory cosine approach, with search executed in the database.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Chunking strategy → langchain-chunking.md
- Document sources (wiki, inline) → wiki-ingestion.md
- Tool selection and orchestration → orchestration-langgraph.md, tool-selection-per-subquery.md
</boundaries>

---
*Topic: pgvector-storage*
*Spec created: 2026-03-04*
