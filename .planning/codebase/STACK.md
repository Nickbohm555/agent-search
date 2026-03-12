# Technology Stack

**Analysis Date:** 2026-03-12

## Languages

**Primary:**
- Python 3.11-3.13 (`>=3.11,<3.14`) - backend API/runtime and SDK core in `src/backend/pyproject.toml` and `sdk/core/pyproject.toml`
- TypeScript (strict mode) - frontend app in `src/frontend/tsconfig.json` and `src/frontend/src`

**Secondary:**
- Shell (`sh`/`bash`) - automation scripts in `scripts/validate_openapi.sh`, `scripts/update_sdk.sh`, and `scripts/release_sdk.sh`
- YAML - container orchestration and CI workflows in `docker-compose.yml` and `.github/workflows/*.yml`

## Runtime

**Environment:**
- Backend container runtime: `python:3.11-slim` in `src/backend/Dockerfile`
- Frontend container runtime: `node:20-alpine` in `src/frontend/Dockerfile`
- Database runtime: `pgvector/pgvector:pg16` in `docker-compose.yml`

**Package Manager:**
- Backend: `uv` with lockfile-driven sync (`uv sync --frozen`) in `src/backend/Dockerfile`
- Frontend: `npm` in `src/frontend/package.json`
- Lockfile: present (`src/backend/uv.lock`, `src/frontend/package-lock.json`)

## Frameworks

**Core:**
- FastAPI `0.115.12` - HTTP API layer in `src/backend/pyproject.toml` and `src/backend/main.py`
- React `18.3.1` - frontend UI in `src/frontend/package.json` and `src/frontend/src/main.tsx`
- Vite `5.4.14` - frontend dev/build tool in `src/frontend/package.json` and `src/frontend/vite.config.ts`

**Testing:**
- Pytest (invoked via `uv run pytest`) - backend tests in `src/backend/tests`
- Vitest `2.1.9` + Testing Library - frontend tests in `src/frontend/package.json` and `src/frontend/src/App.test.tsx`
- FastAPI TestClient - API endpoint verification in `src/backend/tests/api/test_health.py`

**Build/Dev:**
- Docker Compose - multi-service local runtime in `docker-compose.yml`
- Alembic `1.15.1` - DB migrations in `src/backend/pyproject.toml`, `src/backend/alembic.ini`, and `src/backend/alembic/versions`
- Uvicorn `0.34.0` - ASGI server launch command in `docker-compose.yml`
- OpenAPI Generator CLI (containerized) - SDK drift validation in `scripts/validate_openapi.sh`

## Key Dependencies

**Critical:**
- `fastapi==0.115.12` - backend API framework in `src/backend/pyproject.toml`
- `sqlalchemy==2.0.40` and `psycopg[binary]==3.2.6` - relational DB access in `src/backend/pyproject.toml` and `src/backend/db.py`
- `pgvector==0.3.6` - vector extension integration in `src/backend/pyproject.toml` and `src/backend/services/vector_store_service.py`
- `langchain>=1.2.0`, `langchain-community==0.3.31`, `langchain-openai>=0.3.0` - retrieval/rerank orchestration in `src/backend/pyproject.toml` and `src/backend/services`

**Infrastructure:**
- `uvicorn[standard]==0.34.0` - backend runtime server in `src/backend/pyproject.toml`
- `alembic==1.15.1` - schema migration management in `src/backend/pyproject.toml` and `src/backend/alembic`
- `langfuse>=3.0.0` - optional tracing hooks in `src/backend/pyproject.toml`, `src/backend/config.py`, and `src/backend/agent_search/public_api.py`
- `wikipedia>=1.4.0` - wiki ingestion dependency in `src/backend/pyproject.toml` and `src/backend/services/wiki_ingestion_service.py`

## Configuration

**Environment:**
- Central env contract documented in `.env.example`
- Backend service loads `.env` and overrides `DATABASE_URL` in `docker-compose.yml`
- Frontend runtime env uses `VITE_API_BASE_URL` and timeout vars via `src/frontend/src/utils/config.ts` and `src/frontend/src/utils/api.ts`
- LLM/tracing credentials and toggles (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LANGFUSE_*`, `LANGCHAIN_*`) defined in `.env.example`

**Build:**
- Backend build config in `src/backend/Dockerfile` and `src/backend/pyproject.toml`
- Frontend build config in `src/frontend/Dockerfile`, `src/frontend/package.json`, and `src/frontend/vite.config.ts`
- Compose orchestration in `docker-compose.yml`
- CI/release workflow definitions in `.github/workflows/ci.yml` and `.github/workflows/release-sdk.yml`

## Platform Requirements

**Development:**
- Docker + Docker Compose required for full stack in `docker-compose.yml`
- Python 3.11-compatible environment required by backend constraints in `src/backend/pyproject.toml` and `.github/workflows/ci.yml`
- Node 20 runtime expected by frontend container in `src/frontend/Dockerfile`
- `uv` required for backend dependency resolution and local script flows in `src/backend/Dockerfile` and `scripts/update_sdk.sh`

**Production:**
- Not detected as a separate production deployment target in repo config (`docker-compose.yml` is dev-centric and no infra-as-code for cloud deploy is present).
- SDK publishing pipeline targets PyPI via GitHub Actions in `.github/workflows/release-sdk.yml`.

---

*Stack analysis: 2026-03-12*
