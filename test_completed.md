# Agent-Search Completed Test Sections

## Test Section 1: Stack and health – services up and reachable

**Single goal:** Confirm Docker stack is up, backend health returns 200, and frontend is reachable so all later tests can run.

**Details:**
- All services (`backend`, `frontend`, `db`) must be running; backend must respond at `/api/health`; frontend must be loadable at `http://localhost:5173`.
- No agent run or data load in this section.

**Tech stack and dependencies**
- Docker Compose; curl (or browser) for HTTP checks.

**Files and purpose**

| File | Purpose |
|------|--------|
| (none) | N/A – infrastructure check only. |

**How to test:**
1. Start stack: `docker compose up -d` (from repo root).
2. Wait for readiness: `docker compose ps` → all services `Up`; `db` healthy if shown.
3. Backend health: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health` → `200`; `curl -s http://localhost:8000/api/health` → body contains `"status":"ok"`.
4. Frontend: open `http://localhost:5173` in browser (or use cursor-ide-browser: `browser_navigate` to `http://localhost:5173`, then `browser_snapshot`) → page loads, no 5xx or connection refused.
5. Optional: `docker compose logs --tail=20 backend` → no startup tracebacks or fatal errors.

**Test results:**
- Fresh reset/build/start executed:
  - `docker compose down -v --rmi all`
  - `docker compose build`
  - `docker compose up -d`
- Running state (`docker compose ps`) showed required services up:
  - `agent-search-backend ... Up ... 0.0.0.0:8000->8000/tcp`
  - `agent-search-db ... Up (healthy) ... 0.0.0.0:5432->5432/tcp`
  - `agent-search-frontend ... Up ... 0.0.0.0:5173->5173/tcp`
- Backend health checks:
  - `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health` => `200`
  - `curl -s http://localhost:8000/api/health` => `{"status":"ok"}`
- Frontend reachability:
  - `curl -s -I http://localhost:5173 | head -n 1` => `HTTP/1.1 200 OK`
  - `curl -s http://localhost:5173 | head -n 5` returned Vite React HTML shell (`<!doctype html> ...`)
- Useful startup logs:
  - Backend (`docker compose logs --tail=40 backend`) included Alembic upgrade and successful startup:
    - `Running upgrade  -> 001_internal ...`
    - `Application startup complete.`
    - `GET /api/health ... 200 OK`
  - Frontend (`docker compose logs --tail=20 frontend`) included:
    - `VITE v5.4.21 ready`
    - `Local: http://localhost:5173/`

## Test Section 2: Coordinator flow tracking (Section 1) – write_todos and virtual file system

**Single goal:** One full agent run returns 200 and backend logs show coordinator using `write_todos` and the virtual file system (`/runtime/coordinator_flow.md`).

**Details:**
- Run one query (e.g. "What is the Strait of Hormuz?"); do not require prior data load.
- Assert in backend logs: at least one `Tool called: name=write_todos` and at least one `write_file` or tool response involving `coordinator_flow.md`.

**Tech stack and dependencies**
- Docker backend; `docker compose logs backend`.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agents/coordinator.py` | Coordinator that uses write_todos and virtual filesystem. |

**How to test:**
1. Ensure stack is up (Test Section 1).
2. Run: `POST /api/agents/run` with `{"query":"What is the Strait of Hormuz?"}` → expect HTTP 200 and response with `main_question`, `sub_qa`, and `output`.
3. Inspect backend logs: `docker compose logs --tail=300 backend` (or `-f backend` during run). Require:
   - At least one line containing `Tool called: name=write_todos` (or equivalent from deep-agents).
   - At least one line containing `write_file` and `coordinator_flow.md` (or `Tool response` with `files` and `coordinator_flow.md`).
4. If no such lines, restart backend and rerun: `docker compose restart backend`, then repeat step 2 and 3.

**Test results:** (Add when section is complete.)
- curl/response and log grep outcomes.

---

**Test results:**
- Fresh rebuild/start context used for this section:
  - `docker compose down -v --rmi all`
  - `docker compose build`
  - `docker compose up -d`
- Agent run command and response:
  - `curl -sS --max-time 180 -o /tmp/section2_response.json -w "%{http_code}" -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"Find Hormuz risks"}'`
  - `CURL_EXIT:0`, `HTTP_CODE:200`
  - Response body included required fields: `main_question`, `sub_qa`, `output`.
- Required backend log assertions:
  - `Tool called: name=write_todos` found (multiple matches).
  - `Tool called: name=write_file ... /runtime/coordinator_flow.md` found.
  - `Tool response ... '/runtime/coordinator_flow.md'` found.
  - `POST /api/agents/run HTTP/1.1" 200 OK` found.
- Useful service logs viewed:
  - Backend (`docker compose logs --tail=25 backend`) showed full pipeline completion and `Runtime agent run complete`.
  - Frontend (`docker compose logs --tail=25 frontend`) showed Vite dev server ready at `http://localhost:5173/`.
  - DB (`docker compose logs --tail=25 db`) showed PostgreSQL ready to accept connections.

## Test Section 3: Initial search for decomposition context (Section 2)

