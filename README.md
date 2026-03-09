<p align="center">
  <img src="assets/readme-hud-banner.png" alt="agent-search banner" width="100%" data-darkreader-ignore />
</p>

# agent-search

`agent-search` is a Dockerized RAG application and SDK-style runtime built with FastAPI, React, Postgres, pgvector, and a state-graph backend pipeline.

## Purpose

The runtime exposes one canonical answer flow:

`decompose -> expand -> search -> rerank -> answer -> synthesize`

It returns a stable API payload:

`RuntimeAgentRunResponse { main_question, sub_qa[], output }`

## Stack

- Backend: FastAPI + `uv` + Alembic
- Frontend: React + TypeScript + Vite
- Database: Postgres 16 + pgvector
- Retrieval expansion: LangChain `MultiQueryRetriever`
- Reranking: `flashrank`
- Orchestration: graph-state runtime (`run_runtime_agent -> run_parallel_graph_runner`)

## Architecture

### System path

- User submits query in React UI.
- Frontend starts async run with `POST /api/agents/run-async`.
- Backend service runs graph pipeline and emits stage snapshots.
- Frontend polls `GET /api/agents/run-status/{job_id}` and updates timeline panels.
- Final result is returned as `main_question`, `sub_qa`, and `output`.

### Canonical graph stages

1. `decompose`
2. `expand`
3. `search`
4. `rerank`
5. `answer`
6. `synthesize`

### Graph state

Graph state carries:

- `main_question`
- `decomposition_sub_questions`
- `sub_question_artifacts[]`
- `citation_rows_by_index`
- `sub_qa` (compatibility)
- `output` (compatibility)
- `final_answer`
- `stage_snapshots`
- observability metadata: `run_id`, `thread_id`, `trace_id`, `correlation_id`

## How The Flow Works

1. `decompose`: split the main question into atomic sub-questions (normalized, deduped, question-mark terminated).
2. `expand`: generate related query variants per sub-question using `MultiQueryRetriever`, while retaining the original query and applying dedupe/limits.
3. `search`: retrieve candidate chunks for expanded queries using vector similarity, then merge/dedupe results with deterministic identity rules.
4. `rerank`: score merged candidates with `flashrank`, reorder by relevance, and trim to configured context depth.
5. `answer`: generate grounded subanswers from reranked evidence and enforce citation-backed support.
6. `synthesize`: combine subanswers into final output while preserving grounding/citation references.

## Retrieval Fundamentals

### Embeddings and nearest-neighbor retrieval

- Each text chunk is converted to an embedding vector.
- Query embeddings are compared against chunk embeddings.
- Nearest-neighbor search returns the most similar chunks as initial candidates.

### Cosine similarity intuition

- Cosine similarity measures vector direction alignment in `[-1, 1]`.
- Higher values mean stronger semantic alignment.
- Vector retrieval uses this as an initial relevance signal, not a final answer-quality guarantee.

### Why `k_fetch` then `top_n`

- `k_fetch` over-fetches a broader candidate pool during search.
- `top_n` trims to the highest-value context after reranking.
- This usually improves precision and reduces prompt/token budget compared with naive top-k only retrieval.

### Merge/dedupe and citation stability

- Candidates from multiple expanded queries are merged.
- Dedupe prefers `document_id`; fallback identity is `source + content`.
- Citation indices are assigned deterministically from post-merge/post-rerank order so `[n]` markers map consistently to evidence rows.

## Reranking Explained

### Retrieval score vs reranker score

- Initial vector score is embedding-space similarity.
- Reranker score is cross-text relevance scoring for the specific query and candidate passage.
- They measure different signals and can produce different orderings.

### Why reranking improves results

Reranking can elevate a chunk that was not highest by raw vector distance but is more directly relevant to the exact sub-question phrasing.

### Fallback behavior

If reranking is disabled or unavailable, the system keeps deterministic original candidate order and still continues the pipeline.

## Runtime Endpoints

- Health: `GET /api/health`
- Sync run: `POST /api/agents/run`
- Async run: `POST /api/agents/run-async`
- Async status: `GET /api/agents/run-status/{job_id}`
- Async cancel: `POST /api/agents/run-cancel/{job_id}`

## Quick Start

```bash
docker compose build
docker compose up -d
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/api/health`

## Useful Commands

```bash
# Logs
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db

# Containers
docker compose ps
docker compose restart backend
docker compose restart frontend

# Tests
docker compose exec backend uv run pytest
docker compose exec backend uv run pytest tests/api -m smoke
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run build
```

## Benchmark Operator CLI

Run benchmark modes from the backend container:

```bash
docker compose exec backend uv run python benchmarks/run.py \
  --dataset-id internal_v1 \
  --mode baseline_retrieve_then_answer \
  --max-questions 1
```

Export benchmark JSON artifacts (latest run by default):

```bash
docker compose exec backend uv run python benchmarks/export.py
```

Export a specific run to a custom path:

```bash
docker compose exec backend uv run python benchmarks/export.py \
  --run-id benchmark-run-123 \
  --output benchmarks/exports/benchmark-run-123.json
```

## OpenAPI / SDK

- OpenAPI artifact: `openapi.json`
- Export: `uv run --project src/backend python scripts/export_openapi.py`
- Validate: `./scripts/validate_openapi.sh`
- Generate SDK: `./scripts/generate_sdk.sh`

## SDK Release / Versioning

- Core SDK package workspace: `sdk/core`
- Package identity: `agent-search-core`
- Release tag format: `agent-search-core-v<version>` (example: `agent-search-core-v0.1.0`)

Run reproducible local release dry-run:

```bash
./scripts/release_sdk.sh
```

Run publish flow (requires `TWINE_API_TOKEN`):

```bash
PUBLISH=1 TWINE_API_TOKEN=*** ./scripts/release_sdk.sh
```

CI automation:

- Workflow: `.github/workflows/release-sdk.yml`
- Triggered automatically on matching release tags.
- Supports manual dispatch with optional publish toggle.

## Links

- Runtime flow doc: `src/frontend/public/run-flow.html`
- Architecture tracker: `ARCHITECTURE_TRACKER.md`
- Agent operation guide: `AGENTS.md`
