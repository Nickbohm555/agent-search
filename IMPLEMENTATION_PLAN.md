# Agent-Search Implementation Plan (RAG-focused)

**Goal:** Build a better RAG system. Input: user question. Output: answer based on vectorized docs (with citations where applicable).

Tasks are in **recommended implementation order** (1…n). Each section = **one context window**. Complete one section at a time.

Current section to work on: section 15. (move +1 after each turn)

**Guardrail policy:** Time guardrails (Sections 3–18) **do not fail** the run. On timeout, force a return (partial result, fallback, or safe default) and continue so the pipeline stays fast and the user always gets an answer when possible.

---

## Section 1: Optional chat model parameter at run entry

**Single goal:** Allow the run entry point to accept an optional chat model (e.g. LangChain `BaseChatModel` / OpenAI) so callers can supply their own model; when not provided, keep current env-based default.

**Details:**
- Add optional `model` parameter to `run_runtime_agent` (and any public SDK entry that calls it).
- When provided, use it for `create_coordinator_agent(..., model=...)` and for the decomposition LLM call (`_run_decomposition_only_llm_call`); when not provided, use existing `_RUNTIME_AGENT_MODEL` / `_DECOMPOSITION_ONLY_MODEL` and current `ChatOpenAI` construction.
- Do not change request/response schema in this section; focus on the service layer signature and coordinator/decomposition wiring.

**Tech stack and dependencies**
- No new packages; existing `langchain_core` / `langchain_openai` for `BaseChatModel`-like typing if desired.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Add optional `model` to `run_runtime_agent`; thread to `create_coordinator_agent` and `_run_decomposition_only_llm_call`. |
| `src/backend/agents/coordinator.py` | Already accepts `model`; no change unless signature doc updated. |
| `src/backend/tests/services/test_agent_service.py` | Tests for run with provided model vs default. |

