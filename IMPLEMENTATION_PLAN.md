# Agent-Search Implementation Plan

Tasks are in **recommended implementation order** (1…n). Each section = **one context window**. Complete one section at a time.

Current section to work on: section 1. (move +1 after each turn)

---

## Section 1: Coordinator flow tracking via write_todos and virtual file system

**Single goal:** The coordinator agent uses the deep-agents (LangGraph) `write_todos` planning tool and the **deep-agents virtual file system** to keep track of the pipeline flow so it does not lose context across steps.

**Requirement:** The coordinator **MUST** use the deep-agents library’s virtual file system (e.g. `read_file`, `write_file`, or equivalent backend) to persist or read plan/flow state across steps—in addition to `write_todos`. No custom file I/O; use the built-in filesystem tools/backend provided by deep-agents.

**Flow the coordinator coordinates (align with flow.jpg):**

1. **From the user question, parallel inputs:**
   - **Exploratory (fast & simple) search** / **full search on the original question** → results feed into decomposition context and initial-answer generation.
   - **Decompose question into sub-questions** → produces initial sub-questions (one per concept).

2. **Per initial sub-question (in parallel):** For each initial sub-question, run in order: **Expand** (query expansion) → **Search** (retrieval) → **Validate** (doc validation) → **Rerank** → **Answer** (subanswer generation) → **Check** (subanswer verification). All sub-question results feed into **Generate initial answer**.

3. **Generate initial answer:** Combine initial-search results and the aggregated sub-answers into one initial answer.

4. **Need refinement?** Decision: if **No** → output the initial answer as the final answer. If **Yes** → continue below.

5. **Refinement path:**  
   - **Generate new & informed sub-questions** from the initial answer and unanswerable sub-questions so the new sub-questions target gaps.  
   - **Per refined sub-question (in parallel):** Same pipeline as step 2: Expand → Search → Validate → Rerank → Answer → Check.  
   - **Produce & validate refined answer** from the refined sub-answers.  
   - **Compare refined to initial answer** (e.g. for quality or final synthesis), then output the final answer.

**Details:**
- At run start, the coordinator creates or updates a plan via `write_todos` with todos that mirror the stages above (e.g. initial search, decomposition, parallel initial sub-question pipelines, initial answer, refinement decision; and when refining: refined sub-questions, refined pipelines, refined answer, compare → output).
- The coordinator **MUST** use the deep-agents virtual file system to store/read plan or flow state (e.g. write the current plan or stage to a file in the agent’s filesystem, read it back when resuming or delegating). This ensures context survives across tool calls and subagent runs.
- The coordinator marks items in_progress and completed as it delegates and synthesizes. No change to decomposition or RAG logic; only wiring so the coordinator uses `write_todos` and the virtual file system with a plan aligned to this flow (see flow.jpg).

**Tech:** Deep-agents/LangGraph built-in `write_todos` tool and **virtual file system** (e.g. FilesystemMiddleware / backend with `read_file`, `write_file`, etc.). The coordinator must be configured to use a deep-agents backend that provides the virtual file system. No new packages. No Docker change.

**Files**

| File | Purpose |
|------|--------|
| `src/backend/agents/coordinator.py` | Ensure the coordinator is created with a deep-agents backend that provides the virtual file system, and that the system prompt (or invoke-time input) instructs the coordinator to use `write_todos` and the virtual file system to seed/update and persist the plan with the pipeline stages above. |

**How to test:** Unit: mock run where coordinator receives instruction to use write_todos and the virtual file system; assert plan items align with Sections 2–14 and that plan/flow state is written to or read from the virtual file system. Integration: run coordinator with a multi-step query; inspect agent state or tool calls for write_todos usage, plan content, and virtual file system usage (e.g. read_file/write_file or backend writes) for plan persistence.

**Test results:**
- Unit: `docker compose exec backend sh -lc 'uv pip install pytest && uv run pytest tests/agents/test_coordinator_agent.py tests/services/test_agent_service.py'` -> `4 passed`.
- Integration: `POST /api/agents/run` with `"What is the Strait of Hormuz?"` returned `200` and backend logs showed repeated `write_todos` tool calls with staged todo updates (initial intake/search/decompose/sub-question processing/synthesis) plus final response output.
- Smoke command status: `docker compose exec backend sh -lc 'uv run pytest tests/api -m smoke'` had no smoke-selected tests (`2 deselected`).

---

## Section 2: Initial search for decomposition context

**Single goal:** Run one retrieval for the user question and pass top-k results as context into decomposition.

