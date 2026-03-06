# System Architecture: Agent Search

## Purpose
Provide an end-to-end retrieval and answer system where users can load curated wiki sources, run multi-step question answering, and receive a synthesized answer backed by sub-question evidence. The architecture is optimized for transparent data flow across ingestion, retrieval, decomposition, parallel sub-question processing, and optional refinement.

## High-Level Components
- Frontend (`src/frontend`): React/Vite UI for loading wiki data, wiping data, running queries, and displaying final/sub-question outputs.
- Backend API (`src/backend/main.py`, `src/backend/routers/*`): FastAPI app exposing health, data-management, and runtime agent endpoints.
- Runtime orchestration (`src/backend/services/agent_service.py`, `src/backend/agents/coordinator.py`): Coordinator/subagent flow plus deterministic pipeline stages.
- Data ingestion (`src/backend/services/internal_data_service.py`, `src/backend/services/wiki_ingestion_service.py`): Curated source resolution, wiki load, chunking, and persistence.
- Retrieval storage (`src/backend/services/vector_store_service.py`, Postgres+pgvector): Vector collection creation, embedding writes, similarity reads.
- Structured persistence (`src/backend/models.py`, Alembic): Document/chunk relational tables and schema migration lifecycle.
- Processing services:
1. document validation (`document_validation_service.py`)
2. reranking (`reranker_service.py`)
3. subanswer generation (`subanswer_service.py`)
4. subanswer verification (`subanswer_verification_service.py`)
5. initial/refined answer synthesis (`initial_answer_service.py`)
6. refinement decision/decomposition (`refinement_decision_service.py`, `refinement_decomposition_service.py`)

## Runtime And Deployment Boundaries
- `docker-compose.yml` defines runtime boundaries:
1. `frontend` container (Vite dev server on `:5173`)
2. `backend` container (FastAPI/Uvicorn on `:8000`, runs Alembic upgrade on start)
3. `db` container (Postgres 16 + pgvector extension)
4. optional `chrome` container for debug tooling
- Cross-boundary flows:
1. Browser -> frontend HTTP
2. Frontend -> backend HTTP JSON (`/api/*`)
3. Backend -> DB via SQLAlchemy and PGVector
4. Backend -> OpenAI APIs only when API key is configured (otherwise local fallback paths)

## End-to-End Data Flow
### Flow A: Internal data load (knowledge base creation)
### Inputs
- User selects a curated wiki source in frontend.
- Frontend sends `POST /api/internal-data/load` with `{ source_type: "wiki", wiki: { source_id } }`.

### Transformations
1. Router validates payload via Pydantic schema.
2. `internal_data_service.load_internal_data(...)` resolves source definition and loads wiki content.
3. `chunk_wiki_documents(...)` splits long content into chunk documents.
4. `get_embedding_model()` produces deterministic hash embeddings.
5. `get_vector_store(...)` ensures a PGVector collection exists.
6. `add_documents_to_store(...)` writes chunk embeddings + metadata into PGVector tables.
7. Service inserts source marker rows into `internal_documents` for load-state tracking.

### Outputs
- API returns `{ status, source_type, documents_loaded, chunks_created }`.
- Persistent effects:
1. vectorized chunk records available for retrieval
2. source load markers available for UI `already_loaded` state

### Flow B: Query answering pipeline (primary path)
### Inputs
- Frontend sends `POST /api/agents/run` with `{ query }`.

### Transformations
1. `run_runtime_agent(...)` obtains vector store and runs initial context retrieval on full question.
2. Retrieved docs are normalized into compact structured context (`rank/title/source/snippet`).
3. Coordinator agent is invoked with user query + initial context to produce decomposed tasks and subagent retrieval calls.
4. Callback captures `search_database` tool input/output and maps them into `sub_qa` items.
5. `run_pipeline_for_subquestions(...)` executes per item in parallel:
- validate retrieved docs
- rerank validated docs
- generate subanswer text from reranked evidence
- verify answer grounding against reranked evidence
6. `generate_initial_answer(...)` synthesizes main answer from initial context + processed `sub_qa`.
7. `should_refine(...)` decides if answer quality is insufficient.
8. If refinement is needed:
- `refine_subquestions(...)` generates focused follow-up questions
- `_seed_refined_sub_qa_from_retrieval(...)` retrieves evidence for those questions
- same parallel subquestion pipeline runs again
- synthesis runs again and refined output replaces initial output

### Outputs
- `RuntimeAgentRunResponse`:
1. `main_question`
2. `sub_qa` (the final pass used for output, initial or refined)
3. `output` (final synthesized answer)

