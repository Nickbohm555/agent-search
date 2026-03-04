---
Re-start the entire application after each loop if env / DB / other changes were made.
current blocker: ImportError: Could not import wikipedia python package. Please install it with `pip install wikipedia`.


## ⚠️ PRIORITY: Large wiki sources + LangChain loader + dropdown + check-before-load

**This is a top implementation priority.** All wiki loading must satisfy:

1. **LARGE wiki sources only** — Minimum ~1000+ characters per source. Content must be chunked into multiple documents/chunks (no tiny fixture-style snippets). Small demo fixtures are acceptable only for deterministic CI; production/wiki mode must use real, large content.
2. **Curated list (dropdown)** — User selects from a fixed list of options only (no free-form URL/topic). See **Allowed wiki source list** below.
3. **Check before load** — Before allowing a wiki load, the system must indicate whether that source is already vectorized/downloaded (e.g. by `source_ref` or document title). UI/API should prevent or warn on duplicate load and only allow selection from the list.
4. **MUST use LangChain document loader with metadata** — Wiki ingestion MUST use a LangChain document loader (e.g. `WikipediaLoader` from `langchain_community`) that returns Document objects with metadata (e.g. `title`, `source`, `summary`). Metadata must be persisted and exposed in retrieval responses for attribution. No ad-hoc HTTP scraping or fixture-only content for wiki mode in the main path.

**Allowed wiki source list (dropdown options):**

| Option ID / label        | Wikipedia article (query for loader) | Notes                    |
|--------------------------|--------------------------------------|--------------------------|
| `geopolitics`            | Geopolitics                          | Large, conceptual        |
| `strait_of_hormuz`       | Strait of Hormuz                     | Chokepoint, energy       |
| `nato`                   | NATO                                 | Alliance, large          |
| `european_union`         | European Union                       | Large                    |
| `united_nations`         | United Nations                       | Large                    |
| `foreign_policy_us`      | Foreign policy of the United States  | Large                    |
| `middle_east`            | Middle East                          | Region, large            |
| `cold_war`               | Cold War                             | Large                    |
| `international_relations` | International relations            | Large                    |
| `balance_of_power`       | Balance of power (international relations) | Large              |

Backend must expose this list (e.g. `GET /api/internal-data/wiki-sources` or equivalent) so the frontend dropdown is driven by config. Only these options are loadable; reject any other wiki identifier.

---

- [x] P0: Add wiki-source loading path to `/api/internal-data/load` while keeping inline loading intact.
  - Implementation scope:
    - Extend backend load request schema to support a wiki mode plus wiki input (for example URL/topic) without breaking existing inline payloads.
    - Add wiki ingestion service in `src/backend/services/` that resolves one geopolitics wiki page into at least one structured document (`title`, `content`, `source_ref`, `source_type`).
    - Persist wiki attribution fields so downstream retrieval responses can identify wiki origin. **Dropdown: list of only a few options; check if already vectorized/downloaded before allowing load.**
    - **LARGE wiki sources only (1000+ chars); chunk to multiple documents. Use the curated list above.**
    - **MUST use LangChain document loader with metadata** (e.g. `WikipediaLoader`) — Documents with metadata for attribution; no fixture-only path for main wiki load.
  - Remaining work (to align with priority above):
    - Replace or extend fixture-based wiki ingestion with LangChain `WikipediaLoader` (or equivalent) so real, large articles are loaded with metadata.
    - Restrict wiki input to the **allowed wiki source list**; backend returns this list and rejects unknown IDs.
    - Add "already loaded" check: before load, indicate which sources are already in the store; UI shows and optionally blocks duplicate load.
  - Verification requirements (acceptance outcomes):
    - Backend smoke test: wiki-mode load request returns `200` with `status="success"`, `source_type="wiki"`, `documents_loaded >= 1`, `chunks_created >= 1`.
    - Backend smoke test: stored wiki-derived document has non-empty `title` and non-empty `content` suitable for chunking.
    - Backend smoke test: retrieval after wiki load includes at least one result with wiki attribution (`source_type`/`source_ref`).
    - Determinism: ingestion tests use fixtures/mocks (no live wiki network dependency in CI).
  - Completed in this loop:
    - Added `source_type="wiki"` support plus request validation in `src/backend/schemas/internal_data.py` while preserving inline compatibility.
    - Added deterministic wiki ingestion fixture service at `src/backend/services/wiki_ingestion_service.py` for geopolitics topic/url (`Strait of Hormuz`) with no live network dependency.
    - Updated internal load service to ingest wiki-derived documents and persist attribution (`source_type`, `source_ref`) into existing document/chunk tables.
    - Added smoke coverage in `src/backend/tests/api/test_internal_data_loading.py`:
      - `test_wiki_data_load_returns_observable_counts`
      - `test_wiki_retrieval_includes_wiki_attribution_and_content`