**Single goal:** After loading NATO wiki data, one agent run produces backend logs showing initial context search and decomposition context built with non-zero docs.

**Details:**
- Wipe internal data, load NATO wiki, run one query. Logs must show context search completion and "Initial decomposition context built" with `docs=5` (or similar) and `context_items` ≥ 1.

**Tech stack and dependencies**
- Docker backend; vector store and internal-data API.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/vector_store_service.py` | Context search and context building. |
| `src/backend/services/agent_service.py` | Invokes context search and passes context to decomposition. |

**How to test:**
1. Wipe: `POST /api/internal-data/wipe` → 200.
2. Load: `POST /api/internal-data/load` with `{"source_type":"wiki","wiki":{"source_id":"nato"}}` → 200; body shows `documents_loaded=1`, `chunks_created=14` (or similar).
3. Run: `POST /api/agents/run` with `{"query":"What changed in NATO policy?"}` → 200.
4. Backend logs: `docker compose logs --tail=200 backend`. Require:
   - A line matching `Context search complete` with the query and `results=` (e.g. `results=5`).
   - A line matching `Initial decomposition context built` with `docs=` and `context_items=` (e.g. `docs=5`, `context_items=5`).

**Test results:**
- Fresh build/run context used for this section:
  - `docker compose down -v --rmi all`
  - `docker compose build`
  - `docker compose up -d`
- Wipe command/result:
  - `POST /api/internal-data/wipe` => `HTTP 200`
  - Body: `{"status":"success","message":"All internal documents and chunks removed."}`
- Load command/result:
  - `POST /api/internal-data/load` with NATO wiki payload => `HTTP 200`
  - Body: `{"status":"success","source_type":"wiki","documents_loaded":1,"chunks_created":14}`
- Agent run command/result:
  - `POST /api/agents/run` with `{"query":"What changed in NATO policy?"}` => `HTTP 200`
  - Response body included `main_question`, `sub_qa`, and `output`.
- Backend log assertions (verified from full backend logs due long run output):
  - `Context search complete query='What changed in NATO policy?' k=5 score_threshold=None results=5 mode=similarity_search`
  - `Initial decomposition context built query=What changed in NATO policy? docs=5 k=5 score_threshold=None`
  - `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- Useful service logs viewed for this iteration:
  - `docker compose logs --tail=200 db`
  - `docker compose logs --tail=200 backend`
  - `docker compose logs --tail=200 frontend`

## Test Section 4: Context-aware decomposition (Section 3)

**Single goal:** Same run as Section 3 produces logs showing coordinator decomposition input prepared with context, and API response contains non-empty `sub_qa` aligned with the query.

**Details:**
- Reuse data and run from Test Section 3 (or repeat wipe/load/run). Assert "Coordinator decomposition input prepared" with `context_items=5` (or > 0) and response `sub_qa` length ≥ 1 with sub-questions ending in "?".

**Tech stack and dependencies**
- Same as Test Section 3.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agents/coordinator.py` | Context-aware decomposition instructions. |
| `src/backend/services/agent_service.py` | Builds decomposition input with context. |

**How to test:**
1. If not already done: wipe, load NATO wiki, run with "What changed in NATO policy?" (see Test Section 3).
2. Backend logs: require a line like `Coordinator decomposition input prepared ... context_items=5` (or positive `context_items`).
3. From the same run’s response: `sub_qa` is present and non-empty; each `sub_question` is a string ending with `?`.

**Test results:**
- Fresh rebuild/start completed before this section:
  - `docker compose down -v --rmi all`
  - `docker compose build`
  - `docker compose up -d`
- Logs viewed for all built services:
  - `docker compose logs --tail=60 db` showed PostgreSQL init + `database system is ready to accept connections`.
  - `docker compose logs --tail=60 backend` showed Alembic upgrade + Uvicorn startup.
  - `docker compose logs --tail=60 frontend` showed Vite ready on `http://localhost:5173/`.
- Section run commands/results:
  - `POST /api/internal-data/wipe` => `{"status":"success","message":"All internal documents and chunks removed."}`
  - `POST /api/internal-data/load` (wiki nato) => `{"status":"success","source_type":"wiki","documents_loaded":1,"chunks_created":14}`
  - `POST /api/agents/run` with `{"query":"What changed in NATO policy?"}` => HTTP 200 and response with non-empty `sub_qa`.
- Initial failure and fix:
  - First run had some `sub_qa.sub_question` values without trailing `?`.
  - Fixed in `src/backend/services/agent_service.py` by normalizing extracted `sub_question` values to complete question format ending with `?`.
  - Restarted backend: `docker compose restart backend`.
- Post-fix verification:
  - `jq` check on `/tmp/section4_run.json`:
    - `sub_qa_count: 6`
    - `all_sub_questions_end_with_qmark: true`
  - Required context logs present:
    - `Context search complete query='What changed in NATO policy?' ... results=5`
    - `Initial decomposition context built query=What changed in NATO policy? docs=5 ...`
    - `Coordinator decomposition input prepared query=What changed in NATO policy? context_items=5`
  - Backend request log confirmed: `POST /api/agents/run HTTP/1.1" 200 OK`.
