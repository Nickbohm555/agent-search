## Section 1: Wipe – DB logic in common/db

**Single goal:** Implement SQLAlchemy logic that deletes all internal document chunks and documents in the correct order (chunks first, then documents). No route yet; only the shared DB function.

**Details:**
- Delete all `InternalDocumentChunk` rows, then all `InternalDocument` rows (respect FK).
- Add logging (e.g. row counts deleted).

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/common/__init__.py` | Package marker. |
| `src/backend/common/db/__init__.py` | Re-export wipe function. |
| `src/backend/common/db/wipe.py` | `wipe_all_internal_data(session: Session) -> None`. Delete chunks then documents. Logging. |

**How to test:** Backend pytest. TDD. Test: call `wipe_all_internal_data` with a session that has documents/chunks; assert both tables are empty after. Use test DB or transaction rollback for isolation.

---

## Section 2: Wipe – route, schema, and service wiring

**Single goal:** Expose wipe via FastAPI. Add Pydantic response schema and wire `POST /api/internal-data/wipe` to the service, which calls `wipe_all_internal_data`.

**Details:**
- Response body: `{ "status": "success", "message": "..." }` (Pydantic model).
- Route calls a service function that calls `common.db.wipe.wipe_all_internal_data(db)`.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/schemas/internal_data.py` | Add `WipeResponse(BaseModel)` with `status: Literal["success"]`, `message: str`. |
| `src/backend/services/internal_data_service.py` | Implement `wipe_internal_data(db: Session)`: call `common.db.wipe.wipe_all_internal_data(db)`; optional logging. |
| `src/backend/routers/internal_data.py` | Change wipe route to return `response_model=WipeResponse`; call `wipe_internal_data(db)`. |

**How to test:** Backend pytest. Call `POST /api/internal-data/wipe`; assert status 200, response shape; assert internal_documents and internal_document_chunks tables are empty.

---

## Section 3: Wiki load – produce LangChain Documents with metadata

**Single goal:** Ensure the Wikipedia load path returns `langchain_core.documents.Document` instances with `page_content` and `metadata` (e.g. source URL, title). Add logging for document count and metadata.

**Details:**
- Use `from langchain_core.documents import Document`.
- Each loaded wiki page → `Document(page_content=..., metadata={"source": url, "title": ...})`.
- Keep or adapt existing `WikipediaLoader` usage; normalize output to `Document` and log.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/wiki_ingestion_service.py` | Ensure `_load_wikipedia_documents` / `resolve_wiki_documents` (or equivalent) return `list[Document]` with `page_content` and `metadata`. Add logging (doc count, metadata keys). |

**How to test:** Backend pytest. TDD. Load one known wiki source (e.g. geopolitics); assert result is list of `Document`, each has `page_content` and `metadata` with expected keys (e.g. source, title). Assert logging (e.g. via caplog).

**Test results (Docker-based):**
- Added and ran `docker compose exec backend uv run pytest tests/services/test_wiki_ingestion_service.py` (2 passed): verified `resolve_wiki_documents` returns `list[Document]`, includes `page_content`, normalized metadata keys (`source`, `title`), and emits caplog-verified logging with doc count and metadata keys.
- Ran `docker compose exec backend uv run pytest` (4 passed): full backend suite green, including new wiki ingestion service tests and existing wipe tests.
- Ran `docker compose exec frontend npm run typecheck` (passed).
- Ran `docker compose exec frontend npm run test` (fails because no frontend test files exist yet; unchanged by this backend-only section).
- Ran health check with `curl http://localhost:8000/api/health` (failed due pre-existing backend startup/import error: `ImportError: cannot import name 'run_runtime_agent' from services.agent_service`; unrelated to Section 3 changes).

---
## Section 4: Wiki load – chunk with RecursiveCharacterTextSplitter

**Single goal:** Add a function that takes a list of LangChain Documents and returns chunked Documents using `RecursiveCharacterTextSplitter`. Preserve metadata on chunks; add logging.

