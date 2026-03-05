# Agent-Search Implementation Plan

Tasks are ordered by **recommended implementation order**. Each section has a **single clear goal**, with **files and purpose** listed in that section. Complete one section at a time; run the listed tests before moving on.

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

---

## Section 7: Vector store – PGVector get and add documents

**Single goal:** Implement getting a PGVector instance (one collection) and adding documents to it. Collection created if it doesn’t exist. Document metadata includes wiki page name/URL. Add logging.

**Details:**
- `get_vector_store(connection, collection_name, embeddings) -> PGVector` (e.g. `use_jsonb=True`).
- `add_documents_to_store(vector_store, documents: list[Document]) -> list[str]` (return ids or similar).
- One collection for the app; metadata on each doc for wiki page and URL.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/vector_store_service.py` | `get_vector_store(...)` returning `PGVector`; `add_documents_to_store(vector_store, documents)` adding docs and returning ids. Logging (docs added, collection created vs existing). |

**How to test:** Backend pytest. TDD. Create vector store (test DB or in-memory if supported); add documents; assert store has docs and metadata; idempotent add to same collection. Isolate with test DB or cleanup.

---

## Section 8: Internal data – orchestrate wiki load → chunk → vector store

**Single goal:** Implement `load_internal_data` (wiki path) and `list_wiki_sources_with_load_state` so that “Load Wiki Source” runs: resolve wiki → LangChain Documents → chunk → add to vector store, and the UI can show which sources are loaded.

**Details:**
- `load_internal_data(payload: InternalDataLoadRequest, db: Session)`: for `source_type="wiki"`, call wiki ingestion (Documents), chunk, get vector store, add_documents_to_store; return `InternalDataLoadResponse` (e.g. documents_loaded, chunks_created).
- `list_wiki_sources_with_load_state(db)`: return wiki source options with an “already_loaded” flag (e.g. from DB or vector store metadata).
- Optionally persist “loaded” state in SQLAlchemy tables if not inferred from vector store alone.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/internal_data_service.py` | `list_wiki_sources_with_load_state(db) -> WikiSourcesResponse`; `load_internal_data(payload, db) -> InternalDataLoadResponse` (wiki: resolve → chunk → vector store). Logging. |

**How to test:** Backend pytest. TDD. Test load_internal_data with wiki payload: assert response counts; assert vector store contains expected chunks/metadata. Test list_wiki_sources_with_load_state: assert sources and already_loaded where applicable.

---

## Section 9: Retriever tool – similarity search with optional filter

**Single goal:** Expose a LangChain `@tool` that runs similarity search on the vector store and optionally filters by wiki page/source. Return a string representation of results. Add logging.

**Details:**
- Tool signature: e.g. `search_database(query: str, limit: int = 10, wiki_source_filter: Optional[str] = None) -> str`.
- Implementation: `vector_store.similarity_search(query, k=limit, filter=...)`; build filter dict when `wiki_source_filter` is set (e.g. metadata.source or custom field).
- Docstring clear for LLM (query, limit, optional wiki filter). Log query, limit, filter, result count.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tools/__init__.py` | Export the retriever tool (or `make_retriever_tool`). |
| `src/backend/tools/retriever_tool.py` | `@tool` or `make_retriever_tool(vector_store)` that calls `similarity_search` with optional filter; return string; logging. |

**How to test:** Backend pytest. TDD. Tool returns string; respects `limit`; when filter provided, results (or count) reflect filter when data supports it. Assert logging.

---

## Section 10: Coordinator agent factory (main + RAG subagent)

**Single goal:** Implement `create_coordinator_agent()` that returns a runnable agent: main agent has no tools and breaks the query into subquestions; one RAG subagent has the retriever tool and runs similarity search. Use LangChain deep agents subagents and RAG patterns.

**Details:**
- Main agent: no direct tools; system prompt = break user query into subquestions and delegate to subagent via `task()` (or equivalent).
- Subagent: retriever tool + system prompt to run similarity search and return retrieved content.
- Factory: `create_coordinator_agent(vector_store, model, ...) -> runnable`. Use `create_deep_agent` and `subagents=[rag_subagent]`. Add logging (which agent ran, tool calls).

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agents/__init__.py` | Export `create_coordinator_agent`. |
| `src/backend/agents/coordinator.py` | `create_coordinator_agent(vector_store, model, ...)` building main + RAG subagent; return runnable. Logging. |

**How to test:** Backend pytest. Factory returns an invocable; invoke with a query and assert subagent tool is used and a final answer is returned (mock vector store/tool to avoid real DB). Assert logging if feasible.

---

## Section 11: Run – backend route and run_runtime_agent service

**Single goal:** When the frontend calls `POST /api/agents/run`, the backend creates the coordinator agent, invokes it with the user query, and returns the last message content. All request/response use Pydantic.

**Details:**
- Route: `POST /api/agents/run` with body `RuntimeAgentRunRequest` (e.g. `query: str`); response `RuntimeAgentRunResponse` (e.g. `output: str`).
- Service: `run_runtime_agent(payload, db, ...)` creates agent via `create_coordinator_agent(...)`, runs `agent.invoke({"messages": [HumanMessage(content=payload.query)]})`, returns `RuntimeAgentRunResponse(output=result["messages"][-1].content)`.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | `run_runtime_agent(payload: RuntimeAgentRunRequest, db: Session, ...) -> RuntimeAgentRunResponse`: create agent, invoke, extract last message content. Logging. |
| `src/backend/routers/agent.py` | Ensure `POST /run` (or `/api/agents/run`) uses `RuntimeAgentRunRequest`/`RuntimeAgentRunResponse` and calls `run_runtime_agent`. |
| `src/backend/schemas/agent.py` | Keep `RuntimeAgentRunRequest`, `RuntimeAgentRunResponse`, `RuntimeAgentInfo`. |

**How to test:** Backend pytest. POST to run endpoint with a query; assert 200 and response has `output` string (can mock agent or use real agent with test vector store).

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