- [x] P0: Migrate chunk embedding storage from `embedding_json` to native pgvector column.
  - Implementation scope:
    - Add Alembic migration(s) to enable pgvector extension and add a vector column on `internal_document_chunks` with embedding dimension aligned to backend embedding output.
    - Update SQLAlchemy model and load pipeline writes to persist embeddings into the vector column as the primary retrieval store.
    - Preserve observable load API contract (`status`, `source_type`, `documents_loaded`, `chunks_created`).
  - Verification requirements (acceptance outcomes):
    - Migration smoke test (Postgres-backed): extension exists and chunk table exposes vector embedding column after `alembic upgrade head`.
    - Backend smoke test: successful load writes non-null vectors for created chunks.
    - Contract test: load response shape/fields remain unchanged for current consumers.
  - Completed in this loop:
    - Added migration `src/backend/alembic/versions/0003_pgvector_chunk_embeddings.py` to create pgvector extension, add `internal_document_chunks.embedding` (`vector(16)`), backfill from `embedding_json`, and remove legacy JSON storage.
    - Updated ORM model `src/backend/models.py` so `InternalDocumentChunk` now persists `embedding` as native pgvector.
    - Updated load/retrieve service `src/backend/services/internal_data_service.py` to write/read vector embeddings while preserving existing API response contracts.
    - Added smoke coverage:
      - `src/backend/tests/api/test_pgvector_storage.py::test_pgvector_extension_and_embedding_column_exist_on_postgres`
      - `src/backend/tests/api/test_internal_data_loading.py::test_internal_data_load_persists_non_null_chunk_vectors`
      - Strengthened contract assertion in `test_internal_data_load_returns_observable_counts` to enforce stable response keys.

- [x] P0: Switch internal retrieval to database-side pgvector similarity ranking.
  - Implementation scope:
    - Replace Python in-memory cosine ranking with SQL similarity ordering/limit against pgvector (`top-k` in DB).
    - Keep retrieval response schema stable (`content`, `score`, `document_title`, `source_ref`, `source_type`, ids).
    - Ensure query embeddings use the same model/dimension as stored vectors.
  - Verification requirements (acceptance outcomes):
    - Backend smoke test: `/api/internal-data/retrieve` returns ranked `top-k` results with existing response fields unchanged.
    - Relevance regression smoke test: with seeded relevant and unrelated docs, relevant chunk ranks at or above unrelated chunk for matching query.
    - Agent-path smoke test: `/api/agents/run` internal retrieval path returns internal results from loaded store and preserves metadata.
  - Completed in this loop:
    - Updated `src/backend/services/internal_data_service.py::retrieve_internal_data` to use database-side `cosine_distance` ordering (`ORDER BY` + `LIMIT`) for Postgres pgvector backends.
    - Preserved retrieval response contract while normalizing DB distance into `score` (`1 - distance`) and keeping source/document metadata unchanged.
    - Added deterministic fallback to in-process cosine ranking for non-Postgres test backends so scaffold tests stay stable without pgvector.
    - Added/updated smoke tests:
      - `src/backend/tests/api/test_internal_data_loading.py::test_internal_retrieval_returns_loaded_content` now asserts retrieval result field shape stability.
      - `src/backend/tests/api/test_internal_data_loading.py::test_internal_retrieval_ranks_relevant_chunk_above_unrelated` validates relevance ordering.
      - `src/backend/tests/api/test_per_subquery_retrieval.py::test_agent_run_executes_internal_retrieval_from_loaded_store` now asserts metadata preservation (`document_title`, `source_ref`).