**How to test:** Unit tests: run with `model=None` (default behavior unchanged); run with a fake model and assert it is passed to `create_coordinator_agent` and used in decomposition. Restart app and run one query via API to confirm no regression.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `20 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response schema

---

## Section 2: Optional vector store parameter at run entry

**Single goal:** Allow the run entry point to accept an optional vector store instance so callers can supply their own store; when not provided, keep current `get_vector_store(...)` from env/DB.

**Details:**
- Add optional `vector_store` parameter to `run_runtime_agent` (and any public SDK entry).
- When provided, use it for initial search, coordinator retriever, and refinement retrieval; when not provided, call `get_vector_store(connection=..., collection_name=..., embeddings=...)` as today.
- Do not change request/response schema in this section; focus on the service layer.

**Tech stack and dependencies**
- No new packages; existing `vector_store_service.get_vector_store` and store interface (e.g. `similarity_search`).

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Add optional `vector_store` to `run_runtime_agent`; use when provided, else `get_vector_store(...)`. |
| `src/backend/tests/services/test_agent_service.py` | Tests for run with provided vector_store vs default. |

**How to test:** Unit tests: run with `vector_store=None` (default behavior unchanged); run with a fake vector_store and assert it is used for initial search and coordinator. Restart app and run one query via API to confirm no regression.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `25 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with response shape unchanged (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=80 frontend`, `docker compose logs --tail=80 db` -> reviewed for visibility; no change-specific backend exceptions

---

## Section 3: Time guardrail configuration

**Single goal:** Introduce a single place (env or config) that defines timeout seconds for each RAG step so every guardrail can be configured without code changes.

**Details:**
- Define named timeout keys (e.g. `INITIAL_SEARCH_TIMEOUT_S`, `DECOMPOSITION_LLM_TIMEOUT_S`, `COORDINATOR_INVOKE_TIMEOUT_S`, etc.) and read from env with sensible defaults (e.g. 30–120s for LLM steps, 10–30s for retrieval).
- No actual timeout enforcement in this section; only add the configuration and document it (e.g. in `.env.example` or docs).

**Tech stack and dependencies**
- No new packages; `os.getenv` or existing config pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` or a small `config.py` / env module | Declare and read timeout env vars for all steps. |
| `.env.example` or `docs/` | Document new env vars and default values. |

**How to test:** Assert that timeout values are read correctly in tests (e.g. default present, override from env when set). No runtime behavior change yet.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `29 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response shape (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no change-specific backend exceptions

---

## Section 4: Time guardrail — vector store acquisition

**Single goal:** Enforce a maximum time for obtaining the vector store when not provided by the caller (i.e. for the `get_vector_store(...)` path).

**Details:**
- When `run_runtime_agent` calls `get_vector_store(...)`, wrap that call in a timeout; on timeout, **do not fail**—return a safe fallback (e.g. return early from run with a short “unavailable” message, or retry once with shorter timeout) so the API still returns a response.
- Use the timeout value from Section 3 (e.g. `VECTOR_STORE_ACQUISITION_TIMEOUT_S`).
- When caller provides `vector_store`, skip this step; no guardrail applied.

**Tech stack and dependencies**
- Python stdlib `concurrent.futures` or equivalent; no new pip packages.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap `get_vector_store` in timeout when vector_store not provided. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout triggers and normal completion. |

**How to test:** Unit test: mock slow `get_vector_store` and assert timeout raises; test normal path still returns store. Restart app and run one query.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `25 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with response shape unchanged (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=80 frontend`, `docker compose logs --tail=80 db` -> reviewed for visibility; no change-specific backend exceptions

---

## Section 5: Time guardrail — initial search (context for decomposition)

**Single goal:** Enforce a maximum time for the initial retrieval and context build (search_documents_for_context + build_initial_search_context) before decomposition.

**Details:**
- Wrap the block that performs initial search and builds `initial_search_context` in a timeout; on timeout, **do not fail**—use empty or partial context and continue (decomposition can still run with less context).
- Use config from Section 3 (e.g. `INITIAL_SEARCH_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; reuse same timeout pattern as Section 4.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap initial search + build_initial_search_context in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: slow search mock triggers timeout; normal path succeeds. Restart app and run one query.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `27 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response shape (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no change-specific backend exceptions

---

## Section 6: Time guardrail — decomposition LLM call

**Single goal:** Enforce a maximum time for the decomposition-only LLM call (`_run_decomposition_only_llm_call`).

**Details:**
- Wrap `_run_decomposition_only_llm_call` in a timeout; on timeout, **do not fail**—use fallback (e.g. single normalized question from user query) and continue so the pipeline still runs.
- Use config from Section 3 (e.g. `DECOMPOSITION_LLM_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap _run_decomposition_only_llm_call in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout (fallback or error) and normal path. |

**How to test:** Unit test: slow LLM mock triggers timeout; normal path returns parsed sub-questions. Restart app and run one query.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `29 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response shape (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no change-specific backend exceptions

---

## Section 7: Time guardrail — coordinator agent invoke

**Single goal:** Enforce a maximum time for the coordinator agent invocation (agent.invoke with sub-questions and retriever tool).

**Details:**
- Wrap `agent.invoke(...)` in a timeout; on timeout, **do not fail**—use whatever messages/sub_qa were captured so far (or build minimal sub_qa from decomposition only) and continue to synthesis so the user still gets an answer.
- Use config from Section 3 (e.g. `COORDINATOR_INVOKE_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap coordinator agent.invoke in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: slow invoke triggers timeout; normal path returns messages and sub_qa. Restart app and run one query.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `31 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response shape (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no new change-specific backend exceptions

---

## Section 8: Time guardrail — per-subquestion document validation

**Single goal:** Enforce a maximum time for the document validation step applied to each sub-question (e.g. each `_apply_document_validation_to_sub_qa` batch or per-item).

**Details:**
- Wrap the document validation work in a timeout; on timeout, **do not fail**—treat that sub-question as validation-skipped (keep existing docs/order) and continue so the pipeline returns an answer.
- Use config from Section 3 (e.g. `DOCUMENT_VALIDATION_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap document validation in timeout (per item or per batch as chosen). |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: slow validation triggers timeout; normal path completes. Restart app and run one query.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `35 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response shape (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no reranking-guardrail runtime exceptions

---

## Section 9: Time guardrail — per-subquestion reranking

**Single goal:** Enforce a maximum time for the reranking step applied to each sub-question.

**Details:**
- Wrap the reranking work in a timeout; on timeout, **do not fail**—keep existing document order and continue so the pipeline returns an answer.
- Use config from Section 3 (e.g. `RERANK_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap reranking in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: slow rerank triggers timeout; normal path completes. Restart app and run one query.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `39 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response shape (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no Section 11 change-specific runtime exceptions (verification timeout guardrail logs and fallbacks are present in unit test coverage)

---

## Section 10: Time guardrail — per-subquestion subanswer generation

**Single goal:** Enforce a maximum time for the subanswer generation step (LLM call per sub-question).

**Details:**
- Wrap the subanswer generation call in a timeout; on timeout, **do not fail**—use fallback text (e.g. “Answer not available in time”) or mark unanswerable and continue so the pipeline returns an answer.
- Use config from Section 3 (e.g. `SUBANSWER_GENERATION_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap subanswer generation in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: slow subanswer triggers timeout; normal path completes. Restart app and run one query.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `37 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response shape (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no change-specific backend exceptions

---

## Section 11: Time guardrail — per-subquestion subanswer verification

**Single goal:** Enforce a maximum time for the subanswer verification step per sub-question.

**Details:**
- Wrap the verification call in a timeout; on timeout, **do not fail**—mark as not answerable (or use default reason) and continue so the pipeline returns an answer.
- Use config from Section 3 (e.g. `SUBANSWER_VERIFICATION_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap subanswer verification in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: slow verify triggers timeout; normal path completes. Restart app and run one query.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `41 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response shape (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; backend guardrail and request logs present, no Section 12 change-specific runtime exceptions

---

## Section 12: Time guardrail — entire per-subquestion pipeline

**Single goal:** Enforce a maximum total time for `run_pipeline_for_subquestions` (all sub-questions, parallel) so the whole lane is capped even if individual steps pass.

**Details:**
- Wrap `run_pipeline_for_subquestions(sub_qa)` in a timeout; on timeout, **do not fail**—return whatever sub_qa items completed so far and treat the rest as skipped/unanswerable so synthesis still runs and the user gets an answer.
- Use config from Section 3 (e.g. `SUBQUESTION_PIPELINE_TOTAL_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern; coordinate with ThreadPoolExecutor usage.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap run_pipeline_for_subquestions in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout (partial results) and normal path. |

**How to test:** Unit test: pipeline that would exceed limit returns partial results or error; normal path returns full sub_qa. Restart app and run one query.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `41 passed`
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response shape (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; backend guardrail and request logs present, no Section 12 change-specific runtime exceptions

---

## Section 13: Time guardrail — initial answer generation

**Single goal:** Enforce a maximum time for generating the initial answer from context and sub_qa (`generate_initial_answer`).

**Details:**
- Wrap `generate_initial_answer(...)` in a timeout; on timeout, **do not fail**—return a fallback string (e.g. concatenate available subanswers or “Answer generation timed out; partial context only”) so the API still returns a response.
- Use config from Section 3 (e.g. `INITIAL_ANSWER_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap generate_initial_answer in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: slow generate_initial_answer triggers timeout; normal path returns output. Restart app and run one query.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `43 passed`
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py::test_run_runtime_agent_uses_partial_fallback_when_initial_answer_times_out -o log_cli=true --log-cli-level=WARNING'` -> `1 passed` with initial-answer timeout guardrail logs
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response shape (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; backend showed normal restart/watch reload plus request logs, no Section 13 runtime exceptions

---

## Section 14: Time guardrail — refinement decision

**Single goal:** Enforce a maximum time for the refinement decision step (`should_refine`).

**Details:**
- Wrap `should_refine(...)` in a timeout; on timeout, **do not fail**—treat as no refinement (safe default: return initial answer) and continue.
- Use config from Section 3 (e.g. `REFINEMENT_DECISION_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap should_refine in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: slow should_refine triggers timeout; normal path returns decision. Restart app and run one query.

**Test results:**
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `44 passed`
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py::test_run_runtime_agent_skips_refinement_when_decision_times_out -o log_cli=true --log-cli-level=WARNING'` -> `1 passed` with refinement decision timeout guardrail logs
- `docker compose restart backend` -> backend restarted successfully
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with unchanged response shape (`main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no Section 14 change-specific runtime exceptions

---

## Section 15: Time guardrail — refinement decomposition

**Single goal:** Enforce a maximum time for refinement decomposition (`refine_subquestions`).

**Details:**
- Wrap `refine_subquestions(...)` in a timeout; on timeout, **do not fail**—use empty list (no refined sub-questions) and return initial answer as final output so the user still gets a response.
- Use config from Section 3 (e.g. `REFINEMENT_DECOMPOSITION_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap refine_subquestions in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: slow refine_subquestions triggers timeout; normal path returns list. Restart app and run one query that triggers refinement.

**Test results:** (Add when section is complete.)

---

## Section 16: Time guardrail — refinement retrieval

**Single goal:** Enforce a maximum time for refinement retrieval (`_seed_refined_sub_qa_from_retrieval`).

**Details:**
- Wrap `_seed_refined_sub_qa_from_retrieval(...)` in a timeout; on timeout, **do not fail**—return partial list or empty and continue (use initial answer as final if refinement path yields nothing).
- Use config from Section 3 (e.g. `REFINEMENT_RETRIEVAL_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap _seed_refined_sub_qa_from_retrieval in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: slow refinement retrieval triggers timeout; normal path returns seeded sub_qa. Restart app and run one query that triggers refinement.

**Test results:** (Add when section is complete.)

---

## Section 17: Time guardrail — refinement pipeline run

**Single goal:** Enforce a maximum time for the refinement path’s per-subquestion pipeline run (second `run_pipeline_for_subquestions` on refined sub_qa).

**Details:**
- Reuse the same whole-pipeline timeout as Section 12, or define `REFINEMENT_PIPELINE_TOTAL_TIMEOUT_S`; wrap the refinement pipeline call in that timeout; on timeout, **do not fail**—return partial refined results or keep initial answer as final so the user still gets a response.

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap refinement run_pipeline_for_subquestions in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: refinement pipeline timeout; normal path returns refined output. Restart app and run one query that triggers refinement.

**Test results:** (Add when section is complete.)

---

## Section 18: Time guardrail — refined answer generation

**Single goal:** Enforce a maximum time for generating the refined final answer (second `generate_initial_answer` call in the refinement path).

**Details:**
- Wrap the refined-answer `generate_initial_answer(...)` call in a timeout; on timeout, **do not fail**—keep initial answer as final output so the user always gets a response.
- Use config from Section 3 (e.g. same `INITIAL_ANSWER_TIMEOUT_S` or `REFINED_ANSWER_TIMEOUT_S`).

**Tech stack and dependencies**
- Python stdlib; same timeout pattern.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Wrap refined generate_initial_answer in timeout. |
| `src/backend/tests/services/test_agent_service.py` | Test timeout and normal path. |

**How to test:** Unit test: slow refined answer generation triggers timeout; normal path returns refined output. Restart app and run one query that triggers refinement.

**Test results:** (Add when section is complete.)

---