### Flow C: Data reset and source-state refresh
### Inputs
- Frontend sends `POST /api/internal-data/wipe`.

### Transformations
1. Router calls `wipe_internal_data(...)`.
2. shared DB helper deletes chunk rows first, then document rows.
3. Transaction commits, removing internal content and load markers.

### Outputs
- wipe success response and subsequent `GET /api/internal-data/wiki-sources` returns all sources as not loaded.

## Data Model And Storage Flow
- Logical entities:
1. `internal_documents`: source-level records for attribution and loaded-state tracking.
2. `internal_document_chunks`: chunked content + embedding vectors + metadata.
- Physical storage behavior:
1. Alembic migration creates tables and `vector` extension.
2. PGVector vector collection tables are managed by LangChain PGVector integration.
3. Metadata normalization (`title/source/wiki_page/wiki_url`) keeps retrieval output renderable and filterable.
- Data movement:
1. wiki text -> chunking -> embedding vectors -> vector store rows
2. vector retrieval results -> formatted text lines -> validation/rerank/answer/verify pipeline

## Key Interfaces And APIs
- Backend REST APIs:
1. `GET /api/health`
2. `POST /api/internal-data/load`
3. `POST /api/internal-data/wipe`
4. `GET /api/internal-data/wiki-sources`
5. `POST /api/agents/run`
- Core service interfaces:
1. `run_runtime_agent(payload, db) -> RuntimeAgentRunResponse`
2. `load_internal_data(payload, db) -> InternalDataLoadResponse`
3. `search_documents_for_context(vector_store, query, k, score_threshold)`
4. `run_pipeline_for_subquestions(sub_qa) -> list[SubQuestionAnswer]`
5. `generate_initial_answer(main_question, initial_search_context, sub_qa) -> str`
- Frontend API client contracts (`src/frontend/src/utils/api.ts`) validate response shapes before UI state updates.

## Section Connectivity (1-14)
- Section 1 controls coordinator flow tracking and delegation scaffolding.
- Sections 2-5 establish initial retrieval and subquestion search expansion/search.
- Sections 6-9 transform raw retrieval into verified per-subquestion answers.
- Section 10 parallelizes the per-subquestion pipeline.
- Section 11 synthesizes initial output.
- Sections 12-14 gate and execute refinement, then replace output when needed.
- System-level behavior is the composition of these sections inside `run_runtime_agent(...)`.

## System-Wide Tradeoffs
### Chosen design
Hybrid architecture: LLM-driven decomposition + deterministic, explicit post-retrieval processing pipeline with optional refinement.

### Benefits
- Strong data-flow observability: callback-captured tool calls and structured `sub_qa` records expose intermediate states.
- Controlled quality gates: validation/reranking/verification reduce direct LLM dependence.
- Operational resilience: fallback behavior exists when OpenAI API key is absent or model calls fail.
- Modularity: each processing stage is a separate service with targeted tests.
- Practical performance: per-subquestion stages run in parallel with configurable worker limits.

### Costs
- Mixed control plane complexity: agent-driven decomposition and deterministic services increase orchestration code size.
- Format coupling: several stages rely on parseable retrieved-document text formatting (`N. title=... source=... content=...`).
- Potential latency spikes: coordinator invocation + parallel pipelines + optional second refinement pass can be slow for large sub-question sets.
- Final-pass overwrite semantics: when refinement runs, initial `sub_qa` is replaced in response, reducing direct comparison visibility.

### Alternatives considered or effectively rejected
1. End-to-end single LLM answer without staged retrieval checks.
- Pros: simpler architecture.
- Cons: weaker grounding/traceability and less deterministic behavior.
2. Fully deterministic decomposition without agent orchestration.
- Pros: easier predictability and testing.
- Cons: weaker adaptive decomposition for complex queries.
3. Storing only vector chunks without `internal_documents` source markers.
- Pros: less relational schema surface.
- Cons: poorer load-state UX and source tracking.
4. Serial subquestion processing.
- Pros: simpler execution model.
- Cons: significantly worse latency as subquestion count grows.

## Operational Notes
- Backend startup runs migrations automatically before serving.
- Environment variables tune retrieval depth, validation thresholds, rerank behavior, model choices, and concurrency.
- The frontend enforces request timeouts (longer timeout for `/api/agents/run`) and validates response shape before rendering.
- Primary test coverage is in backend service and API tests under `src/backend/tests/*` and frontend tests under `src/frontend/src/App.test.tsx`.
