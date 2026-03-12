# Stack Research

**Domain:** LangGraph-native state graph migration for an existing Python RAG orchestration backend
**Researched:** 2026-03-12
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | `3.12.x` runtime (keep package support `>=3.11,<3.14`) | Production runtime for backend and SDK | Best balance of maturity/performance for current LangGraph/OpenAI ecosystem while staying aligned with your existing Python range. |
| LangGraph | `~1.1` (currently `1.1.2`) | Primary orchestration runtime using `StateGraph` | Official low-level orchestration framework for durable, stateful workflows; explicitly designed for production execution semantics. |
| langgraph-checkpoint-postgres | `~3.0` (currently `3.0.4`) | Durable checkpoint persistence in Postgres | Official LangGraph production-grade checkpointer for Postgres (`PostgresSaver` / `AsyncPostgresSaver`), best fit for your existing Postgres stack. |
| langchain-openai | `~1.1` (currently `1.1.11`) | OpenAI model adapter for LangChain/LangGraph | Preserves OpenAI baseline while keeping orchestration graph-native; minimizes provider migration risk. |
| openai | `~2.26` (currently `2.26.0`) | Provider SDK baseline and fallback direct client usage | Official SDK; current README positions Responses API as primary and Chat Completions as legacy-but-supported baseline. |
| FastAPI | `~0.135` (currently `0.135.1`) | API surface and deployment integration | Keeps app contract stable while orchestration internals migrate; compatible with Pydantic v2 baseline. |
| Pydantic | `~2.12` (currently `2.12.5`) | State/input/output schemas and validation | Current ecosystem standard for FastAPI/LangChain stack; strict schema control is critical for deterministic graph state. |
| SQLAlchemy + psycopg + pgvector | `~2.0` / `~3.3` / `~0.4` | Existing persistence + vector retrieval | Avoids unnecessary datastore churn during orchestration migration; aligns with current architecture and Docker Compose deployment model. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| langchain-core | `~1.2` (currently `1.2.18`) | Core message/tool/runnable abstractions | Use for model/tool interfaces without pulling legacy orchestration behavior. |
| langsmith | `~0.7` (currently `0.7.16`) | Tracing, eval, and runtime observability | Use in all pre-prod/prod environments for migration confidence and graph debugging. |
| langchain-text-splitters | `~1.1` (currently `1.1.1`) | Document chunking consistency | Keep if your ingestion/search pipeline depends on existing chunking behavior. |
| httpx | `~0.28` (currently `0.28.1`) | Async HTTP integrations in graph nodes/tasks | Use for deterministic, testable external calls wrapped in LangGraph tasks. |
| orjson | `~3.11` (currently `3.11.7`) | High-throughput JSON serialization | Use if response/state payload volume is high and JSON becomes a CPU hot path. |
| tenacity | `~9` | Retry/backoff around provider and network edges | Use at integration boundaries, not deep inside pure graph state transforms. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Dependency + lock management | Keep single lock discipline and avoid mixed resolver workflows (`pip install` ad hoc in dev). |
| pytest + pytest-asyncio | Graph behavior and async integration tests | Add replay/resume/idempotency tests specific to LangGraph durability semantics. |
| Alembic | Schema migration control | Use for any checkpoint/store schema changes; keep migration ordering explicit. |
| Docker Compose | Remote parity validation | Keep as production parity harness for milestone acceptance criteria. |

## Installation

