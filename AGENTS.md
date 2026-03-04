you have access to openAI API key and langfuse for testing now.
1. Project status: scaffold-only; do not assume business features exist yet.
2. Stack: Docker Compose + FastAPI + React/TypeScript/Vite + Postgres + Alembic + pgvector.
3. Source roots: `src/backend/`, `src/frontend/`, and `docker-compose.yml`.
4. Backend dependencies are managed with `uv` (`pyproject.toml` + `uv.lock`).
5. Copy env file once: `cp .env.example .env`.
6. Build all services: `docker compose build`.
7. Start all services: `docker compose up -d`.
8. Refresh (normal iteration): Restart backend to pick up code changes: `docker compose restart backend`. No need to tear down or rebuild unless you change dependencies or Dockerfile.
9. Start fresh (when needed): Remove all services, volumes, and images: `docker compose down -v --rmi all`, then `docker compose build` and `docker compose up -d`.
10. Service names: `db`, `backend`, `frontend`, `chrome`.
11. Frontend URL: `http://localhost:5173`.
12. Backend URL: `http://localhost:8000`.
13. Health endpoint: `http://localhost:8000/api/health`.
14. Chrome DevTools endpoint (CDP): `http://localhost:9222`.
15. Tail all logs: `docker compose logs -f`.
16. Tail backend logs: `docker compose logs -f backend`.
17. Tail frontend logs: `docker compose logs -f frontend`.
18. Tail DB logs: `docker compose logs -f db`.
19. Show running state: `docker compose ps`.
20. Backend shell: `docker compose exec backend sh`.
21. Frontend shell: `docker compose exec frontend sh`.
22. DB shell: `docker compose exec db psql -U ${POSTGRES_USER:-agent_user} -d ${POSTGRES_DB:-agent_search}`.
23. Alembic upgrade: `docker compose exec backend uv run alembic upgrade head`.
24. Create migration: `docker compose exec backend uv run alembic revision -m "describe_change"`.
25. Alembic history: `docker compose exec backend uv run alembic history`.
26. Alembic current: `docker compose exec backend uv run alembic current`.
27. Verify pgvector extension: `docker compose exec db psql -U agent_user -d agent_search -c "\\dx"`.
28. Verify tables: `docker compose exec db psql -U agent_user -d agent_search -c "\\dt"`.
29. Wipe internal data (documents + chunks only): `docker compose exec db psql -U agent_user -d agent_search -c "TRUNCATE internal_documents CASCADE;"`.
30. Backend tests: `docker compose exec backend uv run pytest`.
31. Backend smoke tests: `docker compose exec backend uv run pytest tests/api -m smoke`.
32. Frontend tests: `docker compose exec frontend npm run test`.
33. Frontend typecheck: `docker compose exec frontend npm run typecheck`.
34. Frontend build check: `docker compose exec frontend npm run build`.
35. Before commit, pass health + backend tests + frontend tests + typecheck.
36. If backend tests for a new behavior do not exist, add one smoke test first.
37. If frontend tests for a UI change do not exist, add one render/interaction test first.
38. Tests should verify outcomes, not internal implementation details.
39. Keep tests deterministic; avoid hidden network dependencies in CI.
40. Keep API schemas in `src/backend/schemas/` with one file per schema topic.
41. Keep routers in `src/backend/routers/`.
42. Keep DB wiring in `src/backend/db.py`.
43. Keep backend helpers in `src/backend/utils/`.
44. Keep frontend shared helpers in `src/frontend/src/utils/`.
45. Keep Alembic migration files in `src/backend/alembic/versions/`.
46. Every schema change requires a migration file in the same change.
47. Do not manually mutate production schema outside migrations.
48. Langfuse tracing scaffolding lives in `src/backend/observability/` with env placeholders in `.env.example`.
49. Keep tracing wiring isolated to startup/services; avoid coupling routers directly to vendor SDK clients.
50. Use browser DevTools at `http://localhost:5173` for UI/network inspection.
51. Use CDP endpoint `http://localhost:9222` for automated browser checks.
52. Keep AGENTS operational only; progress belongs in `IMPLEMENTATION_PLAN.md`.
53. Because this is scaffold-only, prioritize creating tests alongside each first implementation.
