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

