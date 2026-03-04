1. Project status: scaffold-only; do not assume business features exist yet.
2. Stack: Docker Compose + FastAPI + React/TypeScript/Vite + Postgres + Alembic + pgvector.
3. Source roots: `src/backend/`, `src/frontend/`, and `docker-compose.yml`.
4. Backend dependencies are managed with `uv` (`pyproject.toml` + `uv.lock`).
5. Copy env file once: `cp .env.example .env`.
6. Build all services: `docker compose build`.
7. Start all services: `docker compose up -d`.
8. Remove all services and start over: `docker compose down -v` (stops containers and removes volumes), then `docker compose build` and `docker compose up -d`.
9. Service names: `db`, `backend`, `frontend`, `chrome`.
10. Frontend URL: `http://localhost:5173`.
11. Backend URL: `http://localhost:8000`.
12. Health endpoint: `http://localhost:8000/api/health`.
13. Chrome DevTools endpoint (CDP): `http://localhost:9222`.
14. Tail all logs: `docker compose logs -f`.
15. Tail backend logs: `docker compose logs -f backend`.
16. Tail frontend logs: `docker compose logs -f frontend`.
17. Tail DB logs: `docker compose logs -f db`.
18. Show running state: `docker compose ps`.
19. Backend shell: `docker compose exec backend sh`.
20. Frontend shell: `docker compose exec frontend sh`.
21. DB shell: `docker compose exec db psql -U ${POSTGRES_USER:-agent_user} -d ${POSTGRES_DB:-agent_search}`.
22. Alembic upgrade: `docker compose exec backend uv run alembic upgrade head`.
23. Create migration: `docker compose exec backend uv run alembic revision -m "describe_change"`.
24. Alembic history: `docker compose exec backend uv run alembic history`.
25. Alembic current: `docker compose exec backend uv run alembic current`.
25. Verify pgvector extension: `docker compose exec db psql -U agent_user -d agent_search -c "\\dx"`.
26. Verify tables: `docker compose exec db psql -U agent_user -d agent_search -c "\\dt"`.
27. Backend tests: `docker compose exec backend uv run pytest`.
28. Backend smoke tests: `docker compose exec backend uv run pytest tests/api -m smoke`.
29. Frontend tests: `docker compose exec frontend npm run test`.
30. Frontend typecheck: `docker compose exec frontend npm run typecheck`.
31. Frontend build check: `docker compose exec frontend npm run build`.
32. Before commit, pass health + backend tests + frontend tests + typecheck.
33. If backend tests for a new behavior do not exist, add one smoke test first.
34. If frontend tests for a UI change do not exist, add one render/interaction test first.
35. Tests should verify outcomes, not internal implementation details.
36. Keep tests deterministic; avoid hidden network dependencies in CI.
37. Keep API schemas in `src/backend/schemas/` with one file per schema topic.
38. Keep routers in `src/backend/routers/`.
39. Keep DB wiring in `src/backend/db.py`.
40. Keep backend helpers in `src/backend/utils/`.
41. Keep frontend shared helpers in `src/frontend/src/utils/`.
42. Keep Alembic migration files in `src/backend/alembic/versions/`.
43. Every schema change requires a migration file in the same change.
44. Do not manually mutate production schema outside migrations.
45. Langfuse tracing scaffolding lives in `src/backend/observability/` with env placeholders in `.env.example`.
46. Keep tracing wiring isolated to startup/services; avoid coupling routers directly to vendor SDK clients.
47. Use browser DevTools at `http://localhost:5173` for UI/network inspection.
48. Use CDP endpoint `http://localhost:9222` for automated browser checks.
49. Keep AGENTS operational only; progress belongs in `IMPLEMENTATION_PLAN.md`.
50. Because this is scaffold-only, prioritize creating tests alongside each first implementation.
