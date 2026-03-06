# AGENT-SEARCH

```
╔══════════════════════════════════════════════════════════════════╗
║  RETRIEVAL + DECOMPOSITION + SYNTHESIS  │  WIKI → VECTORS → QA   ║
╚══════════════════════════════════════════════════════════════════╝
```

**Multi-step question answering over curated wiki sources.** Load knowledge, decompose questions, run parallel sub-question pipelines, synthesize answers with optional refinement. Built for transparent data flow and grounded evidence.

---

## SYSTEM OVERVIEW

| Layer        | Stack |
|-------------|--------|
| **Frontend** | React, TypeScript, Vite — load sources, run queries, view sub-QA + final answer |
| **Backend**  | FastAPI, Uvicorn — health, data load/wipe, agent run |
| **Orchestration** | Coordinator agent (decomposition) + deterministic pipeline (validation → rerank → subanswer → verify → synthesis) |
| **Storage**  | Postgres 16, pgvector, Alembic — documents, chunks, embeddings |
| **Runtime**  | Docker Compose — `db`, `backend`, `frontend`, optional `chrome` |

---

## QUICK START

```bash
# Build and bring the stack online
docker compose build
docker compose up -d

# Frontend  →  http://localhost:5173
# Backend   →  http://localhost:8000
# Health    →  http://localhost:8000/api/health
```

**First run:** Load a wiki source in the UI, then run a query. Backend runs Alembic on startup.

**Iterate:** `docker compose restart backend` after code changes. Full reset: `docker compose down -v --rmi all` then rebuild and `up -d`.

---

## DATA FLOW

```
[ USER QUERY ]
      │
      ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Initial search  │────▶│ Coordinator      │────▶│ Sub-question search │
│ (vector store)  │     │ (decompose +     │     │ (per sub-Q, parallel)│
└─────────────────┘     │  tool callbacks) │     └──────────┬──────────┘
                        └──────────────────┘                │
                                                            ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Final answer    │◀────│ Initial answer   │◀────│ Validate → Rerank   │
│ (or refined)    │     │ synthesis        │     │ → Subanswer → Verify │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                              │
                              ▼
                        [ Refine? ] ──yes──▶ Refine sub-Qs → pipeline again
```

- **Load knowledge:** `POST /api/internal-data/load` with `{ "source_type": "wiki", "wiki": { "source_id": "…" } }`.
- **Run QA:** `POST /api/agents/run` with `{ "query": "…" }` → `main_question`, `sub_qa`, `output`.
- **Wipe:** `POST /api/internal-data/wipe` — clears documents and chunks; wiki sources report not loaded.

---

## API SURFACE

| Method | Path | Purpose |
|--------|------|--------|
| GET  | `/api/health` | Liveness |
| POST | `/api/internal-data/load` | Load wiki (or other curated) source |
| POST | `/api/internal-data/wipe` | Remove all internal docs/chunks |
| GET  | `/api/internal-data/wiki-sources` | List wiki sources and load state |
| POST | `/api/agents/run` | Run full QA pipeline |

---

## REPO LAYOUT

```
agent-search/
├── docker-compose.yml      # db, backend, frontend, chrome
├── src/
│   ├── backend/            # FastAPI, agents, services, migrations
│   └── frontend/           # React/Vite app
└── docs/                   # SYSTEM_ARCHITECTURE.md, section-*.md
```

Backend: `uv` + `pyproject.toml`. Frontend: npm. Tests: `docker compose exec backend uv run pytest` and `docker compose exec frontend npm run test`.

---

## DOCS

- **Architecture:** [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) — components, flows, tradeoffs.
- **Sections 1–14:** [docs/section-01-coordinator-flow-tracking.md](docs/section-01-coordinator-flow-tracking.md) through refinement — implementation notes and validation.

---

*Agent-Search — decompose, retrieve, verify, synthesize.*
