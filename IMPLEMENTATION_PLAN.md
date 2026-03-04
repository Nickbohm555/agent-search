- [ ] P0: Add backend wiki load source that feeds the existing load pipeline and is triggerable via `/api/internal-data/load`.
  - Scope: Extend `InternalDataLoadRequest` to support a wiki source mode (e.g., wikipedia URL/topic input), fetch and extract article title/content, normalize into document inputs, then run the same chunk/embed/store path used by inline docs.
  - Verification requirements (from `specs/wiki-ingestion.md` + `specs/data-loading-vectorization.md`):
    - Backend smoke test: wiki-mode load request returns `200` with `status=success`, `documents_loaded >= 1`, `chunks_created >= 1`.
    - Backend smoke test: extracted document fields are non-empty (`title`, `content`) and load outcome is observable via counts in response.
    - Backend smoke/integration test: subsequent `/api/internal-data/retrieve` for a related query returns at least one result attributed to wiki origin (`source_type` or `source_ref` indicates wiki/Wikipedia).
    - Determinism guard: tests must not depend on live external wiki network; use fixture/mocked wiki fetch content.

- [ ] P0: Migrate chunk embedding storage from text JSON to native pgvector column and keep metadata/response contract stable.
  - Scope: Add Alembic migration(s) to enable pgvector extension and add vector column on `internal_document_chunks`, update SQLAlchemy model and load path to persist embeddings in vector column (not only JSON text).
  - Verification requirements (from `specs/pgvector-storage.md`):
    - Backend migration/schema test or DB smoke: pgvector extension exists and `internal_document_chunks` has a vector embedding column after upgrade.
    - Backend load test: after load, stored chunks contain vector embeddings in DB-native vector column.
    - Contract test: load response still reports observable `documents_loaded` and `chunks_created` fields unchanged.

- [ ] P0: Move internal retrieval scoring to database-side pgvector similarity query.
  - Scope: Replace in-memory Python cosine scoring over all rows with top-k similarity query in Postgres using pgvector operator; keep response shape (`content`, `score`, `document_title`, `source_ref`, etc.) unchanged.
  - Verification requirements (from `specs/pgvector-storage.md` + `specs/per-subquery-retrieval.md`):
    - Backend smoke test: `/api/internal-data/retrieve` returns top-k scored chunks from loaded store with unchanged schema.
    - Backend agent smoke test: `/api/agents/run` internal retrieval path returns wiki/inline loaded content from the vectorized store only.
    - Relevance regression test: deterministic fixture query ranks expected relevant chunk at/near top compared with non-relevant chunk set.

- [ ] P1: Wire UI "Load Data" click to support Wikipedia load mode and show clear load outcome.
  - Scope: Update frontend load action/API payloads so user can trigger wiki-backed load (not only hardcoded inline docs), while preserving existing status UX.
  - Verification requirements (from `specs/demo-ui-typescript.md` + `specs/wiki-ingestion.md`):
    - Frontend interaction test: clicking `Load Data` in wiki mode calls `/api/internal-data/load` with wiki source payload.
    - Frontend interaction test: success path shows clear status message with returned counts.
    - Frontend interaction test: backend/API error path shows clear error state in load status region.

- [ ] P1: Add scoped end-to-end smoke covering click-to-load (wiki) through retrieval attribution.
  - Scope: Add one deterministic smoke path validating the scoped user story across UI/API/backend boundaries using controlled wiki fixture input.
  - Verification requirements (combined scoped acceptance):
    - User-triggered load operation completes successfully and is observable.
    - Wiki content becomes retrievable through internal RAG path.
    - Retrieved result metadata preserves wiki attribution fields required by consumers.

- [x] Completed baseline in scaffold (kept for context, not new work):
  - UI includes `Load Data` button with loading/success/error status feedback.
  - `/api/internal-data/load` and `/api/internal-data/retrieve` endpoints exist with observable count/status responses.
  - Internal retrieval is integrated into `/api/agents/run` flow.
  - Existing smoke tests cover inline document loading and basic retrieval behavior.
