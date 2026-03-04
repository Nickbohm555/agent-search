1. Stack: Docker Compose + FastAPI + React/TypeScript/Vite + Postgres + Alembic + pgvector.
2. Source roots: `src/backend/`, `src/frontend/`, and `docker-compose.yml`.
3. Copy env file once: `cp .env.example .env`.
4. Build all services: `docker compose build`.
5. Start all services: `docker compose up -d`.
6. Service names: `db`, `backend`, `frontend`, `chrome`.
7. Frontend URL: `http://localhost:5173`.
8. Backend URL: `http://localhost:8000`.
9. Health endpoint: `http://localhost:8000/api/health`.
10. Chrome DevTools endpoint (CDP): `http://localhost:9222`.
11. Show all logs: `docker compose logs -f`.
12. Backend logs: `docker compose logs -f backend`.
13. Frontend logs: `docker compose logs -f frontend`.
14. DB logs: `docker compose logs -f db`.
15. Show running state: `docker compose ps`.
16. Open backend shell: `docker compose exec backend sh`.
17. Open frontend shell: `docker compose exec frontend sh`.
18. Open DB shell: `docker compose exec db psql -U ${POSTGRES_USER:-agent_user} -d ${POSTGRES_DB:-agent_search}`.
19. Alembic upgrade: `docker compose exec backend alembic upgrade head`.
20. Create migration: `docker compose exec backend alembic revision -m "describe_change"`.
21. Migration history: `docker compose exec backend alembic history`.
22. Current migration: `docker compose exec backend alembic current`.
23. Verify pgvector extension: `docker compose exec db psql -U agent_user -d agent_search -c "\\dx"`.
24. Verify tables: `docker compose exec db psql -U agent_user -d agent_search -c "\\dt"`.
25. Describe documents table: `docker compose exec db psql -U agent_user -d agent_search -c "\\d+ documents"`.
26. Backend tests: `docker compose exec backend pytest`.
27. Run only API smoke tests: `docker compose exec backend pytest tests/api -m smoke`.
28. Run agent-eval tests: `docker compose exec backend pytest tests/agent -m agent_eval`.
29. Frontend tests: `docker compose exec frontend npm run test`.
30. Frontend typecheck: `docker compose exec frontend npm run typecheck`.
31. Frontend build: `docker compose exec frontend npm run build`.
32. Before commit, pass health, backend tests, frontend tests, and typecheck.
33. If backend tests do not exist for new behavior, add at least one smoke API test first.
34. If agent-eval tests do not exist, add a contract test for task input/output shape.
35. For agent features, include one trajectory-level test (multi-step) and one outcome-level test.
36. Keep agent tests deterministic with fixtures/mocks; avoid live external API dependence.
37. For frontend features, if tests do not exist, add at least one render test for the changed UI.
38. For frontend interactions, add a user-visible behavior test (click/input/result).
39. Prefer testing observable outcomes, not implementation details.
40. Keep embeddings length consistent with schema (1536) unless migration + tests update together.
41. Every DB schema change must include an Alembic migration.
42. Do not mutate production schema manually outside migrations.
43. Keep API schemas in `src/backend/schemas.py`.
44. Keep routers in `src/backend/routers/` and DB wiring in `src/backend/db.py`.
45. Keep shared backend helpers in `src/backend/utils/`.
46. Keep shared frontend helpers in `src/frontend/src/utils/`.
47. Use browser DevTools at `http://localhost:5173` for UI/network inspection.
48. Use CDP endpoint `http://localhost:9222` for automated browser checks.
49. Keep AGENTS operational only; progress and status belong in `IMPLEMENTATION_PLAN.md`.
50. If a command fails, inspect container logs first, then rerun the narrowest failing test target.
