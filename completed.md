## Section 1: Coordinator flow tracking via write_todos and virtual file system

**Single goal:** The coordinator agent uses the deep-agents (LangGraph) `write_todos` planning tool and the **deep-agents virtual file system** to keep track of the pipeline flow so it does not lose context across steps.

### Implemented
- Updated `src/backend/agents/coordinator.py` to explicitly configure deep-agents backend as `StateBackend` (virtual filesystem backend) when creating the coordinator agent.
- Strengthened coordinator system prompt to require:
  - `write_todos` at run start and throughout stage transitions.
  - `read_file`/`write_file` usage on `/runtime/coordinator_flow.md` for persisted flow tracking across steps.
  - Stage-aligned planning for the full initial + refinement pipeline.
- Added coordinator creation logging to include backend and flow tracking file path for visibility.
- Added/updated tests in `src/backend/tests/agents/test_coordinator_agent.py`:
  - Verifies coordinator prompt contains mandatory `write_todos` + virtual filesystem instructions.
  - Verifies backend passed to deep-agents is `StateBackend`.
  - Verifies backend override wiring works.

### Validation and logs
- Fresh restart (full rebuild):
  - `docker compose down -v --rmi all`
  - `docker compose build`
  - `docker compose up -d`
- Backend unit tests:
  - `docker compose exec backend sh -lc 'uv run pytest tests/agents/test_coordinator_agent.py tests/services/test_agent_service.py'`
  - Result: `5 passed`
- API smoke selection command:
  - `docker compose exec backend sh -lc 'uv run pytest tests/api -m smoke'`
  - Result: `2 deselected` (no smoke-selected tests)
- Integration run:
  - `POST /api/agents/run` with `{"query":"What is the Strait of Hormuz?"}`
  - Result: `HTTP 200`
  - Response included `main_question`, `sub_qa`, and `output`.
- Backend logs confirmed required runtime behavior:
  - `Tool called: name=write_todos ...`
  - `Tool called: name=write_file input={'file_path': '/runtime/coordinator_flow.md', ...}`
  - `Tool response ... Command(update={'files': {'/runtime/coordinator_flow.md': ...}})`
  - Additional flow updates and staged todo status transitions were present.
- Container log sweep performed (`backend`, `frontend`, `db`) and `docker compose ps` checked all services up/healthy.

### Noted runtime detail
- `GET /api/health` currently returns `404 Not Found` in this codebase state.

## Section 2: Initial search for decomposition context

**Single goal:** Run one retrieval for the user question and pass top-k results as context into decomposition.

**Details:**
- One retrieval (same vector store/retriever as sub-question search) using the raw user question, before decomposition.
- Return bounded top-k docs/snippets; pass as structured context (e.g. list of doc IDs, snippets, or metadata) into decomposition. Do not change decomposition logic; only add the search step and wire its output.
- k and retriever config (e.g. score threshold) configurable (env or settings).

**Tech:** Existing retriever/vector_store_service. No new packages. No Docker change unless new env vars.

**Files**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Invoke initial search before coordinator/decomposition; pass context into decomposition. |
| `src/backend/services/vector_store_service.py` (or equivalent) | Use existing similarity search; optional thin wrapper for context-only search with configurable k. |
| `src/backend/schemas/agent.py` (optional) | Optional schema for “initial search context” if not inlined in run request/state. |

**How to test:** Unit: mock retriever → assert returned context is passed to decomposition. Integration: full agent request → decomposition receives non-empty context when store has relevant docs.

### Implemented
- Added `search_documents_for_context(...)` in `src/backend/services/vector_store_service.py` to run one pre-decomposition retrieval with configurable `k` and optional `score_threshold`.
- Added `build_initial_search_context(...)` in `src/backend/services/vector_store_service.py` to shape context into bounded structured items (`rank`, `document_id`, `title`, `source`, `snippet`).
- Updated `src/backend/services/agent_service.py` to:
  - Run one initial context retrieval before coordinator invocation.
  - Build structured context and inject it into the coordinator’s first `HumanMessage` as decomposition context.
  - Add new runtime logs for visibility of retrieval mode, result count, and context build metadata.
- Added unit coverage in:
  - `src/backend/tests/services/test_agent_service.py` to assert context retrieval/build is called and coordinator receives context in input message.
  - `src/backend/tests/services/test_vector_store_service.py` to validate new context-search wrapper behavior and context shape formatting.

### Validation and logs
- Fresh environment reset before implementation:
  - `docker compose down -v --rmi all`
  - `docker compose build`
  - `docker compose up -d`
- Backend restarted after code changes:
  - `docker compose restart backend`
- Unit tests:
  - `docker compose exec backend sh -lc 'uv pip install pytest && uv run pytest tests/services/test_agent_service.py tests/services/test_vector_store_service.py'`
  - Result: `7 passed`
- Integration flow:
  - `POST /api/internal-data/wipe` -> success
  - `POST /api/internal-data/load` with `{"source_type":"wiki","wiki":{"source_id":"nato"}}` -> `documents_loaded=1`, `chunks_created=14`
  - `POST /api/agents/run` with `{"query":"What changed in NATO policy?"}` -> `HTTP 200`
- Backend logs confirmed the Section 2 behavior:
  - `Context search complete query='What changed in NATO policy?' k=5 score_threshold=None results=5 mode=similarity_search`
  - `Initial decomposition context built query=What changed in NATO policy? docs=5 k=5 score_threshold=None`
  - `INFO ... "POST /api/agents/run HTTP/1.1" 200 OK`
- Container log sweep completed after implementation:
  - `docker compose logs --tail=60 backend`
  - `docker compose logs --tail=60 frontend`
  - `docker compose logs --tail=60 db`
  - `docker compose ps` (all services up; db healthy)

**Test results:** Complete.