**Details:**
- One retrieval (same vector store/retriever as sub-question search) using the raw user question, before decomposition.
- Return bounded top-k docs/snippets; pass as structured context (e.g. list of doc IDs, snippets, or metadata) into decomposition. Do not change decomposition logic; only add the search step and wire its output.
- k and retriever config (e.g. score threshold) configurable (env or settings).

**Tech:** Existing retriever/vector_store_service. No new packages. No Docker change unless new env vars.

**Files**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Invoke initial search before coordinator/decomposition; pass context into decomposition. |
| `src/backend/services/vector_store_service.py` (or equivalent) | Use existing similarity search; optional thin wrapper for context-only search with configurable k. |
| `src/backend/schemas/agent.py` (optional) | Optional schema for “initial search context” if not inlined in run request/state. |

**How to test:** Unit: mock retriever → assert returned context is passed to decomposition. Integration: full agent request → decomposition receives non-empty context when store has relevant docs.

**Test results:** (Add when section is complete.)

---

## Section 3: Question decomposition informed by context

**Single goal:** Produce narrow sub-questions from the user question using initial-search context (Section 2).

**Details:**
- Input: initial-search context + user question. Output: list of sub-questions (one concept per sub-question, complete questions ending with “?”).
- Decomposition = LLM (coordinator prompt) or dedicated function; deliverable = context-aware sub-questions only. No query expansion, reranking, or refinement here.

**Tech:** Existing LLM and coordinator. No new packages. No Docker change.

**Files**

| File | Purpose |
|------|--------|
| `src/backend/agents/coordinator.py` | Update system prompt/inputs so coordinator gets initial-search context and uses it for sub-questions. |
| `src/backend/services/agent_service.py` | Pass initial-search context (Section 2) into coordinator (e.g. first HumanMessage or dedicated context field). |

**How to test:** Unit: fixed context + user question → decomposition returns list of strings, each ending with “?”. Integration: ambiguous question → sub-questions align with provided context.

**Test results:** (Add when section is complete.)

---

## Section 4: Per-subquestion query expansion

**Single goal:** For each sub-question, produce an expanded query (synonyms, reformulations) for retrieval.

**Details:**
- Input: one sub-question. Output: one expanded query (or small set; if multiple, downstream defines combination, e.g. union). Expansion = LLM or rule/keyword-based. No retrieval or reranking changes here.

**Tech:** LLM if used; no new packages. No Docker change.

**Files**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` or new `src/backend/services/query_expansion_service.py` | sub_question → expanded_query; call from per-subquestion pipeline. |
| `src/backend/schemas/agent.py` (optional) | Optional expanded_query on SubQuestionAnswer or pipeline state for observability. |

**How to test:** Unit: sub-question → expanded query non-empty (or equals original if no-op). Integration: one sub-question through pipeline → search uses expanded query.

**Test results:** (Add when section is complete.)

---

## Section 5: Per-subquestion search

**Single goal:** Run retrieval per sub-question using the expanded query (Section 4); return ranked list of documents per sub-question.

**Details:**
- Input: expanded query (or sub-question if expansion skipped). Output: ordered list of docs (or IDs + snippets) per sub-question. Use existing vector store/retriever; pipeline must call it with expanded query when expansion enabled. No validation, reranking, or subanswer generation here.

**Tech:** Existing retriever and vector_store_service. No new packages. No Docker change.

**Files**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` or pipeline module | Per sub-question: call expansion then retriever with expanded query; store retrieved docs per sub-question. |
| `src/backend/tools/retriever_tool.py` | Invoked as-is or via service wrapper (query string → docs). |

**How to test:** Unit: mock retriever + expanded query → returned doc list passed to next step. Integration: one sub-question through expansion + search → doc count and content as expected.

**Test results:** (Add when section is complete.)

---

## Section 6: Per-subquestion document validation (parallel)

**Single goal:** Validate retrieved documents per sub-question (relevance/constraints); run validations in parallel across documents.

**Details:**
- Input: per-subquestion doc list. Output: per-subquestion list of docs that passed (or validation flags). Criteria configurable (score threshold, date, source allowlist); parallel within sub-question (thread pool or async). No reranking or subanswer generation here.

**Tech:** LLM or rule-based; add any new dependency to pyproject.toml. No Docker change unless new env vars.

**Files**

| File | Purpose |
|------|--------|
| New `src/backend/services/document_validation_service.py` (or equivalent) | Validate list of docs in parallel; expose to pipeline. |
| `src/backend/services/agent_service.py` or pipeline module | After search, call validation per sub-question; pass validated docs to reranking. |

