# Agent-Search Implementation Plan

Tasks are ordered by **recommended implementation order**. Each section has a **single clear goal**, with **files and purpose** listed in that section. Complete one section at a time; run the listed tests before moving on.

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
