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