**How to test:** Unit: fixed docs + rules → validated output subset/flags correct; parallel (mock delay, check total time). Integration: search → validation → only valid docs proceed.

**Test results:** (Add when section is complete.)

---

## Section 7: Per-subquestion reranking

**Single goal:** Rerank validated documents per sub-question so top results are best for subanswer generation.

**Details:**
- Input: per-subquestion validated doc list. Output: same docs in new order (or top-n) per sub-question. Reranker = cross-encoder, LLM, or heuristic. No subanswer generation or verification here.

**Tech:** Add reranker dependency if needed (e.g. sentence-transformers, LLM) in pyproject.toml. No Docker change unless new runtime dependency.

**Files**

| File | Purpose |
|------|--------|
| New `src/backend/services/reranker_service.py` (or equivalent) | rerank(docs, query) → ordered list; cross-encoder or LLM. |
| `src/backend/services/agent_service.py` or pipeline module | After validation, call reranker per sub-question; pass reranked docs to subanswer generation. |

**How to test:** Unit: fixed docs + query → output order differs when non-trivial; top doc sensible. Integration: validation → rerank → order and count verified.

**Test results:** (Add when section is complete.)

---

## Section 8: Per-subquestion subanswer generation

**Single goal:** Generate sub-answer text per sub-question from the reranked document set (Section 7).

**Details:**
- Input: sub-question + reranked docs for that sub-question. Output: one sub-answer string per sub-question. Use LLM (or existing subagent) with reranked docs as context; concise, attributed. No verification here.

**Tech:** Existing LLM and prompts. No new packages. No Docker change.

**Files**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` or new `src/backend/services/subanswer_service.py` | (sub_question, reranked_docs) → sub_answer; use Section 7 output. |
| `src/backend/agents/coordinator.py` (optional) | If RAG subagent does subanswer, ensure it receives reranked docs; else keep in dedicated service. |

**How to test:** Unit: sub-question + fixed reranked docs → sub-answer non-empty and on-topic. Integration: rerank → subanswer → SubQuestionAnswer.sub_answer set.

**Test results:** (Add when section is complete.)

---

## Section 9: Per-subquestion subanswer verification

**Single goal:** Verify each sub-answer (against reranked docs or criteria); expose answerable vs not (or confidence) for refinement.

**Details:**
- Input: sub-question, sub-answer, docs for that sub-question. Output: verification per sub-question (e.g. boolean answerable or score, optional short reason). LLM or rule-based. Expose in pipeline state or SubQuestionAnswer. No refinement logic here.

**Tech:** LLM if used. No new packages. No Docker change.

**Files**

| File | Purpose |
|------|--------|
| `src/backend/schemas/agent.py` | Optional verification fields on SubQuestionAnswer (e.g. answerable: bool, verification_reason: str). |
| New `src/backend/services/subanswer_verification_service.py` or equivalent | verify(sub_question, sub_answer, docs) → answerable + optional reason. |
| `src/backend/services/agent_service.py` or pipeline module | After subanswer generation, call verification; set SubQuestionAnswer.answerable (and reason). |

**How to test:** Unit: sub-answer contradicting docs → answerable False (or low score). Integration: subanswer → verification → response includes verification result.

**Test results:** (Add when section is complete.)

---

## Section 10: Parallel sub-question processing

**Single goal:** Run the per-subquestion pipeline (expansion → search → validation → rerank → subanswer → verification) for all sub-questions in parallel.

**Details:**
- Given sub-questions from decomposition (Section 3), run Sections 4–9 for each sub-question in parallel (thread pool, asyncio, or task graph). No shared mutable state across sub-questions; each yields one SubQuestionAnswer with sub_answer and verification. Use minimal executor (e.g. concurrent.futures) if no orchestration yet. No initial-answer assembly or refinement here.

**Tech:** concurrent.futures or asyncio (stdlib), or existing orchestration. Add new dependency to pyproject.toml if needed. No Docker change.

**Files**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` or new `src/backend/services/subquestion_pipeline.py` | run_pipeline_for_subquestions(sub_questions, ...) → expansion→…→verification per sub-question in parallel; return list of SubQuestionAnswer. |
| `src/backend/services/agent_service.py` | After decomposition, invoke parallel pipeline; pass results to initial-answer generation. |

**How to test:** Unit: 2+ sub-questions with mocks → both complete, results ordered/keyed; wall-clock < sequential. Integration: multiple sub-questions → all sub_qa populated, verification set.

**Test results:** (Add when section is complete.)