- [x] P1: Update UI `Load Data` flow to support wiki-triggered loads and clear status readout.
  - Implementation scope:
    - Add a minimal wiki source control in the existing load panel (reuse shared `src/frontend/src/lib/*` patterns/components where practical).
    - Extend frontend API request typing/client payload to send wiki load requests while preserving inline compatibility.
    - Keep existing loading/success/error UX behavior and readable count feedback.
  - Verification requirements (acceptance outcomes):
    - Frontend interaction test: wiki mode + click `Load Data` sends `/api/internal-data/load` with wiki payload.
    - Frontend interaction test: successful wiki load renders clear success message with counts.
    - Frontend interaction test: failed wiki load renders clear error state in load status region.
  - Completed in this loop:
    - Added wiki source controls to `src/frontend/src/App.tsx` (`Load Source` select + `Wiki Topic` input) while keeping inline load behavior as default.
    - Added `buildLoadPayload` in `App` so `handleLoad` emits deterministic inline or wiki payloads through `loadInternalData`.
    - Extended frontend API types in `src/frontend/src/utils/api.ts` with a discriminated `InternalDataLoadRequest` union supporting both inline documents and wiki payloads.
    - Updated load success readout in `src/frontend/src/lib/utils/messages.ts` to provide a wiki-specific success message while preserving inline wording.
    - Added frontend interaction/API coverage:
      - `src/frontend/src/App.test.tsx::sends wiki payload and shows wiki success readout when wiki load is selected`
      - `src/frontend/src/App.test.tsx::shows clear load error state for wiki load failures`
      - `src/frontend/src/utils/api.test.ts::sends wiki load payload to the load endpoint`
  - Verification run results:
    - `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
    - `docker compose exec backend uv run pytest` -> `51 passed`
    - `docker compose exec frontend npm run test` -> `26 passed`
    - `docker compose exec frontend npm run typecheck` -> pass

- [x] P1: Add one scoped deterministic smoke path for “click load data -> wiki vectorized in pgvector -> retrievable”.
  - Implementation scope:
    - Add an end-to-end smoke scenario covering user-triggered load through retrievable wiki-backed internal results.
    - Use deterministic fixture content/embeddings and avoid hidden network calls.
  - Verification requirements (acceptance outcomes):
    - User-triggered load completes with observable success status and counts.
    - Retrieval after load returns wiki-derived internal content.
    - Returned retrieval metadata includes wiki attribution required by consumers.
  - Completed in this loop:
    - Added `src/backend/tests/api/test_pgvector_storage.py::test_wiki_load_vectorize_and_retrieve_path_on_postgres` as a deterministic Postgres-backed smoke path that:
      - Calls `POST /api/internal-data/load` with `source_type="wiki"` (user-triggered API surface) and asserts observable success/count fields.
      - Verifies wiki-loaded chunks were vectorized (`internal_document_chunks.embedding IS NOT NULL`) for the loaded wiki `source_ref`.
      - Calls `POST /api/internal-data/retrieve` and asserts returned results include wiki attribution (`source_type="wiki"`, matching `source_ref`).
      - Cleans up inserted smoke documents by `source_ref` to keep repeated runs stable.

- [x] **P0 (PRIORITY): Large wiki + LangChain document loader with metadata + dropdown + check-before-load**
  - Implementation scope (see priority box at top of this file):
    - Use **LangChain document loader** (e.g. `WikipediaLoader`) for wiki ingestion; Documents must carry **metadata** (title, source, etc.) and be persisted for attribution.
    - **LARGE sources only** (1000+ chars); chunk to multiple documents. No small fixtures in the main wiki load path.
    - **Curated list only**: backend exposes allowed wiki source list (e.g. `GET /api/internal-data/wiki-sources`); frontend **dropdown** shows only these options; reject unknown IDs.
    - **Check before load**: indicate which sources are already vectorized/downloaded; UI prevents or warns on duplicate load.
  - Verification requirements (acceptance outcomes):
    - Wiki load uses LangChain loader and returns Documents with metadata; stored chunks have correct document/source attribution.
    - Loaded wiki content is large enough to produce multiple chunks (e.g. `chunks_created >= 2` for a single wiki source).
    - Dropdown is driven by backend list; only allowed IDs accepted; load returns 4xx or clear error for unknown wiki ID.
    - API or UI exposes "already loaded" state for each wiki source so user can avoid re-loading.
  - Completed in this loop:
    - Replaced fixture-only main-path wiki ingestion with LangChain loader wiring in `src/backend/services/wiki_ingestion_service.py` via `WikipediaLoader` (`langchain_community`) and conversion of loader `Document` output + metadata into persisted internal documents.
    - Added curated backend wiki-source registry (`geopolitics`, `strait_of_hormuz`, `nato`, `european_union`, `united_nations`, `foreign_policy_us`, `middle_east`, `cold_war`, `international_relations`, `balance_of_power`) and strict source-ID validation for wiki loads.
    - Enforced large-content wiki ingestion threshold (`>=1000` chars aggregate) before persistence so wiki loads produce multi-chunk content.
    - Added duplicate-load prevention in `src/backend/services/internal_data_service.py` (reject load when selected wiki source is already vectorized).
    - Added `GET /api/internal-data/wiki-sources` in `src/backend/routers/internal_data.py` returning curated options with `already_loaded` state from persisted wiki docs.
    - Updated frontend load UX in `src/frontend/src/App.tsx` to fetch wiki source list from backend, drive wiki selection from dropdown only, and block duplicate wiki loads with a clear status readout.
    - Updated frontend API client in `src/frontend/src/utils/api.ts` with `listWikiSources()` plus schema validation for wiki-source responses.
    - Added deterministic smoke and interaction coverage:
      - Backend: `src/backend/tests/api/test_internal_data_loading.py`
        - `test_wiki_sources_endpoint_reports_already_loaded_state`
        - `test_wiki_load_rejects_unknown_source_id`
        - `test_wiki_load_rejects_duplicate_source`
        - Updated wiki load/retrieval smoke tests to use curated `source_id` and mocked LangChain loader docs.
      - Backend Postgres smoke: updated `src/backend/tests/api/test_pgvector_storage.py::test_wiki_load_vectorize_and_retrieve_path_on_postgres` to use curated wiki source IDs with deterministic mocked wiki loader content.
      - Frontend: `src/frontend/src/App.test.tsx` and `src/frontend/src/utils/api.test.ts` updated for dropdown/list contract and duplicate-load behavior.

- [x] Completed baseline relevant to this scope (confirmed in current codebase):
  - `/api/internal-data/load` and `/api/internal-data/retrieve` endpoints exist and return observable counts/results.
  - Frontend has clickable `Load Data` control with deterministic loading/success/error status messaging.
  - Internal retrieval is wired into `/api/agents/run` internal tool path.
  - Current gaps: none for this P0 wiki scope.

- Verification run results:
  - `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
  - `docker compose exec backend uv run pytest` -> `56 passed`
  - `docker compose exec frontend npm run test` -> `28 passed`
  - `docker compose exec frontend npm run typecheck` -> pass

