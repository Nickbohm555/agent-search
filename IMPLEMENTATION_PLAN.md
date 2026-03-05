# Agent-Search Implementation Plan

Tasks are ordered by **recommended implementation order**. Each section has a **single clear goal**, with **files and purpose** listed in that section. Complete one section at a time; run the listed tests before moving on.

---

## Section 12: Run – frontend button and response display

**Single goal:** Run button submits the query to `POST /api/agents/run` and displays the returned answer. Add or adjust frontend tests for Run flow.

**Details:**
- On Run click: POST `{ query }` to `/api/agents/run`; on success, show `response.output` in the UI.
- Handle loading and error states; types aligned with Pydantic (e.g. `RuntimeAgentRunResponse`).

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/App.tsx` | Run button/form calls `runAgent(query)`; display answer and run state (loading/success/error). |
| `src/frontend/src/utils/api.ts` | `runAgent(query)` POST to `/api/agents/run`; validate response shape; types for request/response. |

**How to test:** Frontend tests: e.g. submit Run with a query, assert request to `/api/agents/run` and that response output is displayed. Optional E2E or manual test.

---

## Wipe + PGVector (optional follow-up)

**Single goal:** If PGVector stores data in the same PostgreSQL DB and uses tables that should be cleared on “Wipe Data”, extend `wipe_all_internal_data` (or the code path called by the wipe route) to delete or truncate those tables/collections so wipe is full. Document in the wipe section which tables/collections are cleared.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/common/db/wipe.py` | Optionally clear PGVector collection/tables (e.g. delete langchain collection rows) in addition to InternalDocumentChunk and InternalDocument. |

**How to test:** Backend pytest. After wipe, assert vector store is empty or reset (e.g. no documents in collection).

---

## Dependency summary

- **Backend:** `langchain-core`, `langchain-community` (Wikipedia loader), `langchain-text-splitters` (RecursiveCharacterTextSplitter), `langchain-postgres` (PGVector), embeddings package; deep agents per [LangChain subagents](https://docs.langchain.com/oss/python/deepagents/subagents) (add to pyproject if needed).
- **Database:** PostgreSQL with pgvector; one connection string for SQLAlchemy and PGVector where applicable.
- **Frontend:** No new deps; existing fetch and types.

---

## Test layout (backend)

- **Location:** `src/backend/tests/` or `tests/` at backend root.
- **conftest.py:** Fixtures (db session, vector store mock, sample documents).
- **Per-section tests:** `test_common_db_wipe.py` (Sections 1–2), `test_wiki_ingestion_service.py` (3–4), `test_vector_store_service.py` (6–7), `test_internal_data_service.py` (8), `test_retriever_tool.py` (9), `test_coordinator_agent.py` (10), `test_agent_service.py` / `test_routers_agent.py` (11).
- **Run:** `pytest` (or `uv run pytest`) from backend root.
