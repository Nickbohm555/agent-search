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