```bash
# Core graph migration dependencies (backend/sdk)
uv add "langgraph~=1.1" "langgraph-checkpoint-postgres~=3.0" \
  "langchain-openai~=1.1" "openai~=2.26" "langchain-core~=1.2"

# Supporting (as needed)
uv add "langsmith~=0.7" "httpx~=0.28" "orjson~=3.11" "tenacity~=9.0"

# Keep existing app stack current
uv add "fastapi~=0.135" "pydantic~=2.12" "sqlalchemy~=2.0" \
  "psycopg[binary,pool]~=3.3" "pgvector~=0.4" "alembic~=1.18"

# Test/dev
uv add --dev "pytest~=9.0" "pytest-asyncio~=1.3"
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `langgraph-checkpoint-postgres` | `langgraph-checkpoint-sqlite` | Local prototyping only; not for remote multi-instance production. |
| LangGraph `StateGraph` orchestration | LangChain high-level agent loops only | Small/simple assistants with minimal control-flow needs; not suitable for your existing multi-stage RAG orchestration requirements. |
| OpenAI via `langchain-openai` (+ `openai` SDK available) | Provider abstraction swap during same milestone | Only in later milestones after graph migration stabilizes and parity tests pass. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `InMemorySaver` in production | No durable restart/recovery guarantees across process restarts | `langgraph-checkpoint-postgres` with thread IDs and Postgres-backed checkpointing |
| `langgraph-checkpoint-sqlite` for remote prod | Good for local workflows, weak fit for concurrent distributed runtime | Postgres checkpointer already aligned with your infra |
| `langchain-classic` as orchestration foundation | Legacy abstraction layer increases migration drag and behavior ambiguity | LangGraph `StateGraph` + explicit nodes/tasks and typed state |
| Unbounded majors (`>=` only) for core orchestrator deps | Major-version drift can break graph/runtime semantics unexpectedly | Use compatible minor pins (`~=`) and controlled bump windows |
| Direct Chat Completions as new primary integration path | OpenAI’s current SDK docs position Responses API as the primary API | Keep OpenAI baseline through `langchain-openai` and/or OpenAI Responses API |

## Stack Patterns by Variant

**If migration must preserve exact behavior first (recommended first milestone):**
- Keep retrieval/indexing/storage stack unchanged.
- Replace only orchestration control flow with `StateGraph` nodes and typed state.
- Enable Postgres checkpointer early to validate replay/resume semantics.

**If optimizing for throughput after parity is proven:**
- Introduce async nodes + `AsyncPostgresSaver`.
- Add targeted retries (`tenacity`) and JSON perf tuning (`orjson`) where profiling proves benefit.
- Keep model/provider behavior stable while scaling execution characteristics.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `langgraph~=1.1` | `langgraph-checkpoint-postgres~=3.0` | Officially aligned package family for state graph + Postgres checkpointing. |
| `langchain-openai~=1.1` | `openai~=2.26` and `langchain-core~=1.2` | Keeps OpenAI provider baseline while using modern LangChain core interfaces. |
| `fastapi~=0.135` | `pydantic~=2.12` | Current FastAPI generation built on Pydantic v2. |
| `sqlalchemy~=2.0` | `psycopg[binary,pool]~=3.3` | Mature Postgres integration path with sync/async options. |
| `pgvector~=0.4` | Postgres with pgvector extension | Keep existing semantic search storage unchanged during orchestration migration. |

## Migration-Safe Upgrade Sequencing

1. **Preflight lock discipline:** Convert core deps to compatible minor pins (`~=`) in backend and SDK manifests; regenerate lockfiles.
2. **Foundation upgrade:** Upgrade `langgraph`, `langchain-core`, `langchain-openai`, `openai` together in one branch without graph rewrites yet; run smoke tests.
3. **Durability layer:** Add `langgraph-checkpoint-postgres`; wire thread IDs and checkpoint setup; verify resume/replay behavior in Docker Compose.
4. **Graph refactor:** Move orchestration stages (decompose, validate, semantic search, subanswers, synthesis) into explicit `StateGraph` nodes with typed state.
5. **Provider stabilization:** Keep OpenAI baseline constant; only adjust model IDs/params after parity tests pass.
6. **SDK/documentation release prep:** Update PyPI package metadata, API docs, and app HTML docs after functional parity and remote environment validation.
7. **Hardening pass:** Add trace/eval coverage (LangSmith), idempotency checks for side-effect nodes, and failure recovery tests.

## Sources

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) — production positioning and install guidance (HIGH)
- [LangGraph durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution) — determinism/idempotency requirements (HIGH)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) — checkpointer options; Postgres marked ideal for production (HIGH)
- [LangGraph add-memory how-to](https://langchain-ai.github.io/langgraph/how-tos/memory/add-memory/) — practical Postgres checkpointer install patterns (MEDIUM; older docs domain)
- [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview) — LangChain-on-LangGraph relationship and abstraction boundaries (HIGH)
- [openai-python README](https://raw.githubusercontent.com/openai/openai-python/main/README.md) — Responses API primary, Chat Completions legacy supported (HIGH)
- [PyPI JSON: langgraph](https://pypi.org/pypi/langgraph/json), [langgraph-checkpoint-postgres](https://pypi.org/pypi/langgraph-checkpoint-postgres/json), [langchain-openai](https://pypi.org/pypi/langchain-openai/json), [openai](https://pypi.org/pypi/openai/json), [fastapi](https://pypi.org/pypi/fastapi/json), [pydantic](https://pypi.org/pypi/pydantic/json), [langchain-core](https://pypi.org/pypi/langchain-core/json), [langsmith](https://pypi.org/pypi/langsmith/json), [sqlalchemy](https://pypi.org/pypi/sqlalchemy/json), [psycopg](https://pypi.org/pypi/psycopg/json), [pgvector](https://pypi.org/pypi/pgvector/json), [alembic](https://pypi.org/pypi/alembic/json), [uvicorn](https://pypi.org/pypi/uvicorn/json) — current version baselines as of 2026-03-12 (HIGH)

---
*Stack research for: LangGraph State Graph Migration for Agent Search*
*Researched: 2026-03-12*
