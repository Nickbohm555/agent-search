# Implementation Plan

## 1. Wipe the DB (internal data only)

- **Goal:** Clear all internal documents and chunks so you can reload from scratch (e.g. after schema changes or to re-vectorize).
- **Options:**
  - **A. Truncate tables (recommended):** Run once to wipe only internal data; DB and schema stay.
    ```sql
    TRUNCATE internal_documents CASCADE;
    ```
    (Chunks are removed by FK cascade.) Run via: `docker compose exec db psql -U agent_user -d agent_search -c "TRUNCATE internal_documents CASCADE;"`
  - **B. Full DB reset:** For a completely fresh DB (all data + schema re-applied): `docker compose down -v`, then `docker compose up -d` and `docker compose exec backend uv run alembic upgrade head`.
- **Deliverable:** Document the truncate command in AGENTS.md or a short “Wipe internal data” section so it’s easy to run.

---

## 2. Metadata column on `internal_document_chunks`

- **Goal:** Store per-chunk attribution in a single column: **source** (wiki link) and **topic** (topic name). No other fields in metadata for now.
- **Schema:**
  - Add column: `chunk_metadata` (JSONB, nullable). (Name avoids shadowing SQLAlchemy `Base.metadata`.)
  - Stored shape: `{ "source": "<wiki page URL>", "topic": "<topic name>" }`.
  - For inline docs, `source`/`topic` are derived from document `source_ref`/`title`.
- **Implementation steps (done):**
  1. **Migration:** `0004_chunk_metadata` adds `chunk_metadata` (JSONB, nullable) to `internal_document_chunks`.
  2. **Model:** `InternalDocumentChunk.chunk_metadata` (JSONB, nullable).
  3. **Populate on write:** In `_persist_documents`, each chunk gets `chunk_metadata = {"source": document_input.source_url or document_input.source_ref, "topic": document_input.title}`. Wiki ingestion sets `source_url` from LangChain doc metadata so the wiki link is stored.
  4. **Retrieval (optional):** Add `chunk_metadata` to `InternalRetrievedChunk` and fill from the chunk row when building results.
- **Verification:**
  - After migration, `internal_document_chunks` has a `chunk_metadata` column.
  - After a wiki load, chunk rows have `chunk_metadata` with `source` (URL) and `topic` (name).
  - (Optional) Retrieve endpoint returns chunk metadata when present.

---

## Order of operations

1. ~~Add migration and model for `internal_document_chunks.chunk_metadata`.~~ Done.
2. Run migration: `docker compose exec backend uv run alembic upgrade head`.
3. (Optional) Wipe internal data: `docker compose exec db psql -U agent_user -d agent_search -c "TRUNCATE internal_documents CASCADE;"`.
4. ~~Update load path to set chunk `chunk_metadata` (source + topic).~~ Done (wiki sets `source_url`, inline uses `source_ref`/title).
5. ~~Optionally expose `chunk_metadata` on retrieval response.~~ Done in this loop:
   - `InternalRetrievedChunk` now includes `chunk_metadata`.
   - `retrieve_internal_data` now returns chunk metadata for both PostgreSQL pgvector ordering and SQLite fallback ordering.
   - Smoke tests now verify metadata shape/content for inline and wiki retrieval paths.

## Loop Update (2026-03-04)

- **Completed highest-priority item:** retrieval response now exposes chunk attribution metadata (`source`, `topic`) from `internal_document_chunks.chunk_metadata`.
- **Compatibility fix made while running required tests:** MCP `/api/mcp/tools` preserves `input_schema` (snake_case) for existing API consumers, while JSON-RPC `tools/list` keeps MCP-style `inputSchema`.
- **Validation performed:**
  - `curl -sf http://localhost:8000/api/health`
  - `docker compose exec backend uv run pytest` (58 passed)
  - `docker compose exec frontend npm run test -- --run` (32 passed)
  - `docker compose exec frontend npm run typecheck` (pass)

## Loop Update (2026-03-04, retrieval attribution readout)

- **Completed highest-priority item this run:** surfaced chunk attribution metadata (`topic`, `source`) in frontend retrieval readouts for internal sub-query results.
- **Implementation details:**
  - Added frontend runtime type support for `InternalRetrievedChunk.chunk_metadata`.
  - Strengthened `runAgent` response validation to verify `retrieval_results` nested payload shapes (internal chunks, web results, opened pages) and reject malformed metadata.
  - Updated progress-history retrieval rendering to include attribution when metadata is present.
- **Tests added/updated for this item:**
  - `src/frontend/src/App.test.tsx`: retrieval/validation readout test now asserts internal retrieval attribution text includes topic/source.
  - `src/frontend/src/utils/api.test.ts`: added success-path test for run payloads with valid `chunk_metadata`; added malformed-path test that rejects invalid `chunk_metadata`.
- **Validation performed:**
  - `curl -sf http://localhost:8000/api/health`
  - `docker compose exec backend uv run pytest` (58 passed)
  - `docker compose exec frontend npm run test -- --run` (34 passed)
  - `docker compose exec frontend npm run typecheck` (pass)

## Loop Update (2026-03-04, streamed runtime error contract)

- **Completed highest-priority item this run:** added structured streamed runtime error handling so `/api/agents/run/stream` emits an `error` SSE event on runtime failure and the frontend stream client surfaces it as a deterministic `runtime` API error.
- **Implementation details:**
  - Extended backend stream event schema to include `error`.
  - Updated `stream_runtime_agent` to catch `astream`/`ainvoke` failures and emit an ordered `{ message, retryable }` error event after heartbeat instead of failing with opaque stream interruption.
  - Extended frontend stream event type guards to accept `error` events and updated stream parsing to return `{ type: "runtime" }` errors immediately when such an event is received.
  - Stabilized two existing App in-flight tests by explicitly selecting `inline` load source (app default is `wiki`), preventing false negatives unrelated to stream logic.
- **Tests added/updated for this item:**
  - `src/backend/tests/api/test_streaming_compile_invoke_dummy.py`: added smoke test asserting stream emits `heartbeat` then `error` with structured payload on invoke failure.
  - `src/frontend/src/utils/stream.test.ts`: added unit test asserting backend `error` event maps to frontend `runtime` error result.
  - `src/frontend/src/App.test.tsx`: adjusted two existing in-flight UI tests to explicitly set inline source for deterministic control-state assertions.
- **Validation performed:**
  - `curl -sf http://localhost:8000/api/health`
  - `docker compose exec backend uv run pytest` (59 passed)
  - `docker compose exec frontend npm run test -- --run` (35 passed)
  - `docker compose exec frontend npm run typecheck` (pass)
