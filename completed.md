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

**Test results (Docker-based):**
- Added and ran `docker compose exec backend uv run pytest tests/tools/test_retriever_tool.py` (2 passed): verified tool returns a formatted string, enforces `limit`, applies optional `wiki_source_filter` via similarity search `filter`, and emits caplog-asserted query/limit/filter/result_count logging.
- Ran `docker compose exec backend uv run pytest` (14 passed): full backend suite green, including new retriever-tool tests plus existing API/DB/wiki/vector/embedding/internal-data tests.
- Ran `docker compose exec frontend npm run test` (passed, 2 tests).
- Ran `docker compose exec frontend npm run typecheck` (passed).
- Ran health check with `curl -sS -i http://localhost:8000/api/health` (failed: `curl: (56) Recv failure: Connection reset by peer`). Backend logs show pre-existing startup import error: `ImportError: cannot import name 'run_runtime_agent' from 'services.agent_service'`; unrelated to Section 9 changes.

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

**Test results (Docker-based):**
- Added and ran `docker compose exec backend uv run pytest tests/services/test_vector_store_service.py` (2 passed): verified `get_vector_store` initializes the collection and logs `state=created` then `state=existing` on repeated calls for the same collection; verified `add_documents_to_store` returns IDs, stores documents, preserves searchable content, and normalizes metadata with `wiki_page`/`wiki_url`.
- Ran `docker compose exec backend uv run pytest` (10 passed): full backend suite green, including new vector store tests and existing API/DB/wiki/embedding tests.
- Ran `docker compose exec frontend npm run test` (passed, 2 tests).
- Ran `docker compose exec frontend npm run typecheck` (passed).
- Ran health check with `curl -sS -i http://localhost:8000/api/health` (failed: `curl: (56) Recv failure: Connection reset by peer`). Backend logs show pre-existing startup import error: `ImportError: cannot import name 'run_runtime_agent' from 'services.agent_service'`; unrelated to Section 7 changes.

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

**Test results (Docker-based):**
- Added and ran `docker compose exec backend uv run pytest tests/services/test_internal_data_service.py` (2 passed): validated `load_internal_data` wiki orchestration resolves/chunks/adds to vector store and returns expected `documents_loaded`/`chunks_created`; validated `list_wiki_sources_with_load_state` marks persisted wiki sources as `already_loaded`.
- Ran `docker compose exec backend uv run pytest` (12 passed): full backend suite green, including new internal-data service tests plus existing API/DB/wiki/vector/embedding tests.
- Ran `docker compose exec frontend npm run test` (passed, 2 tests).
- Ran `docker compose exec frontend npm run typecheck` (passed).
- Ran health check with `curl -sS -i http://localhost:8000/api/health` (failed: `curl: (56) Recv failure: Connection reset by peer`). Backend logs show pre-existing startup import error: `ImportError: cannot import name 'run_runtime_agent' from 'services.agent_service'`; unrelated to Section 8 changes.

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
| `src/backend/tests/agents/test_coordinator_agent.py` | Verifies factory builds an invocable coordinator, configures subagent/tool wiring, invokes retriever tool, and emits logs. |

**How to test:** Backend pytest. Factory returns an invocable; invoke with a query and assert subagent tool is used and a final answer is returned (mock vector store/tool to avoid real DB). Assert logging if feasible.

**Test results (Docker-based):**
- Added and ran `docker compose exec backend uv run pytest tests/agents/test_coordinator_agent.py` (1 passed): verified `create_coordinator_agent` returns an invocable runnable, configures `create_deep_agent` with `subagents=[rag_retriever]` and retriever tool wiring, and returns a final answer after retrieval.
- Ran `docker compose exec backend uv run pytest` (15 passed): full backend suite green, including new coordinator-agent test plus existing API/DB/wiki/vector/embedding/retriever/internal-data tests.
- Ran `docker compose exec frontend npm run test` (passed, 2 tests).
- Ran `docker compose exec frontend npm run typecheck` (passed).
- Ran health check with `curl -sS -i http://localhost:8000/api/health` (failed: `curl: (56) Recv failure: Connection reset by peer`). Backend logs confirm pre-existing startup/import error: `ImportError: cannot import name 'run_runtime_agent' from 'services.agent_service'`; unrelated to Section 10 changes.

---

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

**Test results (Docker-based):**
- Added and ran `docker compose exec backend uv run pytest tests/services/test_agent_service.py tests/api/test_agent_run.py` via the full backend suite command `docker compose exec backend uv run pytest` (17 passed total): verified `run_runtime_agent` creates vector store + coordinator agent, invokes with `HumanMessage(payload.query)`, extracts the final message as `RuntimeAgentRunResponse.output`, and logs start/complete events; verified `POST /api/agents/run` returns 200 with `{ "output": string }`.
- Ran `docker compose exec frontend npm run test` (passed, 2 tests).
- Ran `docker compose exec frontend npm run typecheck` (passed).
- Ran health check with `curl -sS -i http://localhost:8000/api/health` (returned `404 Not Found`; health endpoint is not currently implemented in the running backend).
