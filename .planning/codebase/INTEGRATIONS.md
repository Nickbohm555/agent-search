# External Integrations

**Analysis Date:** 2026-03-12

## APIs & External Services

**LLM Providers:**
- OpenAI - chat model execution for runtime, query expansion, and reranking
  - SDK/Client: `langchain-openai` in `src/backend/pyproject.toml`
  - Auth: `OPENAI_API_KEY` in `.env.example`
  - Usage points: `src/backend/routers/agent.py`, `src/backend/services/query_expansion_service.py`, `src/backend/services/reranker_service.py`
- Anthropic - provider key is wired in env contract; active usage path not detected in current backend source
  - SDK/Client: Not detected in `src/backend/pyproject.toml`
  - Auth: `ANTHROPIC_API_KEY` in `.env.example`

**Knowledge/Data Source APIs:**
- Wikipedia content retrieval for ingestion
  - SDK/Client: `langchain_community.document_loaders.WikipediaLoader` via `langchain-community`/`wikipedia` dependencies
  - Auth: Not required
  - Usage points: `src/backend/services/wiki_ingestion_service.py`

**Tracing/Telemetry Services:**
- Langfuse (optional) - runtime tracing and scoring callbacks
  - SDK/Client: `langfuse` in `src/backend/pyproject.toml`
  - Auth: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`/`LANGFUSE_BASE_URL` in `.env.example`
  - Usage points: `src/backend/config.py`, `src/backend/agent_search/public_api.py`, `src/backend/agent_search/runtime/runner.py`

## Data Storage

**Databases:**
- PostgreSQL 16 with pgvector extension
  - Connection: `DATABASE_URL` in `.env.example` and `docker-compose.yml`
  - Client: SQLAlchemy + psycopg in `src/backend/db.py` and `src/backend/pyproject.toml`
  - Vector access: LangChain PGVector store in `src/backend/services/vector_store_service.py`
  - Migrations: Alembic in `src/backend/alembic.ini` and `src/backend/alembic/versions`

**File Storage:**
- Local filesystem only (source repo + Docker volumes in `docker-compose.yml`)

**Caching:**
- None detected (no Redis/Memcached integration in manifests or service wiring)

## Authentication & Identity

**Auth Provider:**
- Custom/no end-user auth detected for app routes
  - Implementation: API endpoints exposed without authentication middleware in `src/backend/main.py`, `src/backend/routers/agent.py`, and `src/backend/routers/internal_data.py`

## Monitoring & Observability

**Error Tracking:**
- No dedicated external error tracker detected (no Sentry/Bugsnag integration in manifests)

**Logs:**
- Application logging via Python `logging` and frontend `console` output
  - Backend logging setup in `src/backend/main.py` and throughout `src/backend/services`
  - Frontend runtime logs in `src/frontend/src/App.tsx`
- Optional Langfuse tracing spans/scores in `src/backend/agent_search/runtime/runner.py`

## CI/CD & Deployment

**Hosting:**
- Local Docker Compose stack (backend/frontend/db/chrome) in `docker-compose.yml`
- Browser automation/debug dependency via Browserless Chrome container in `docker-compose.yml`

**CI Pipeline:**
- GitHub Actions CI checks OpenAPI/spec and generated SDK drift in `.github/workflows/ci.yml` and `scripts/validate_openapi.sh`
- GitHub Actions release pipeline builds and publishes `agent-search-core` to PyPI in `.github/workflows/release-sdk.yml` and `scripts/release_sdk.sh`

## Environment Configuration

**Required env vars:**
- Database/runtime: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL` in `.env.example` and `docker-compose.yml`
- Frontend API/runtime: `VITE_API_BASE_URL`, `VITE_AGENT_RUN_TIMEOUT_MS` in `.env.example` and `src/frontend/src/utils/config.ts`
- LLM/tracing: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LANGFUSE_*`, `LANGCHAIN_API_KEY`, `LANGGRAPH_API_KEY` in `.env.example`

**Secrets location:**
- Local `.env` loaded by Docker Compose backend service (`docker-compose.yml`)
- CI secrets expected in GitHub Actions environment for publish path (`.github/workflows/release-sdk.yml`)

## Webhooks & Callbacks

**Incoming:**
- None detected (no webhook endpoints defined in `src/backend/routers`)

**Outgoing:**
- Langfuse callback emission from runtime when enabled in `src/backend/agent_search/public_api.py` and `src/backend/agent_search/runtime/runner.py`
- External HTTP calls to Wikipedia/OpenAI happen through LangChain integrations in `src/backend/services/wiki_ingestion_service.py`, `src/backend/services/query_expansion_service.py`, and `src/backend/services/reranker_service.py`

---

*Integration audit: 2026-03-12*