- [x] P1: Honor reduced-motion preference in UI state while preserving readout feedback.
  - Implementation scope:
    - Add deterministic reduced-motion state detection in frontend app startup/render path.
    - Apply a dedicated reduced-motion class at the app shell so decorative transitions/hover motion can be disabled without hiding status text.
    - Keep load/run status readouts unchanged so essential progress feedback remains visible.
  - Verification requirements (acceptance outcomes):
    - Frontend test: app marks reduced-motion mode when `matchMedia("(prefers-reduced-motion: reduce)")` is true.
    - Frontend test: app remains in default motion mode when reduced-motion preference is false.
    - Existing load/run tests remain green to confirm status/answer readouts are still visible with motion changes.
  - Completed in this loop:
    - Added `src/frontend/src/utils/motion.ts::usePrefersReducedMotion` hook to centralize reduced-motion preference detection from `window.matchMedia`.
    - Updated `src/frontend/src/App.tsx` to apply `reduced-motion` class and `data-reduced-motion` attribute on the root `<main>` shell.
    - Updated `src/frontend/src/styles.css` to support both app-driven `.reduced-motion` and OS-level `@media (prefers-reduced-motion: reduce)` fallbacks that disable non-essential transitions/hover motion.
    - Added frontend interaction coverage in `src/frontend/src/App.test.tsx`:
      - `marks app reduced-motion state when system preference requests less motion`
      - `keeps default motion mode when reduced-motion preference is not requested`
  - Verification run results:
    - `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
    - `docker compose exec backend uv run pytest` -> `56 passed`
    - `docker compose exec frontend npm run test` -> `30 passed`
    - `docker compose exec frontend npm run typecheck` -> pass

- [x] P1: Ensure keyboard-only operability for both load and run flows with visible focus styling.
  - Implementation scope:
    - Make the load/vectorize controls submit through a semantic form path so keyboard submission behaves the same as pointer activation.
    - Keep the existing load behavior and duplicate-guard checks intact while routing keyboard submits through shared load logic.
    - Strengthen interactive focus styling so keyboard and programmatic focus remain visibly highlighted in the cyberpunk theme.
  - Verification requirements (acceptance outcomes):
    - Frontend interaction test: load flow can be triggered through form submit (keyboard path) and renders success readout.
    - Frontend interaction test: run flow remains keyboard-submittable and continues to render streamed/final readouts.
    - Styling: interactive controls retain visible neon focus indicators via shared focus selectors.
  - Completed in this loop:
    - Added `handleLoadSubmit` in `src/frontend/src/App.tsx` and wired `Load / Vectorize` controls as a form submit path (`type="submit"`), preserving existing `handleLoad` side effects and guards.
    - Updated focus styling in `src/frontend/src/styles.css` from `:focus-visible`-only to shared `:focus` selectors for `textarea`, `input`, `select`, and `button` to keep focus indicators visible for keyboard and programmatic focus.
    - Added frontend interaction coverage in `src/frontend/src/App.test.tsx`:
      - `supports keyboard form submission for load flow`
  - Verification run results:
    - `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
    - `docker compose exec backend uv run pytest` -> `56 passed`
    - `docker compose exec frontend npm run test` -> `31 passed`
    - `docker compose exec frontend npm run typecheck` -> pass

