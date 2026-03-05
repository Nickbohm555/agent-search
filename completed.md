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

