# System Architecture

## Purpose

`agent-search` combines three aligned surfaces:

- Runtime API + UI for interactive question answering.
- In-process SDK boundary (`agent_search`) for direct Python integration.
- Benchmark execution + scoring pipeline for deterministic mode comparisons.

All three surfaces share the same canonical runtime contract:

`RuntimeAgentRunResponse { main_question, sub_qa[], output }`

## Runtime System Flow

```mermaid
flowchart TD
    U[User] --> FE[React + Vite Frontend]
    FE -->|POST /api/agents/run-async| BAPI[FastAPI Routers]
    FE -->|GET /api/agents/run-status/{job_id}| BAPI

    BAPI --> AS[agent_service.run_runtime_agent]
    AS --> VS[vector_store_service]
    AS --> GR[graph runner]

    subgraph GRAPH[Canonical graph stages]
      D[decompose] --> E[expand] --> S[search] --> R[rerank] --> A[answer] --> Y[synthesize]
    end

    GR --> GRAPH
    GRAPH --> RESP[RuntimeAgentRunResponse]
    RESP --> BAPI --> FE --> U

    VS --> DB[(Postgres + pgvector)]
```

## Benchmark System Flow

```mermaid
flowchart TD
    OP[Operator/API Client] -->|POST /api/benchmarks/runs| BR[benchmarks router]
    BR --> BJ[benchmark_jobs.start_benchmark_run_job]
    BJ --> EX[ThreadPoolExecutor job]
    EX --> RUN[BenchmarkRunner.run]

    RUN --> MODES[mode execution loop]
    MODES --> ADAPT[BenchmarkExecutionAdapter]
    ADAPT --> SDK[agent_search public_api]
    SDK --> RUNTIME[run_runtime_agent]

    RUNTIME --> DB[(Postgres + pgvector)]
    RUN --> RES[(benchmark_* tables)]

    OP -->|GET /api/benchmarks/runs| BR
    OP -->|GET /api/benchmarks/runs/{run_id}| BR
    OP -->|GET /api/benchmarks/runs/{run_id}/compare| BR
    BR --> RES
```

## SDK Runtime Boundary

Primary public module:

- `src/backend/agent_search/public_api.py`

Public functions:

- `run(query, *, vector_store, model, config=None)`
- `run_async(query, *, vector_store, model, config=None)`
- `get_run_status(job_id)`
- `cancel_run(job_id)`

Public config model:

- `RuntimeConfig` (`timeout`, `retrieval`, `rerank` sub-configs)

Public error taxonomy:

- `SDKError`
- `SDKConfigurationError`
- `SDKRetrievalError`
- `SDKModelError`
- `SDKTimeoutError`

Vector store contract:

- `VectorStoreProtocol.similarity_search(query, k, filter=None)`
- `LangChainVectorStoreAdapter` for first-class LangChain compatibility.

## Backend HTTP Surfaces

Runtime:

- `GET /api/health`
- `POST /api/agents/run`
- `POST /api/agents/run-async`
- `GET /api/agents/run-status/{job_id}`
- `POST /api/agents/run-cancel/{job_id}`

Benchmark:

- `POST /api/benchmarks/runs`
- `GET /api/benchmarks/runs`
- `GET /api/benchmarks/runs/{run_id}`
- `GET /api/benchmarks/runs/{run_id}/compare`
- `POST /api/benchmarks/runs/{run_id}/cancel`
- `POST /api/benchmarks/wipe`

Internal data:

- `GET /api/internal-data/wiki-sources`
- `POST /api/internal-data/load`
- `POST /api/internal-data/wipe`

## Data Model Boundaries

Primary runtime data:

- `internal_documents`
- `internal_document_chunks` (`embedding Vector(1536)`)

Benchmark data:

- `benchmark_runs`
- `benchmark_run_modes`
- `benchmark_results`
- `benchmark_quality_scores`
- `benchmark_citation_*`
- `benchmark_retrieval_metrics`

## Observability and Tracing

Langfuse integration exists for both runtime and benchmark scopes.

Environment knobs:

- `LANGFUSE_ENABLED`
- `LANGFUSE_BASE_URL` (fallback: `LANGFUSE_HOST`)
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_ENVIRONMENT`
- `LANGFUSE_RELEASE`
- `LANGFUSE_RUNTIME_SAMPLE_RATE`
- `LANGFUSE_BENCHMARK_SAMPLE_RATE`

Tracing utility module:

- `src/backend/utils/langfuse_tracing.py`

Runtime attaches a callback handler when enabled/sampled; benchmark pipeline emits trace/span/score events for dataset, mode, and question execution.

## Deployment Boundaries

- `frontend` container: React/Vite on `:5173`
- `backend` container: FastAPI + SDK/runtime + benchmark workers on `:8000`
- `db` container: Postgres 16 + pgvector on `:5432`
- Optional `chrome` container: remote debug endpoint on `:9222`

## Operator Workflows

Normal iteration:

```bash
docker compose restart backend
```

Fresh rebuild:

```bash
docker compose down -v --rmi all
docker compose build
docker compose up -d
```

Benchmark CLI examples:

```bash
docker compose exec backend uv run python benchmarks/run.py \
  --dataset-id internal_v1 \
  --mode baseline_retrieve_then_answer \
  --dry-run

docker compose exec backend uv run python benchmarks/export.py
```
