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