**Details:**
- Use `RecursiveCharacterTextSplitter` (set `chunk_size`, `chunk_overlap`; optionally `separators`, `keep_separator`, `is_separator_regex`).
- Input: `list[Document]`. Output: `list[Document]` (more, smaller docs with same metadata shape).
- Log chunk count per doc and total.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/wiki_ingestion_service.py` | Add `chunk_wiki_documents(documents: list[Document], chunk_size=..., chunk_overlap=...) -> list[Document]`. Use `RecursiveCharacterTextSplitter`. Preserve metadata. Logging. |

**How to test:** Backend pytest. TDD. Given 1–2 Documents, assert output has more Documents; each has `page_content` and metadata; chunk sizes within expected range. Assert logging.

**Test results (Docker-based):**
- Added and ran `docker compose exec backend uv run pytest tests/services/test_wiki_ingestion_service.py` (4 passed): verified chunking splits 1–2 input `Document` objects into more output chunks, preserves metadata, keeps chunk sizes within the configured `chunk_size`, validates bad chunk params, and emits per-doc plus total chunking logs.
- Ran `docker compose exec backend uv run pytest` (6 passed): full backend suite green including wipe API/DB tests and wiki ingestion tests.
- Ran `docker compose exec frontend npm run typecheck` (passed).
- Ran `docker compose exec frontend npm run test` (fails because no frontend test files exist yet; unchanged by this backend-only section).
- Ran health check with `curl -i http://localhost:8000/api/health` (failed due pre-existing backend startup/import error: `ImportError: cannot import name 'run_runtime_agent' from services.agent_service`; unrelated to Section 4 changes).

---
## Section 5: Frontend – wiki dropdown from hardcoded list

**Single goal:** Ensure the wiki source dropdown is populated from a hardcoded list of topics (geopolitics-focused: Geopolitics, Strait of Hormuz, NATO, etc.). Can mirror backend source list or be frontend-only.

**Details:**
- Dropdown options: fixed list (e.g. same labels as backend `WikiSourceDefinition`).
- If list comes from API (`/api/internal-data/wiki-sources`), ensure backend returns that list; otherwise define a hardcoded list in the frontend (e.g. constants or inline).

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/App.tsx` | Dropdown options from hardcoded list or from `listWikiSources()`; display label and “loaded” state if from API. |
| `src/frontend/src/utils/constants.ts` (optional) | Hardcoded wiki topic list (ids + labels) if not using API for options. |
| `src/frontend/src/utils/api.ts` | No change if already using `listWikiSources`; otherwise ensure types match. |

**How to test:** Manual check or frontend test: open app, assert dropdown shows expected wiki topics (e.g. Geopolitics, NATO, …). If using API, assert options update when “loaded” state changes.

**Test results (Docker-based):**
- Added and ran `docker compose exec frontend npm run test` (2 passed): `src/App.test.tsx` verifies the wiki dropdown renders curated hardcoded topics (e.g. Geopolitics, Strait of Hormuz, NATO) when wiki-source API fetch fails, and verifies API `already_loaded` state merges into option labels (`Geopolitics (loaded)`) while retaining hardcoded options.
- Ran `docker compose exec frontend npm run typecheck` (passed).
- Ran `docker compose exec backend uv run pytest` (6 passed).
- Ran health check with `curl -sS -i http://localhost:8000/api/health` (failed: `curl: (56) Recv failure: Connection reset by peer`). Backend logs confirm pre-existing startup import error: `ImportError: cannot import name 'run_runtime_agent' from 'services.agent_service'`.

---
## Section 6: Vector store – embeddings utility

**Single goal:** Provide a single place for embedding dimension and embedding model used by PGVector and (if needed) SQLAlchemy `Vector(EMBEDDING_DIM)`.

**Details:**
- Export `EMBEDDING_DIM` (int) and a way to get an `Embeddings` instance (e.g. `get_embedding_model()` or module-level instance).
- Used by `models.py` (Vector column) and later by PGVector and the retriever.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/utils/__init__.py` | Package marker (if not present). |
| `src/backend/utils/embeddings.py` | `EMBEDDING_DIM` constant; `get_embedding_model()` or `embeddings` instance. Match backend’s chosen embedding provider. |

**How to test:** Backend pytest. Assert `EMBEDDING_DIM` is a positive int; assert `get_embedding_model()` (or equivalent) returns an object with an `embed_documents` (or equivalent) method. Mock API keys if needed.

**Test results (Docker-based):**
- Added and ran `docker compose exec backend uv run pytest tests/utils/test_embeddings.py` (2 passed): verified `EMBEDDING_DIM` is a positive int and `get_embedding_model()` returns an embeddings-like object with `embed_documents`, producing vectors with length `EMBEDDING_DIM`.
- Ran `docker compose exec backend uv run pytest` (8 passed): full backend suite green including new embeddings tests plus existing API/DB/wiki tests.
- Ran `docker compose exec frontend npm run test` (passed, 2 tests).
- Ran `docker compose exec frontend npm run typecheck` (passed).
- Ran health check with `curl -sS -i http://localhost:8000/api/health` (failed: `curl: (56) Recv failure: Connection reset by peer`). Backend logs show pre-existing startup import error: `ImportError: cannot import name 'run_runtime_agent' from 'services.agent_service'`; unrelated to Section 6 changes.

---