---

## Section 11: Initial answer generation

**Single goal:** Produce the initial answer from initial search results (Section 2) and sub-question answers (Section 10).

**Details:**
- Input: user question, initial-search context, list of SubQuestionAnswer. Output: one initial answer string. LLM (coordinator or synthesizer) uses both initial docs and sub_qa. No refinement decision or refinement decomposition here.

**Tech:** Existing LLM and coordinator/synthesizer. No new packages. No Docker change.

**Files**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | After parallel pipeline, call initial-answer generation with question + initial context + sub_qa; set response.output (or state for refinement). |
| `src/backend/agents/coordinator.py` (optional) | If coordinator produces initial answer, feed it initial-search context and sub_qa; else dedicated synthesizer. |

**How to test:** Unit: fixed initial context + sub_qa → initial answer non-empty, aligned with inputs. Integration: full flow → response.output is initial answer (no refinement yet).

**Test results:** (Add when section is complete.)

---


## Section 12: Refinement decision

**Single goal:** Decide if the initial answer is lacking; set “refinement needed” (and optional reason) to trigger the refinement path (Section 13).

**Details:**
- Input: user question, **initial answer (Section 11)**, and **sub_qa (Section 9)**. Both the initial answer and sub_qa are required: we evaluate the initial answer and the per-sub-question results (answerable/unanswerable, verification) together. Output: refinement_needed: bool, optional reason. LLM or rule-based (e.g. “no relevant found”, low verification). Expose to next step only; no refinement decomposition or answer here.

**Tech:** LLM if used. No new packages. No Docker change.

**Files**

| File | Purpose |
|------|--------|
| New `src/backend/services/refinement_decision_service.py` or equivalent | should_refine(question, initial_answer, sub_qa) → (refinement_needed: bool, reason: str). |
| `src/backend/services/agent_service.py` | After initial answer, call refinement decision; if refinement_needed → Section 13; else return initial answer as final. |

**How to test:** Unit: initial answer “no relevant docs” → refinement_needed True; complete answer → False. Integration: weak initial answer → refinement path taken.

**Test results:** (Add when section is complete.)

---

## Section 13: Refinement decomposition

**Single goal:** Produce a new list of refined sub-questions that target gaps and unanswerable sub-questions. Run only when refinement_needed (Section 12). Refined sub-questions are then run through the full per-subquestion pipeline in Section 14.

**Details:**
- Input: user question, initial answer (Section 11), SubQuestionAnswer list (Section 9; with answerable/verification). Output: list of refined sub-questions. We do not re-ask the same sub-questions; the LLM uses the initial answer and sub_qa (including which were unanswerable) to generate gap-targeting sub-questions. No retrieval or synthesis here; output feeds Section 14.

**Tech:** Existing LLM. No new packages. No Docker change.

**Files**

| File | Purpose |
|------|--------|
| New `src/backend/services/refinement_decomposition_service.py` or equivalent | refine_subquestions(question, initial_answer, sub_qa) → list[str]. |
| `src/backend/services/agent_service.py` | When refinement_needed (Section 12), call refinement decomposition; pass refined sub-questions to Section 14. |

**How to test:** Unit: initial answer with gap + unanswerable sub-questions → refined sub-questions target gap. Integration: refinement_needed=True → refined sub-questions passed to next step.

**Test results:** (Add when section is complete.)

---

## Section 14: Refinement answer path

**Single goal:** Run the same per-subquestion pipeline (Sections 4–9) on the refined sub-questions from Section 13, then synthesize the refined final answer. When refinement was taken, this is the final output.

**Details:**
- Input: refined sub-questions (Section 13). Reuse the same pipeline as Section 10 (expand → search → validate → rerank → answer → check) for each refined sub-question in parallel. Output: refined answer (synthesizer combining refined sub-answers and optionally initial answer). response.output = refined answer when refinement was taken (optional initial_answer in metadata).

**Tech:** Reuse pipeline and LLM from Sections 4–11. No new dependencies. No Docker change.

**Files**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | On refinement path: call same parallel sub-question pipeline (Section 10) with refined sub-questions; synthesizer → refined answer; response.output = refined answer. |
| `src/backend/schemas/agent.py` (optional) | Optional response fields for initial_answer and refined_answer if both returned to client. |

**How to test:** Unit: mocks + refined sub-questions → pipeline invoked, refined answer non-empty. Integration: refinement_needed=True → final response.output is refined answer; sub_qa/metadata reflect refined sub-questions and answers.

**Test results:** (Add when section is complete.)

---