- [x] P0: Trace failed `/api/agents/run` executions so errors are not silently untraced.
  - Implementation scope:
    - Ensure Langfuse span lifecycle wraps runtime execution, not just successful post-processing.
    - Record deterministic error trace payload fields (`query`, `agent_name`, `error_type`, `persistence_context`) before re-raising.
    - Preserve success-path trace payload contract and runtime response shape.
  - Verification requirements (acceptance outcomes):
    - Backend smoke test: forced runtime failure still creates one `agent.run` span with error payload metadata.
    - Existing tracing smoke tests for success/disabled/stream/MCP remain green.
  - Completed in this loop:
    - Updated `src/backend/services/agent_service.py::run_runtime_agent` so tracing starts before `graph_agent.run(...)`; on exceptions it writes error trace metadata and re-raises.
    - Preserved the existing success trace update payload to avoid downstream contract regressions.
    - Added smoke coverage in `src/backend/tests/api/test_agent_run_tracing.py::test_agent_run_failure_still_records_error_trace_when_enabled`.
  - Verification run results:
    - `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
    - `docker compose exec backend uv run pytest tests/api/test_agent_run_tracing.py -q` -> `7 passed`
    - `docker compose exec backend uv run pytest` -> `57 passed`
    - `docker compose exec frontend npm run test` -> `31 passed`
    - `docker compose exec frontend npm run typecheck` -> pass

- [x] P1: Stream per-subquery retrieval/validation events and surface them in final progress readouts.
  - Implementation scope:
    - Extend `/api/agents/run/stream` fallback emission to include ordered `retrieval_result` and `validation_result` events per sub-query before `completed`.
    - Keep stream completion payload contract stable (`agent_name`, `output`, `thread_id`, `checkpoint_id`, `sub_queries`, `tool_assignments`).
    - Hydrate frontend final run details from streamed events so retrieval/validation sections show actual execution outcomes rather than empty placeholders.
  - Verification requirements (acceptance outcomes):
    - Backend smoke test: stream includes retrieval/validation events in order after tool assignments and before completion.
    - Backend parity smoke test: streamed retrieval/validation event payloads match `/api/agents/run` response arrays for the same request.
    - Frontend interaction test: when stream includes retrieval/validation events, progress readout renders retrieval counts and validation statuses after completion.
  - Completed in this loop:
    - Updated `src/backend/services/agent_service.py::stream_runtime_agent` to emit `retrieval_result` and `validation_result` events for each paired retrieval/validation result before `completed`.
    - Updated backend smoke tests:
      - `src/backend/tests/api/test_streaming_agent_heartbeat.py`
      - `src/backend/tests/api/test_streaming_compile_invoke_dummy.py`
      - `src/backend/tests/api/test_sync_stream_contract_parity.py::test_runtime_agent_stream_retrieval_and_validation_events_match_sync_payload`
    - Updated frontend run assembly in `src/frontend/src/App.tsx` to derive `retrieval_results`, `validation_results`, and `web_tool_runs` from streamed events.
    - Updated frontend readout component `src/frontend/src/lib/components/ProgressHistory.tsx` to render retrieval results alongside validation timeline sections.
    - Added frontend coverage:
      - `src/frontend/src/App.test.tsx::renders retrieval and validation readouts from streamed execution events on completion`
      - `src/frontend/src/utils/stream.test.ts` updated ordered-event parser coverage for retrieval/validation events.
  - Verification run results:
    - `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
    - `docker compose exec backend uv run pytest` -> `58 passed`
    - `docker compose exec frontend npm run test` -> `32 passed`
    - `docker compose exec frontend npm run typecheck` -> pass
