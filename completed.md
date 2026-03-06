## Section 1: Add decomposition-only LLM call and prompt

**Onyx article:** Lesson 1 — "Agents are just prompts": planning is *completely isolated* from execution; use a specific system prompt and curate input so the planning task is well defined and simple.

**Single goal:** Add one new LLM call that takes user query + initial_search_context and returns a list of sub-questions. No flow tracking, write_todos, or task() in this call.

**Details:**
- In agent_service, after building initial_search_context and before invoking the coordinator, run a dedicated decomposition call.
- Input: user query + initial_search_context. Output: list of sub-questions only (e.g. JSON array or one-question-per-line).
- Add a dedicated system prompt (e.g. in coordinator.py as `_DECOMPOSITION_ONLY_PROMPT` or a small new module). This step produces the "plan"; Section 3 will consume it.

**Tech stack and dependencies**
- No new packages; one new LLM invoke path (same model as coordinator or env-configured).
- get_vector_store / build_initial_search_context unchanged.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/agent_service.py | Run decomposition-only step after initial_search_context is built; capture raw output for Section 2. |
| src/backend/agents/coordinator.py | Add _DECOMPOSITION_ONLY_PROMPT for the decomposition-only call. |

**How to test:** Run a query; in logs or trace confirm one LLM call returns only sub-questions (no task() or write_todos). Unit test: mock LLM returning a fixed list, assert agent_service captures it.

### Completion notes (March 6, 2026)
- Added `_DECOMPOSITION_ONLY_PROMPT` and exported prompt accessor via `agents`.
- Added `_run_decomposition_only_llm_call(...)` in `agent_service` and invoked it immediately after initial context construction and before coordinator invocation.
- Added runtime logging for decomposition-only output capture.
- Updated service unit test to mock decomposition call and assert capture.

### Useful logs
- `Runtime agent run start query=What is vector search? query_length=22`
- `Initial decomposition context built query=What is vector search? docs=0 k=5 score_threshold=None`
- `Decomposition-only LLM output captured output_length=26 output_preview=["What is vector search?"]`
- `Coordinator decomposition input prepared query=What is vector search? context_items=0`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`

### Tests run
- `docker compose exec backend uv run pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py` -> `16 passed`
- `docker compose exec backend uv run pytest tests/api -m smoke` -> `3 deselected / 0 selected`

---

## Section 2: Decomposition output format contract

**Onyx article:** Lesson 1 — Plan is the only context brought into the research phase; format must be consumable by the coordinator and _extract_sub_qa.

**Single goal:** Define and enforce the decomposition output format so the coordinator and _extract_sub_qa can consume it. Document the contract.

**Details:**
- Sub-questions must have trailing `?`, one concept per question. Format: list of strings (e.g. JSON array or one-per-line) matching _build_coordinator_input_message and _extract_sub_qa expectations.
- In agent_service: parse/validate decomposition LLM output into a list of sub-question strings; pass that list to the next phase (Section 3). If the LLM returns malformed output, normalize or fail clearly.
- Document the contract in coordinator.py (near _DECOMPOSITION_ONLY_PROMPT) or in docs/section-03: "Decomposition output is a list of sub-questions, each ending with ?, one concept per question."

**Tech stack and dependencies**
- No new packages; parsing/validation and docs only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/agent_service.py | Parse/validate decomposition output into list of sub-questions; pass to coordinator phase. |
| src/backend/agents/coordinator.py or docs/section-03 | Document decomposition output format contract. |

**How to test:** Unit test: mock LLM returning various formats (JSON, newline-separated); assert agent_service produces a list of strings with `?`. Run a query; confirm parsed list is passed to coordinator.

### Completion notes (March 6, 2026)
- Added `_parse_decomposition_output(...)` in `agent_service` with contract enforcement for JSON arrays and newline/bullet formats.
- Normalization now guarantees trailing `?`, removes duplicates, and falls back clearly to normalized main question on malformed/empty outputs.
- `run_runtime_agent(...)` now parses decomposition output and passes the normalized list into `_build_coordinator_input_message(...)`.
- Coordinator handoff message now includes `Normalized decomposition output (contract-compliant list of sub-questions)` for Section 3 consumption.
- Added contract documentation comment near `_DECOMPOSITION_ONLY_PROMPT` in `coordinator.py`.

### Useful logs
- `Decomposition-only LLM output captured output_length=2 output_preview=[]`
- `Decomposition output parsed sub_question_count=1 sub_questions=["What changed in NATO policy?"]`
- `Coordinator decomposition input prepared query=What changed in NATO policy? context_items=0 parsed_sub_questions=1`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- `Container agent-search-backend Restarting`

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py'` -> `20 passed`

---

## Section 3: Coordinator receives only sub-questions (no decomposition in same context)

**Onyx article:** Lesson 1 — Plan is the only context brought into the research phase; "contrast this with instructing the LLM to first generate a plan then immediately execute on it" (avoid that; we do decomposition then hand off).

**Single goal:** Coordinator receives only the list of sub-questions from Sections 1–2; it does not perform decomposition in the same context.

**Details:**
- Agent_service builds the coordinator input from the Section 2 sub-questions list only (e.g. a single HumanMessage listing them). Do not pass the full "Decomposition input" that asks the coordinator to derive sub-questions from context.
- Update _COORDINATOR_PROMPT: remove or narrow decomposition rules; state that sub-questions are provided and the coordinator must call write_todos, maintain the flow file, and delegate each via task(description=sub_question).
- _extract_sub_qa and the per-subquestion pipeline unchanged; only the input and coordinator role change.
- Update docs/section-03: note that decomposition is isolated in Sections 1–2.

**Tech stack and dependencies**
- No new packages; prompt and message-building only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/agent_service.py | Build coordinator message from sub-questions list (not _build_coordinator_input_message(query, context)). |
| src/backend/agents/coordinator.py | Update _COORDINATOR_PROMPT: no decomposition; receive sub-questions; write_todos, flow, task(description=sub_question). |
| docs/section-03-question-decomposition-informed-by-context.md | Note decomposition is done in a prior step (Sections 1–2). |

**How to test:** Run a query; confirm coordinator receives a message that lists sub-questions (not "derive sub-questions from context"). Confirm task() calls match that list. Extend test_agent_service / test_coordinator_agent as needed.

### Completion notes (March 6, 2026)
- Updated `agent_service._build_coordinator_input_message(...)` to accept only the normalized sub-question list and removed query/context decomposition payload from coordinator input.
- Updated coordinator handoff logging to `Coordinator sub-question input prepared ...` including delegated sub-question list for visibility.
- Updated `_COORDINATOR_PROMPT` so stage 2 consumes provided sub-questions and explicitly forbids same-context decomposition.
- Rewrote `docs/section-03-question-decomposition-informed-by-context.md` to document isolated decomposition handoff from Sections 1–2 into coordinator delegation.
- Updated backend tests (`test_agent_service`, `test_coordinator_agent`) to validate new coordinator input contract and prompt semantics.

### Useful logs
- `Runtime agent run start query=What is pgvector used for? query_length=26`
- `Decomposition output parsed sub_question_count=2 sub_questions=["What is pgvector?", "What are the use cases of pgvector?"]`
- `Coordinator sub-question input prepared parsed_sub_questions=2 sub_questions=["What is pgvector?", "What are the use cases of pgvector?"]`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- `docker compose ps` shows `db` healthy and `backend/frontend/chrome` up.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py'` -> `20 passed`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK`

---

## Section 4: Coordinator only delegates and gathers (no final answer synthesis)

**Onyx article:** Lesson 2 — "Deep frying is unhealthy": "The Orchestrator just gathers context. It doesn't meaningfully transform or reinterpret information"; orchestrator gathers, doesn't synthesize the final answer.

**Single goal:** The coordinator does not synthesize the final answer from subanswers; agent_service owns final answer generation via generate_initial_answer.

**Details:**
- In _COORDINATOR_PROMPT, remove or replace "After you have subanswers, use them to answer the main question with one concise answer." The coordinator only delegates via task() and gathers subagent responses.
- agent_service already uses generate_initial_answer(main_question, initial_search_context, sub_qa) for the API response; coordinator_output is only for logging. API response shape unchanged.
- If the framework expects a final assistant message from the coordinator, use a short summary like "Delegation complete; subanswers collected."

**Tech stack and dependencies**
- No new packages; prompt change in coordinator.py only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/agents/coordinator.py | Remove final-answer synthesis from _COORDINATOR_PROMPT; coordinator only delegates and reports completion. |

**How to test:** Run a query; confirm API response still comes from generate_initial_answer and shape is unchanged. Confirm coordinator's last message does not contain the main answer. test_agent_service assertions on RuntimeAgentRunResponse still pass.

### Completion notes (March 6, 2026)
- Updated `_COORDINATOR_PROMPT` flow stages so coordinator ends at delegation/gather completion handoff and no longer claims ownership of final answer synthesis.
- Replaced synthesis instruction with explicit completion behavior:
  - coordinator only delegates and gathers subagent outputs,
  - must not synthesize the final main-question answer,
  - must end with a short status message (`Delegation complete; subanswers collected.`).
- Added an explicit flow-file sequencing guardrail in prompt instructions: call `read_file` first, create with `write_file` if missing, then use `edit_file`.
- Updated `src/backend/tests/agents/test_coordinator_agent.py` expectations to assert delegate/gather-only completion semantics.

### Useful logs
- `Coordinator raw output captured output_length=42 output_preview=Delegation complete; subanswers collected.`
- `Initial answer generation start question_len=17 context_items=0 sub_qa_count=1`
- `Initial answer generation complete via LLM answer_len=373 model=gpt-4.1-mini`
- `Runtime agent run complete output_length=523 output_preview=Pgvector is a PostgreSQL extension ...`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- `docker compose ps` showed `backend` up, `db` healthy, `frontend` up after backend restart.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run python -m pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py'` -> `20 passed`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector?"}'` -> `200 OK` with unchanged `RuntimeAgentRunResponse` shape (`main_question`, `sub_qa`, `output`)

---

## Section 5: Retriever tool citation contract

**Onyx article:** Lesson 4 — "Tool Design": return results and let the model choose and cite; preserve identity so "facts don't become disconnected from their sources."

**Single goal:** Ensure the retriever tool returns a stable numbered format (index, title, source, content) and document that format as the citation contract.

**Details:**
- retriever_tool._format_results should return lines like "1. title=… source=… content=…". Confirm this is stable; document index (1, 2, 3…) is the citation key.
- Add a docstring or comment in retriever_tool.py: the numbered format is the citation contract for RAG; downstream (subanswer, verification, UI) may cite by [1], [2] etc.
- No behavior change required if format is already correct; otherwise small tweaks only.

**Tech stack and dependencies**
- No new packages; retriever_tool.py only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/tools/retriever_tool.py | Confirm _format_results keeps index/title/source; add docstring or comment on citation contract. |

**How to test:** Run retriever; inspect output for "1. title=… source=…". Read docstring for citation contract.

### Completion notes (March 6, 2026)
- Added `_format_results(...)` docstring in `src/backend/tools/retriever_tool.py` that explicitly defines the stable citation contract shape:
  - `{index}. title={title} source={source} content={content}`
  - 1-based index is the canonical citation key for downstream references like `[1]`, `[2]`.
- Extended retriever runtime log payload to include `citation_contract=index.title.source.content` for operational visibility.
- Updated `src/backend/tests/tools/test_retriever_tool.py` to assert citation-contract log emission.

### Useful logs
- `Retriever tool search_database query='strategic shipping' ... result_count=2 citation_contract=index.title.source.content`
- `docker compose ps` shows `backend` up, `frontend` up, `db` healthy.
- `INFO: ... "GET /api/health HTTP/1.1" 200 OK`
- Backend restart and log check completed after code edits.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run pytest tests/tools/test_retriever_tool.py'` -> `3 passed`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`

---

## Section 6: Pipeline preserves document identity (validation and rerank)

**Onyx article:** Lesson 4 — Tool design: preserve document identity through the pipeline so verification and citations can use the same structure.

**Single goal:** Ensure document_validation_service and agent_service preserve the numbered title/source/content format through the pipeline; no step drops indices or sources.

**Details:**
- format_retrieved_documents (document_validation_service) and any format_retrieved_documents in the reranker path must not drop title/source. Output same shape as retriever_tool (numbered lines).
- agent_service._format_retrieved_documents_for_pipeline: ensure same shape for refinement path. SubQuestionAnswer.sub_answer and reranked output should retain numbered document list where needed for verification.

**Tech stack and dependencies**
- No new packages; document_validation_service and agent_service formatting only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/document_validation_service.py | Ensure format_retrieved_documents preserves numbered format. |
| src/backend/services/agent_service.py | _format_retrieved_documents_for_pipeline: same shape for refinement path. |

**How to test:** Run a query; inspect sub_qa[].sub_answer and reranked output for numbered lines with title= and source=.

### Completion notes (March 6, 2026)
- Updated `src/backend/services/agent_service.py` to reuse `document_validation_service.format_retrieved_documents(...)` in `_format_retrieved_documents_for_pipeline(...)` via normalized `RetrievedDocument` instances, so refinement/retrieval formatting now shares the same citation contract serializer.
- Added contract visibility logging in pipeline formatting and per-stage validation/rerank logs:
  - `Pipeline retrieval formatter emitted citation contract ...`
  - `Per-subquestion document validation ... contract_lines=...`
  - `Per-subquestion reranking ... contract_lines=...`
- Added `format_retrieved_documents(...)` citation-contract docstring and formatter logs in `src/backend/services/document_validation_service.py`.
- Added tests to prove identity contract preservation:
  - `test_format_retrieved_documents_preserves_numbered_identity_contract`
  - `test_format_retrieved_documents_for_pipeline_preserves_citation_contract_shape`

### Useful logs
- `Runtime agent run start query=What changed in NATO policy? query_length=28`
- `Retriever tool search_database ... result_count=0 citation_contract=index.title.source.content`
- `Per-subquestion document validation sub_question=What changed in NATO policy? docs_before=0 docs_after=n/a rejected=n/a contract_lines=0`
- `Per-subquestion reranking skipped; no parseable retrieved docs sub_question=What changed in NATO policy?`
- `Refinement retrieval complete count=6`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- `docker compose ps` shows `db` healthy and `backend/frontend/chrome` up.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run pytest tests/services/test_document_validation_service.py tests/services/test_agent_service.py'` -> `22 passed`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What changed in NATO policy?"}'` -> `200 OK`

---

## Section 7: Subanswer service — full document list and citation instructions (no summarization)

**Onyx article:** Lesson 4 — "use LLMs to summarize web results… handicaps better models"; keep full document list for citation and verification.

**Single goal:** subanswer_service receives the full document list and is instructed to cite by index [1], [2]; no summarization that drops source identity.

**Details:**
- Audit subanswer_service.generate_subanswer: input is reranked_retrieved_output (string). Ensure the prompt does not ask the model to "summarize the documents" in a way that drops indices/sources. Prefer "use the documents below to answer; cite by [1], [2]."
- The model must have access to the full numbered list and produce answers that preserve citation ability.

**Tech stack and dependencies**
- No new packages; prompt/logic in subanswer_service only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/subanswer_service.py | Ensure input to the model is the full document list; answer format preserves citation ability; no summarization that drops sources. |

**How to test:** Run a query; inspect subanswer content for citation-like references [1], [2]. Confirm sub_answer and reranked output retain numbered list for verification.

### Completion notes (March 6, 2026)
- Updated `src/backend/services/subanswer_service.py` to pass the full parsed reranked list into prompt context using stable rank keys (`[rank] title=... source=... content=...`) instead of truncating context.
- Reworked subanswer prompt instructions to explicitly require citation-by-index (`[1]`, `[2]`) and forbid evidence-list summarization that drops source identity.
- Added subanswer visibility logs for parsed document count, context line count, and citation reference count detected in successful LLM output.
- Updated `src/backend/tests/services/test_subanswer_service.py` with:
  - citation instruction assertion in prompt,
  - full-list prompt coverage assertion (including later-ranked docs).

### Useful logs
- `Subanswer generation parsed reranked docs sub_question=recent changes to NATO policy? doc_count=0`
- `Subanswer generation skipped; no parseable reranked docs sub_question=recent changes to NATO policy?`
- `Per-subquestion subanswer generated sub_question=What is NATO policy? generated_len=49`
- `Runtime agent run complete output_length=273 ...`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- `docker compose ps` showed `backend` up, `frontend` up, and `db` healthy.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run python -m pytest tests/services/test_subanswer_service.py tests/services/test_agent_service.py'` -> `22 passed`
- `curl -sS -i http://localhost:8000/api/health` -> `HTTP/1.1 200 OK`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What changed in NATO policy?"}'` -> `200 OK` with `RuntimeAgentRunResponse` payload

---

## Section 8: Initial answer service — source info and no summarization

**Onyx article:** Lesson 4 — Same as Section 7; keep ground truth for the final answer.

**Single goal:** initial_answer_service uses sub_qa and context with source info; no summarization that drops sources.

**Details:**
- Audit initial_answer_service: it consumes sub_qa and context for generate_initial_answer. Ensure it uses source info (e.g. sub_answer text that may include [1], [2]) and does not instruct the model to summarize in a way that drops citation links.
- API response shape unchanged; only prompt/logic so that final answer can cite or reference sources where applicable.

**Tech stack and dependencies**
- No new packages; prompt/logic in initial_answer_service only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/services/initial_answer_service.py | Use sub_qa and context with source info; no summarization that drops sources. |

**How to test:** Run a query; inspect initial answer for citation-like references or preserved source structure. Confirm API response shape unchanged.

### Completion notes (March 6, 2026)
- Updated `src/backend/services/initial_answer_service.py` prompt requirements to preserve citation markers (`[1]`, `[2]`), avoid uncited summarization, and explicitly reference context `source` fields when used.
- Added runtime visibility logs in initial answer generation:
  - fallback path selection and citation-ref counts,
  - prepared evidence summary (answerable sub_qa count, citation refs, context source count),
  - final LLM output citation/source attribution counts.
- Added citation helper and logging-safe counters used across fallback and final-answer stages.
- Extended `src/backend/tests/services/test_initial_answer_service.py`:
  - fallback test now asserts citation markers are preserved,
  - new prompt-contract test asserts citation-preservation/non-summarization instructions are sent to the LLM call.

### Useful logs
- `Initial answer fallback path selected source=any_subanswers count=6 citation_refs=0`
- `Initial answer evidence prepared answerable_sub_qa=0 total_sub_qa=6 subanswer_citation_refs=0 context_sources=0`
- `Initial answer generation complete via LLM answer_len=238 model=gpt-4.1-mini citation_refs=0 source_attributions=0`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- `docker compose logs --since=10m frontend` confirms Vite dev server healthy on `http://localhost:5173/`
- `docker compose logs --since=10m db` confirms Postgres ready for connections.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run python -m pytest tests/services/test_initial_answer_service.py tests/services/test_agent_service.py'` -> `22 passed`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector and why is it used in RAG systems?"}'` -> `200 OK` with unchanged `RuntimeAgentRunResponse` shape (`main_question`, `sub_qa`, `output`)

---

## Section 9: Co-locate RAG subagent tool instructions with tool usage in prompt

**Onyx article:** Lesson 3, Rule 1 — "Co-locate instructions": keep tool-use instructions adjacent to the tool definitions so the model doesn't "hop" over unrelated text.

**Single goal:** In the RAG subagent, put all retriever-usage and response-format instructions in one block adjacent to the tool description.

**Details:**
- Only the RAG subagent has the retriever (search_database). Apply co-location in _RAG_SUBAGENT_PROMPT in coordinator.py.
- Group in one place: (1) use the retriever with query and expanded_query, (2) if relevant docs use them to answer else "nothing relevant found", (3) respond in format "{subquestion}: {answer}". Remove or relocate any other instructions that sit between these and the tool.

**Tech stack and dependencies**
- No new packages; prompt string changes in coordinator.py only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/agents/coordinator.py | Restructure _RAG_SUBAGENT_PROMPT so retriever usage and response-format instructions are in a single block. |

**How to test:** Inspect the RAG subagent system prompt (create_coordinator_agent or logs); confirm tool-use and response-format instructions are adjacent with no unrelated sentences between them.

### Completion notes (March 6, 2026)
- Reworked `src/backend/agents/coordinator.py` `_RAG_SUBAGENT_PROMPT` into one contiguous `Retriever tool contract (search_database)` block that co-locates all required behavior:
  - expanded query construction,
  - `search_database` call shape (`query` + `expanded_query`),
  - relevant-docs vs `nothing relevant found` handling,
  - strict response format `{subquestion}: {answer}`.
- Removed scattered/duplicative phrasing so retriever usage and output formatting are now adjacent with no unrelated instructions in-between.
- Added coordinator construction log for runtime visibility:
  - `RAG subagent prompt configured subagent=rag_retriever tool=search_database contract=co_located_retriever_and_response_format`
- Updated `src/backend/tests/agents/test_coordinator_agent.py` assertions to validate the new co-located prompt contract and visibility log.

### Useful logs
- `HTTP/1.1 200 OK` on `GET /api/health` after backend restart.
- Backend runtime includes expected startup and migration logs after clean rebuild.
- Prompt visibility log (validated in tests):
  - `RAG subagent prompt configured subagent=rag_retriever tool=search_database contract=co_located_retriever_and_response_format`
- Frontend logs show Vite healthy on `http://localhost:5173/`.
- DB logs show PostgreSQL ready for connections.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run pytest tests/agents/test_coordinator_agent.py'` -> `2 passed`
- `curl -sS -i http://localhost:8000/api/health` -> `HTTP/1.1 200 OK`
- `docker compose logs --tail=120 backend` / `--tail=60 frontend` / `--tail=80 db` reviewed; no blocking runtime errors.

---

## Section 10: Add RAG subagent end-of-context reminder

**Onyx article:** Lesson 3, Rule 3 — "Use Reminders": inject reminders at the very end of context; the LLM attends strongly to the most recent tokens; keep reminders short and coherent (one thing).

**Single goal:** Append a short end-of-context reminder to the RAG subagent so it reliably follows the required response format and citation behavior.

**Details:**
- Add a reminder at the end of the subagent's context (trailing message or suffix if the framework supports it). Reminder: one thing only, e.g. "Respond in the format: {subquestion}: {answer}. Use document content to support your answer."
- If the framework does not support per-subagent end-of-context injection, add the reminder as the final sentence of _RAG_SUBAGENT_PROMPT.

**Tech stack and dependencies**
- No new packages; prompt or deep-agents subagent config only.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/agents/coordinator.py | Add reminder text to RAG subagent (end of _RAG_SUBAGENT_PROMPT or via framework hook if available). |

**How to test:** Run queries; inspect subagent responses (_extract_sub_qa / sub_agent_response). Confirm format "{subquestion}: {answer}" (or citation) appears consistently.

### Completion notes (March 6, 2026)
- Updated `src/backend/agents/coordinator.py` `_RAG_SUBAGENT_PROMPT` by appending a final end-of-context reminder sentence (at the very end of the prompt) that reinforces one coherent requirement: return `{subquestion}: {answer}` grounded in retrieved docs with citation markers like `[1]` when supported.
- Added runtime visibility logging for this section by extending the prompt-configuration log with:
  - `reminder=end_of_context_format_and_citation`
- Updated `src/backend/tests/agents/test_coordinator_agent.py` to assert:
  - the reminder text exists,
  - it is the final prompt sentence (`endswith(...)`),
  - prompt visibility log contains the reminder marker.

### Useful logs
- `RAG subagent prompt configured subagent=rag_retriever tool=search_database contract=co_located_retriever_and_response_format reminder=end_of_context_format_and_citation`
- `Agent message[4] tool_result tool=task content_len=41 content_preview=What is pgvector?: nothing relevant found`
- `Agent message[5] tool_result tool=task content_len=54 content_preview=What are the uses of pgvector: Nothing relevant found.`
- `INFO: ... "GET /api/health HTTP/1.1" 200 OK`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- Frontend logs show Vite ready on `http://localhost:5173/`; DB logs show PostgreSQL ready for connections.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run pytest tests/agents/test_coordinator_agent.py'` -> `2 passed`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> `200 OK` with runtime `sub_qa` output captured

---

## Section 11: Simplify RAG subagent prompt

**Onyx article:** Lesson 3, Rule 2 — "Don't add too many instructions": give high-level tasks; too many "in this case do X, but if Y do Z" causes loss of track; prefer fewer, high-level instructions.

**Single goal:** Reduce conditional and multi-branch instructions in _RAG_SUBAGENT_PROMPT to one clear flow; keep co-location (Section 9) and reminder (Section 10).

**Details:**
- Audit _RAG_SUBAGENT_PROMPT: remove or consolidate "If it is not atomic break down further", "Generate one expanded query", "If no useful expansion…", "If retriever gives relevant docs…", "If it does not…". Single flow: receive question → expand query (or use as-is) → call retriever → answer from docs or "nothing relevant found" → respond "{subquestion}: {answer}".
- Keep co-location and end-of-context reminder; remove redundant or rarely applicable branches.

**Tech stack and dependencies**
- No new packages; prompt text only in coordinator.py.

**Files and purpose**

| File | Purpose |
|------|--------|
| src/backend/agents/coordinator.py | Simplify _RAG_SUBAGENT_PROMPT: one clear flow, fewer if/else instructions. |

**How to test:** Run queries; confirm subagent still calls search_database with query/expanded_query and returns answers in the expected format. Check sub_agent_response and sub_answer in RuntimeAgentRunResponse.

**Test results:** Completed on March 6, 2026.
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run pytest tests/agents/test_coordinator_agent.py'` -> 2 passed.
- `curl -sS -m 30 -w '\n%{http_code}\n' -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> 200 OK.
- Live backend logs include:
  - `RAG subagent prompt configured subagent=rag_retriever tool=search_database contract=co_located_retriever_and_response_format flow=simplified_single_path reminder=end_of_context_format_and_citation`
  - `tool_result tool=task content_preview=What is pgvector?: nothing relevant found`
  - `POST /api/agents/run HTTP/1.1" 200 OK`

---

## Section S1: Add script to export OpenAPI from FastAPI app to a file

**Single goal:** Add a script that loads the FastAPI app, calls `app.openapi()`, and writes the OpenAPI spec to a file (no running server required).

**Details:**
- Script must be runnable from repo (e.g. `python scripts/export_openapi.py` or from backend dir).
- Output path may be configurable or fixed; schema must include all mounted routes (`/api/health`, `/api/agents/*`, `/api/internal-data/*`).

**Tech stack and dependencies**
- FastAPI (existing). Optional: `pyyaml` if writing YAML; otherwise JSON is fine.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/scripts/export_openapi.py` | Loads app, calls `app.openapi()`, writes spec to a file. |

**How to test:** Run the script; confirm the output file exists and contains OpenAPI 3.x paths and components.

### Completion notes (March 6, 2026)
- Added `scripts/export_openapi.py` to load FastAPI app from `src/backend/main.py`, call `app.openapi()`, and export JSON schema without starting the server.
- Added configurable output path via `--output` (default `openapi.json`) with path normalization to repo root.
- Added INFO log visibility in script output: exported file path, OpenAPI version, total path count, and sample exported routes.
- Confirmed exported schema contains required API routes and components.

### Useful logs
- `2026-03-06 17:29:33,061 INFO scripts.export_openapi: OpenAPI export complete output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json openapi_version=3.1.0 path_count=5 sample_paths=['/api/agents/run', '/api/health', '/api/internal-data/load', '/api/internal-data/wiki-sources', '/api/internal-data/wipe']`
- `docker compose restart` showed all services restarted successfully (`backend`, `frontend`, `db`, `chrome`).
- Backend logs after restart:
  - `INFO: Uvicorn running on http://0.0.0.0:8000`
  - `INFO: Application startup complete.`
- Frontend logs after restart:
  - `VITE v5.4.21 ready in ...`
  - `Local: http://localhost:5173/`
- DB logs after restart:
  - `database system is ready to accept connections`
- Health check after restart:
  - `HTTP/1.1 200 OK` for `GET /api/health`.

### Tests run
- `uv run --project src/backend python scripts/export_openapi.py` -> pass, `openapi.json` generated.
- `python - <<'PY' ...` schema verification -> pass (`openapi_version: 3.1.0`, `has_components: True`, all required `/api/*` paths present).
- `curl -sS -i http://localhost:8000/api/health` -> `HTTP/1.1 200 OK`.

---

## Section S2: Canonical OpenAPI spec file path and format

**Single goal:** Define a single canonical path and format for the OpenAPI spec file in the repo so all tooling uses the same input.

**Details:**
- Spec file lives at one path (e.g. `agent-search-api.yaml` or `openapi.yaml` at repo root or in a designated folder).
- Export script (S1) must write to this path. YAML preferred for readability; JSON acceptable.

**Tech stack and dependencies**
- None new; export script from S1.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/agent-search-api.yaml` (or chosen path) | Canonical OpenAPI 3.x spec; produced by export script. |

**How to test:** Run export script; confirm file exists at canonical path. Optionally validate with `openapi-generator validate -i <path>` or online validator.

### Completion notes (March 6, 2026)
- Defined canonical OpenAPI spec artifact as `openapi.json` at repo root (OpenAPI 3.x JSON).
- Updated `scripts/export_openapi.py` with explicit `CANONICAL_OPENAPI_REL_PATH` and canonical-path-aware logging; script now warns if `--output` overrides canonical location.
- Updated `README.md` with a dedicated OpenAPI section documenting canonical path/format and the standard export command used by tooling.
- Re-exported schema to canonical path and verified required endpoints/components are present.

### Useful logs
- `2026-03-06 17:31:36,049 INFO scripts.export_openapi: OpenAPI export complete output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json canonical_output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json openapi_version=3.1.0 path_count=5 sample_paths=['/api/agents/run', '/api/health', '/api/internal-data/load', '/api/internal-data/wiki-sources', '/api/internal-data/wipe']`
- `Container agent-search-frontend Restarting`
- `Container agent-search-backend Restarting`
- `Container agent-search-db Restarting`
- Backend startup logs after restart:
  - `INFO: Uvicorn running on http://0.0.0.0:8000`
  - `INFO: Application startup complete.`
- Frontend startup logs after restart:
  - `VITE v5.4.21 ready in 620 ms`
  - `Local: http://localhost:5173/`
- DB restart logs after restart:
  - `database system is ready to accept connections`
- Health check verification:
  - `{"status":"ok"}`

### Tests run
- `uv run --project src/backend python scripts/export_openapi.py` -> pass; canonical `openapi.json` regenerated.
- `python - <<'PY' ...` OpenAPI verification -> pass (`openapi_version 3.1.0`, `path_count 5`, required paths present, `components` present).
- `docker compose ps` -> backend/frontend up, db healthy.
- `docker compose restart backend frontend db` -> pass.
- `docker compose logs --no-color --tail=80 backend frontend db` -> inspected; services healthy after restart.
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`.

---

## Section S3: Validate exported OpenAPI spec

**Single goal:** Add a repeatable way to validate the canonical OpenAPI spec (syntax and structure).

**Details:**
- Use OpenAPI Generator’s validate command (e.g. via Docker) or a documented validator; no new app code required.
- Document the validation command in README or script comment.

**Tech stack and dependencies**
- Docker (for `openapi-generator validate`) or another validator; no new app dependencies.

**Files and purpose**

| File | Purpose |
|------|--------|
| Optional: one-line in `scripts/validate_openapi.sh` or in docs | Runs validation against canonical spec file. |

**How to test:** Run validation; fix spec or export if it fails until validation passes.

**Test results:** Completed on March 6, 2026.
- `uv run --project src/backend python scripts/export_openapi.py` -> refreshed canonical spec at `openapi.json` with OpenAPI `3.1.0`.
- `./scripts/validate_openapi.sh` -> OpenAPI Generator validation passed (`No validation issues detected.`).
- `docker compose restart db backend frontend` -> all required services restarted cleanly.
- `docker compose ps` -> `db` healthy; `backend` and `frontend` up.
- `docker compose logs --tail=120 backend`, `docker compose logs --tail=120 frontend`, and `docker compose logs --tail=120 db` reviewed with no startup/runtime errors after restart.

### Completion notes (March 6, 2026)
- Added repeatable validator script at `scripts/validate_openapi.sh` using `openapitools/openapi-generator-cli` Docker image.
- Added README documentation for both the scripted validation command and the direct Docker equivalent.
- Validator script emits timestamped start/pass log lines for operational visibility.

### Useful logs
- `2026-03-06 17:33:52,214 INFO scripts.export_openapi: OpenAPI export complete output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json canonical_output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json openapi_version=3.1.0 path_count=5 sample_paths=['/api/agents/run', '/api/health', '/api/internal-data/load', '/api/internal-data/wiki-sources', '/api/internal-data/wipe']`
- `2026-03-06T22:33:58Z INFO validate_openapi: starting validation spec=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json`
- `Validating spec (/local/openapi.json)`
- `No validation issues detected.`
- `2026-03-06T22:34:21Z INFO validate_openapi: validation passed spec=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json`
- Backend logs: `Application startup complete.` and `GET /api/health ... 200 OK` after restart.
- Frontend logs: `VITE v5.4.21 ready` and `Local: http://localhost:5173/` after restart.
- DB logs after restart end in: `database system is ready to accept connections`.

---

## Section S4: Docker command for OpenAPI Generator (Python client)

**Single goal:** Document the exact `docker run` command that generates the Python SDK from the canonical spec, with no local generator install.

**Details:**
- Use image `openapitools/openapi-generator-cli`; mount repo (or spec dir) so `-i` and `-o` point at host paths.
- Output to a dedicated directory (e.g. `sdk/python/` or `agent-search-python-sdk/`). No script yet; command only.

**Tech stack and dependencies**
- Docker.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/README.md` or `agent-search/sdk/README.md` | Document the one-line `docker run ... generate -i ... -g python -o ...` command. |

**How to test:** Run the documented command; confirm output directory exists and contains generated Python client (e.g. `api/`, `models/`, `configuration.py`).

### Completion notes (March 6, 2026)
- Added the exact Docker OpenAPI Generator command to `README.md` under the OpenAPI section.
- Chosen SDK output path is `sdk/python` (dedicated generated-client directory).
- Included `-u "$(id -u):$(id -g)"` in the command so generated files are owned by the current host user.
- Verified the command generates a complete Python SDK layout from canonical `openapi.json`.

### Useful logs
- `2026-03-06 17:36:06,716 INFO scripts.export_openapi: OpenAPI export complete output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json canonical_output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json openapi_version=3.1.0 path_count=5 sample_paths=['/api/agents/run', '/api/health', '/api/internal-data/load', '/api/internal-data/wiki-sources', '/api/internal-data/wipe']`
- OpenAPI Generator output includes:
  - `OpenAPI Generator: python (client)`
  - `writing file /local/sdk/python/openapi_client/api/agents_api.py`
  - `writing file /local/sdk/python/openapi_client/models/runtime_agent_run_response.py`
  - `writing file /local/sdk/python/openapi_client/configuration.py`
- Backend logs after restart include `Application startup complete.` and `GET /api/health HTTP/1.1" 200 OK`.
- Frontend logs after restart include `VITE v5.4.21 ready` and `Local: http://localhost:5173/`.
- DB logs after restart end with `database system is ready to accept connections`.
- `docker compose ps` after restart:
  - `agent-search-db ... Up ... (healthy)`
  - `agent-search-backend ... Up`
  - `agent-search-frontend ... Up`

### Tests run
- `uv run --project src/backend python scripts/export_openapi.py` -> pass; refreshed `openapi.json`.
- `docker run --rm -u "$(id -u):$(id -g)" -v "$(pwd):/local" openapitools/openapi-generator-cli generate -i /local/openapi.json -g python -o /local/sdk/python` -> pass; SDK generated.
- `ls -la sdk/python` and `rg --files sdk/python` -> pass; confirmed presence of `openapi_client/api`, `openapi_client/models`, and `openapi_client/configuration.py`.
- `docker compose restart db backend frontend` -> pass.
- `docker compose logs --tail=120 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed; no blocking errors.
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`.

---

## Section S5: Generate-SDK shell script

**Single goal:** Add a shell script that runs the OpenAPI Generator Docker command so SDK generation is a single invocation.

**Details:**
- Script takes no args (or optional spec path / output path); uses canonical spec path and output dir from S2 and S4.
- Must be runnable from repo root or a documented cwd.

**Tech stack and dependencies**
- Docker; no new pip/npm deps.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/scripts/generate_sdk.sh` | Invokes `docker run ... openapi-generator-cli generate` with correct `-i`, `-g python`, `-o`. |

**How to test:** Run `./scripts/generate_sdk.sh`; confirm SDK output directory is created/updated with generated code.

### Completion notes (March 6, 2026)
- Added `scripts/generate_sdk.sh` as an executable one-command SDK generator with canonical defaults (`openapi.json` -> `sdk/python`) and optional path overrides.
- Added timestamped script logs for start/success/failure visibility, including explicit missing-spec guidance.
- Updated `README.md` OpenAPI section to document the single-command path: `./scripts/generate_sdk.sh`.
- Re-exported OpenAPI and regenerated Python SDK using the new script.

### Useful logs
- `2026-03-06T22:38:27Z INFO generate_sdk: starting image=openapitools/openapi-generator-cli lang=python spec=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json output=/Users/nickbohm/Desktop/worktree/agent-search/sdk/python`
- `OpenAPI Generator: python (client)`
- `writing file /local/sdk/python/openapi_client/api/agents_api.py`
- `writing file /local/sdk/python/openapi_client/configuration.py`
- `2026-03-06T22:38:32Z INFO generate_sdk: generation complete spec=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json output=/Users/nickbohm/Desktop/worktree/agent-search/sdk/python`
- `docker compose restart` restarted `backend`, `frontend`, `db`, and `chrome`.
- `docker compose ps` confirms `backend` up, `frontend` up, `chrome` up, and `db` healthy.
- Runtime logs reviewed with healthy startup lines:
  - backend: `Application startup complete.`
  - frontend: `VITE v5.4.21 ready`
  - db: `database system is ready to accept connections`
  - chrome: `Running on port 3000`
- Health endpoint check: `{"status":"ok"}` from `GET /api/health`.

### Tests run
- `uv run --project src/backend python scripts/export_openapi.py` -> pass.
- `./scripts/generate_sdk.sh` -> pass.
- `docker compose restart` -> pass.
- `docker compose ps` -> pass (`db` healthy; `backend`/`frontend`/`chrome` up).
- `docker compose logs --tail=140` -> reviewed for all running containers; no blocking errors.
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`.

---

## Section S6: SDK output location and repo policy

**Single goal:** Decide where the generated SDK lives in the repo and whether it is committed or gitignored.

**Details:**
- One chosen path (e.g. `sdk/python/` or `agent-search-python-sdk/`). Document in README or sdk/README.
- Either add that path to `.gitignore` (regenerate only) or commit generated files; document the choice.

**Tech stack and dependencies**
- None.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/.gitignore` and/or `agent-search/sdk/README.md` | Ignore or commit policy for generated SDK directory; document location. |

**How to test:** Run generate script; confirm output is at the documented path; confirm git state matches policy.

### Completion notes (March 6, 2026)
- Documented canonical SDK location and repo policy in `README.md` under OpenAPI: generated Python SDK output path is `sdk/python` and generated files are committed to git.
- Added `sdk/README.md` with SDK directory guidance, canonical source spec (`openapi.json`), generation command (`./scripts/generate_sdk.sh`), and explicit committed-artifact policy.
- Added policy note to `.gitignore` clarifying `sdk/python` is intentionally not ignored.
- Re-exported OpenAPI and regenerated SDK to verify location and policy alignment.

### Useful logs
- OpenAPI export log:
  - `2026-03-06 17:40:45,689 INFO scripts.export_openapi: OpenAPI export complete output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json canonical_output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json openapi_version=3.1.0 path_count=5 sample_paths=['/api/agents/run', '/api/health', '/api/internal-data/load', '/api/internal-data/wiki-sources', '/api/internal-data/wipe']`
- SDK generation logs:
  - `2026-03-06T22:40:31Z INFO generate_sdk: starting image=openapitools/openapi-generator-cli lang=python spec=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json output=/Users/nickbohm/Desktop/worktree/agent-search/sdk/python`
  - `OpenAPI Generator: python (client)`
  - `writing file /local/sdk/python/openapi_client/api/agents_api.py`
  - `writing file /local/sdk/python/openapi_client/configuration.py`
  - `2026-03-06T22:40:45Z INFO generate_sdk: generation complete spec=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json output=/Users/nickbohm/Desktop/worktree/agent-search/sdk/python`
- Container restart and runtime logs:
  - `docker compose restart db backend frontend` restarted all required app services successfully.
  - Backend logs include `Uvicorn running on http://0.0.0.0:8000` and `Application startup complete.`
  - Frontend logs include `VITE v5.4.21 ready` and `Local: http://localhost:5173/`.
  - DB logs include `database system is ready to accept connections`.
  - Initial health probe during restart returned transient `curl: (56) Recv failure: Connection reset by peer`; follow-up health check succeeded once services stabilized.

### Tests run
- `uv run --project src/backend python scripts/export_openapi.py` -> pass.
- `./scripts/generate_sdk.sh` -> pass (regenerated `sdk/python`).
- `test -d sdk/python && ls -la sdk/python` -> pass (output present at documented path).
- `git check-ignore -v sdk/python` and `git check-ignore -v sdk/python/README.md` -> pass (no ignore rule applies).
- `git ls-files sdk/python` -> pass (generated SDK files are tracked, matching committed policy).
- `docker compose restart db backend frontend` -> pass.
- `docker compose ps` -> pass (`db` healthy; `backend` and `frontend` up).
- `docker compose logs --tail=140 backend`, `docker compose logs --tail=140 frontend`, `docker compose logs --tail=140 db` -> reviewed; no blocking startup/runtime errors.
- `curl -sS -i http://localhost:8000/api/health` -> pass (`HTTP/1.1 200 OK`, `{"status":"ok"}`).

## Section S7: SDK install and usage documentation

**Single goal:** Document how to install the generated SDK and call one endpoint (e.g. health or agents run).

**Details:**
- Install steps (e.g. `pip install -e sdk/python` or from generated folder).
- Minimal code example: import client, set base URL, call one method. No new code deliverable; docs only.

**Tech stack and dependencies**
- Generated SDK’s own dependencies only.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/sdk/README.md` or main `README.md` | Install instructions and minimal usage example (copy-pasteable). |

**How to test:** Follow the doc in a clean venv; confirm install and one successful call (against running API or mock).

### Completion notes (March 6, 2026)
- Updated `sdk/README.md` with copy-pasteable SDK installation instructions using a clean virtual environment and editable install from `sdk/python`.
- Added minimal runnable usage examples for:
  - health endpoint (`DefaultApi.health_api_health_get`),
  - agents run endpoint (`AgentsApi.run_agent_api_agents_run_post`).
- Documented configurable base URL via `AGENT_SEARCH_BASE_URL` (default `http://localhost:8000`).
- Validated docs by executing the install flow and running a live health call through the generated SDK.

### Useful logs
- Virtualenv install output:
  - `Successfully installed ... openapi_client-1.0.0 ...`
- SDK runtime validation output:
  - `HEALTH_RESPONSE {'status': 'ok'}`
- Container restart output:
  - `Container agent-search-frontend Restarting`
  - `Container agent-search-backend Restarting`
  - `Container agent-search-db Restarting`
- `docker compose ps` after restart:
  - `agent-search-db ... Up ... (healthy)`
  - `agent-search-backend ... Up`
  - `agent-search-frontend ... Up`
- Backend logs after restart include:
  - `Uvicorn running on http://0.0.0.0:8000`
  - `Application startup complete.`
- Frontend logs after restart include:
  - `VITE v5.4.21 ready`
  - `Local: http://localhost:5173/`
- DB logs after restart include:
  - `database system is ready to accept connections`
- Post-restart health check:
  - `HTTP/1.1 200 OK`
  - `{"status":"ok"}`

### Tests run
- `docker compose up -d db backend frontend` -> pass.
- `python3 -m venv .venv-sdk-s7` -> pass.
- `source .venv-sdk-s7/bin/activate && pip install --upgrade pip && pip install -e sdk/python` -> pass.
- `AGENT_SEARCH_BASE_URL=http://localhost:8000 python - <<'PY' ... DefaultApi.health_api_health_get() ... PY` -> pass (`HEALTH_RESPONSE {'status': 'ok'}`).
- `docker compose restart db backend frontend` -> pass.
- `docker compose ps` -> pass (`db` healthy; `backend` and `frontend` up).
- `docker compose logs --no-color --tail=140 backend`, `frontend`, `db` -> reviewed; no blocking errors.
- `curl -sS -i http://localhost:8000/api/health` -> pass (`HTTP/1.1 200 OK`, `{"status":"ok"}`).

---

## Section S8: Minimal runnable example script using generated SDK

**Single goal:** Add one runnable example script that uses the generated client to call the API.

**Details:**
- Single file (e.g. `sdk/examples/run_health.py` or `sdk/examples/run_agent.py`); uses generated client; base URL configurable via env or arg.
- No new libraries; only the generated SDK.

**Tech stack and dependencies**
- Generated SDK from S5.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/sdk/examples/run_health.py` (or similar) | Calls one endpoint (e.g. health or agents/run) using generated client. |

**How to test:** Install SDK, set base URL, run example script; confirm no import or runtime errors against running API.

### Completion notes (March 6, 2026)
- Added runnable SDK example script at `sdk/examples/run_health.py` that uses generated `openapi_client` to call `DefaultApi.health_api_health_get()`.
- Added visibility logging in the script:
  - startup log with selected base URL,
  - success log with returned health status,
  - exception logs for API and unexpected failures.
- Added `--base-url` CLI flag support with fallback to `AGENT_SEARCH_BASE_URL` env var and default `http://localhost:8000`.
- Updated `sdk/README.md` with a copy-paste command to run the checked-in example script.

### Useful logs
- Example script runtime logs:
  - `2026-03-06 17:45:46,990 INFO run_health: starting health check base_url=http://localhost:8000`
  - `2026-03-06 17:45:47,902 INFO run_health: health check succeeded status=ok`
  - `{'status': 'ok'}`
- Container restart output:
  - `Container agent-search-chrome Restarting`
  - `Container agent-search-backend Restarting`
  - `Container agent-search-db Restarting`
  - `Container agent-search-frontend Restarting`
- Container state after restart:
  - `docker compose ps` -> `agent-search-backend Up`, `agent-search-frontend Up`, `agent-search-chrome Up`, `agent-search-db Up (healthy)`.
- Backend logs include:
  - `Uvicorn running on http://0.0.0.0:8000`
  - `Application startup complete.`
  - `GET /api/health HTTP/1.1" 200 OK`
- Frontend logs include:
  - `VITE v5.4.21 ready`
  - `Local: http://localhost:5173/`
- DB logs include:
  - `database system is ready to accept connections`
- Health endpoint verification after startup stabilization:
  - `HTTP/1.1 200 OK`
  - `{"status":"ok"}`

### Tests run
- `chmod +x sdk/examples/run_health.py` -> pass.
- `docker compose up -d db backend frontend` -> pass.
- `python3 -m venv .venv-sdk-s8` -> pass.
- `source .venv-sdk-s8/bin/activate && pip install --upgrade pip && pip install -e sdk/python` -> pass.
- `AGENT_SEARCH_BASE_URL=http://localhost:8000 python sdk/examples/run_health.py` -> pass.
- `docker compose restart` -> pass.
- `docker compose ps` -> pass (`db` healthy; `backend`/`frontend`/`chrome` up).
- `docker compose logs --no-color --tail=160` -> reviewed; no blocking errors.
- `docker compose logs --no-color --tail=160 backend` -> reviewed; backend startup healthy.
- `docker compose logs --no-color --tail=160 frontend` -> reviewed; frontend startup healthy.
- `docker compose logs --no-color --tail=160 db` -> reviewed; db startup healthy.
- `curl -sS -i http://localhost:8000/api/health` -> transient connection reset observed during immediate post-restart window.
- Retry health check after stabilization:
  - `curl -sS -i http://localhost:8000/api/health` -> pass (`HTTP/1.1 200 OK`, `{"status":"ok"}`).

---

## Section S9: Document “Updating the SDK” workflow

**Single goal:** Document the steps to refresh the SDK when the API or spec changes (re-export spec, then re-run generator).

**Details:**
- Add “Updating the SDK” subsection to README or sdk/README: run export script, then generate script; link to S1 and S5.
- No automation required in this section; docs only.

**Tech stack and dependencies**
- None.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/README.md` or `agent-search/sdk/README.md` | “Updating the SDK” subsection with ordered steps. |

**How to test:** Change a route or schema, follow the documented steps, confirm generated SDK reflects the change.

### Completion notes (March 6, 2026)
- Added `### Updating the SDK` subsection to `sdk/README.md` with explicit ordered workflow and direct linkage to **S1** (`export_openapi.py`) and **S5** (`generate_sdk.sh`).
- Included a review step (`git status -- openapi.json sdk/python`) so generated artifacts are consistently verified before commit.
- Executed the documented update steps end-to-end and validated the generated SDK still runs against the live backend.

### Useful logs
- OpenAPI export:
  - `2026-03-06 17:48:19,856 INFO scripts.export_openapi: OpenAPI export complete output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json canonical_output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json openapi_version=3.1.0 path_count=5 sample_paths=['/api/agents/run', '/api/health', '/api/internal-data/load', '/api/internal-data/wiki-sources', '/api/internal-data/wipe']`
- SDK generation:
  - `2026-03-06T22:48:21Z INFO generate_sdk: starting image=openapitools/openapi-generator-cli lang=python spec=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json output=/Users/nickbohm/Desktop/worktree/agent-search/sdk/python`
  - `OpenAPI Generator: python (client)`
  - `writing file /local/sdk/python/openapi_client/api/agents_api.py`
  - `writing file /local/sdk/python/openapi_client/configuration.py`
  - `2026-03-06T22:48:26Z INFO generate_sdk: generation complete spec=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json output=/Users/nickbohm/Desktop/worktree/agent-search/sdk/python`
- Container restart and runtime visibility:
  - `docker compose restart` restarted `backend`, `frontend`, `db`, and `chrome`.
  - `docker compose ps` shows `agent-search-db ... Up ... (healthy)` and `agent-search-backend` / `agent-search-frontend` / `agent-search-chrome` up.
  - Backend logs include `Uvicorn running on http://0.0.0.0:8000` and `Application startup complete.`
  - Frontend logs include `VITE v5.4.21 ready` and `Local:   http://localhost:5173/`.
  - DB logs include `database system is ready to accept connections`.
- Health + SDK runtime checks:
  - `HTTP/1.1 200 OK` with `{"status":"ok"}` from `GET /api/health`.
  - `2026-03-06 17:49:02,002 INFO run_health: starting health check base_url=http://localhost:8000`
  - `2026-03-06 17:49:02,020 INFO run_health: health check succeeded status=ok`
  - `{'status': 'ok'}`

### Tests run
- `uv run --project src/backend python scripts/export_openapi.py` -> pass.
- `./scripts/generate_sdk.sh` -> pass.
- `docker compose restart` -> pass.
- `docker compose ps` -> pass (`db` healthy; `backend`/`frontend`/`chrome` up).
- `docker compose logs --no-color --tail=180 backend` -> reviewed; no blocking errors.
- `docker compose logs --no-color --tail=180 frontend` -> reviewed; no blocking errors.
- `docker compose logs --no-color --tail=180 db` -> reviewed; no blocking errors.
- `curl -sS -i http://localhost:8000/api/health` -> pass (`HTTP/1.1 200 OK`, `{"status":"ok"}`).
- `python3 -m venv .venv-sdk-s9 && source .venv-sdk-s9/bin/activate && pip install -e sdk/python && AGENT_SEARCH_BASE_URL=http://localhost:8000 python sdk/examples/run_health.py` -> pass.

---

## Section S10: Optional orchestration script (export + generate)

**Single goal:** Add a single script or Make target that runs export then generate (optional one-command SDK refresh).

**Details:**
- Script runs export_openapi (or equivalent) then generate_sdk; may assume cwd or accept paths.
- Optional: only add if the team wants one-command refresh; can be skipped.

**Tech stack and dependencies**
- Same as S1 and S5.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/scripts/update_sdk.sh` or Makefile target | Runs export script then generate_sdk script. |

**How to test:** Run orchestration script; confirm spec file and SDK output are both updated.

### Completion notes (March 6, 2026)
- Added executable orchestration script at `scripts/update_sdk.sh` that chains:
  1. `uv run --project src/backend python scripts/export_openapi.py --output <spec>`
  2. `scripts/generate_sdk.sh <spec> <output>`
- Script supports optional args (`SPEC_PATH`, `OUTPUT_DIR`) with defaults (`openapi.json`, `sdk/python`) and emits timestamped INFO logs for start/export-complete/full-complete visibility.
- Updated `sdk/README.md` with optional one-command refresh entry:
  - `./scripts/update_sdk.sh`

### Useful logs
- Orchestration run:
  - `2026-03-06T22:51:22Z INFO update_sdk: start spec=openapi.json output=sdk/python`
  - `2026-03-06 17:51:24,805 INFO scripts.export_openapi: OpenAPI export complete output=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json ... openapi_version=3.1.0 path_count=5`
  - `2026-03-06T22:51:25Z INFO update_sdk: openapi export complete spec=openapi.json`
  - `2026-03-06T22:51:25Z INFO generate_sdk: starting ...`
  - `OpenAPI Generator: python (client)`
  - `2026-03-06T22:51:30Z INFO generate_sdk: generation complete spec=/Users/nickbohm/Desktop/worktree/agent-search/openapi.json output=/Users/nickbohm/Desktop/worktree/agent-search/sdk/python`
  - `2026-03-06T22:51:30Z INFO update_sdk: sdk refresh complete spec=openapi.json output=sdk/python`
- Container restart and runtime visibility:
  - `docker compose restart` restarted `backend`, `frontend`, `db`, and `chrome`.
  - `docker compose ps` shows `agent-search-db ... Up ... (healthy)` and `agent-search-backend` / `agent-search-frontend` / `agent-search-chrome` up.
  - Backend logs include `Uvicorn running on http://0.0.0.0:8000` and `Application startup complete.`
  - Frontend logs include `VITE v5.4.21 ready` and `Local: http://localhost:5173/`.
  - DB logs include `database system is ready to accept connections`.
- Health check:
  - `HTTP/1.1 200 OK`
  - `{"status":"ok"}`

### Tests run
- `chmod +x scripts/update_sdk.sh && ./scripts/update_sdk.sh` -> pass.
- `docker compose restart` -> pass.
- `docker compose ps` -> pass (`db` healthy; `backend`/`frontend`/`chrome` up).
- `docker compose logs --no-color --tail=200 backend` -> reviewed; no blocking errors.
- `docker compose logs --no-color --tail=200 frontend` -> reviewed; no blocking errors.
- `docker compose logs --no-color --tail=200 db` -> reviewed; no blocking errors.
- `curl -sS -i http://localhost:8000/api/health` -> pass (`HTTP/1.1 200 OK`, `{"status":"ok"}`).

---

## Section 1: Optional chat model parameter at run entry

**Single goal:** Allow the run entry point to accept an optional chat model (e.g. LangChain `BaseChatModel` / OpenAI) so callers can supply their own model; when not provided, keep current env-based default.

**Details:**
- Add optional `model` parameter to `run_runtime_agent` (and any public SDK entry that calls it).
- When provided, use it for `create_coordinator_agent(..., model=...)` and for the decomposition LLM call (`_run_decomposition_only_llm_call`); when not provided, use existing `_RUNTIME_AGENT_MODEL` / `_DECOMPOSITION_ONLY_MODEL` and current `ChatOpenAI` construction.
- Do not change request/response schema in this section; focus on the service layer signature and coordinator/decomposition wiring.

### Completion notes (March 6, 2026)
- Updated `run_runtime_agent(...)` in `src/backend/services/agent_service.py` to accept optional `model: BaseChatModel | None = None`.
- Threaded optional `model` to both coordinator and decomposition call paths:
  - `create_coordinator_agent(vector_store=..., model=selected_model)` where `selected_model` is caller-provided model or existing `_RUNTIME_AGENT_MODEL` default.
  - `_run_decomposition_only_llm_call(..., model=model)`.
- Updated `_run_decomposition_only_llm_call(...)` to accept optional `model`; when provided, invoke that model directly; when omitted, preserve existing `ChatOpenAI` + env-default behavior and fallback behavior.
- Added runtime logging for model selection visibility (`provided_model` and decomposition model selection log).
- Added/updated service tests in `src/backend/tests/services/test_agent_service.py`:
  - default path verifies decomposition model argument is `None` and coordinator keeps default model behavior.
  - provided-model path verifies the same model object is passed to both decomposition and `create_coordinator_agent`.

### Useful logs
- Unit tests:
  - `============================== 20 passed in 6.92s ==============================`
- Container restart/state:
  - `Container agent-search-backend  Restarting`
  - `Container agent-search-backend  Started`
  - `agent-search-backend ... Up ...`
  - `agent-search-db ... Up ... (healthy)`
- Health/API:
  - `{"status":"ok"}` from `GET /api/health`
  - Runtime log during API run: `Runtime agent run start query=What is pgvector used for? query_length=26 provided_model=False`
  - Runtime log shows normal pipeline progression with no backend exceptions for this change.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> pass (`20 passed`).
- `docker compose restart backend` -> pass.
- `curl -sS http://localhost:8000/api/health` -> pass.
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> pass (200 with `main_question`, `sub_qa`, `output` response shape).
- `docker compose logs --tail 80 backend db frontend` -> reviewed for visibility; no change-specific blocking errors.

---

## Section 2: Optional vector store parameter at run entry

**Single goal:** Allow the run entry point to accept an optional vector store instance so callers can supply their own store; when not provided, keep current `get_vector_store(...)` from env/DB.

**Details:**
- Add optional `vector_store` parameter to `run_runtime_agent` (and any public SDK entry).
- When provided, use it for initial search, coordinator retriever, and refinement retrieval; when not provided, call `get_vector_store(connection=..., collection_name=..., embeddings=...)` as today.
- Do not change request/response schema in this section; focus on the service layer.

### Completion notes (March 6, 2026)
- Updated `src/backend/services/agent_service.py` to accept optional `vector_store: Any | None = None` on `run_runtime_agent(...)`.
- Added selection logic:
  - Uses caller-provided vector store when present.
  - Falls back to existing `get_vector_store(connection=DATABASE_URL, collection_name=_VECTOR_COLLECTION_NAME, embeddings=get_embedding_model())` path when omitted.
- Threaded selected vector store through all required retrieval paths:
  - initial search (`search_documents_for_context` before decomposition),
  - coordinator creation (`create_coordinator_agent(vector_store=...)`),
  - refinement retrieval (`_seed_refined_sub_qa_from_retrieval(vector_store=...)`).
- Added visibility logs for vector store source:
  - `provided_vector_store` at run start,
  - `Runtime agent vector store selected source=default|provided`.
- Added coverage in `src/backend/tests/services/test_agent_service.py`:
  - new test asserts provided vector store bypasses `get_vector_store` and is used in initial search, coordinator, and refinement retrieval.
  - default path remains covered by existing tests with `get_vector_store` monkeypatched and asserted.

### Useful logs
- Unit tests:
  - `============================== 21 passed in 4.20s ==============================`
- Backend restart + health:
  - `Container agent-search-backend  Restarting`
  - `Container agent-search-backend  Started`
  - `{"status":"ok"}` from `GET /api/health`
- Runtime visibility:
  - `Runtime agent run start query=What is pgvector used for? query_length=26 provided_model=False provided_vector_store=False`
  - `Runtime agent vector store selected source=default collection_name=agent_search_internal_data`
- API smoke:
  - `POST /api/agents/run` returned HTTP `200`
  - Response shape includes `main_question`, `sub_qa`, `output`
- Container log checks performed for all relevant services:
  - `docker compose logs --tail=200 backend`
  - `docker compose logs --tail=120 frontend`
  - `docker compose logs --tail=120 db`

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> pass (`21 passed`).
- `docker compose restart backend` -> pass.
- `curl -sS http://localhost:8000/api/health` -> pass (`{"status":"ok"}`).
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> pass (HTTP `200`).
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no change-specific blocking errors.

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

### Completion notes (March 6, 2026)
- Added centralized `RuntimeTimeoutConfig` in `src/backend/services/agent_service.py` with a single builder (`build_runtime_timeout_config_from_env`) covering all timeout keys needed for Sections 4–18.
- Added robust timeout env parsing via `_read_timeout_seconds(...)` with fallback-to-default behavior and warning logs for invalid/non-positive values.
- Added `_RUNTIME_TIMEOUT_CONFIG` load point and runtime visibility log at run start to show configured timeout values without changing runtime behavior.
- Documented all timeout env vars and defaults in `.env.example`.
- Added unit tests validating default timeout values and env overrides/fallback handling.

### Useful logs
- `Runtime timeout config loaded vector_store=20s initial_search=20s decomposition_llm=60s coordinator_invoke=90s ... refined_answer=60s`
- `Invalid timeout env value; using default env_key=REFINED_ANSWER_TIMEOUT_S value=abc default=60`
- `docker compose restart backend` -> `Container agent-search-backend Restarting` / `Started`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `docker compose logs --tail=120 backend` included normal startup lines and no new traceback after restart.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `23 passed`
- `docker compose ps` -> `backend`, `frontend`, `db` up (`db` healthy)
- Log checks run for all services:
  - `docker compose logs --tail=120 backend`
  - `docker compose logs --tail=80 frontend`
  - `docker compose logs --tail=80 db`

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

### Completion notes (March 6, 2026)
- Added `_run_with_timeout(...)` in `src/backend/services/agent_service.py` using stdlib `concurrent.futures` and wired it into the default `get_vector_store(...)` path.
- Added a section-4 guardrail in `run_runtime_agent(...)`:
  - Applies timeout only when `vector_store` is not provided.
  - On timeout, logs warning visibility and short-circuits with a safe `RuntimeAgentRunResponse` fallback message instead of failing.
  - Keeps provided-vector-store path unchanged (no timeout wrapper applied).
- Added visibility log lines for timeout guardrail operation (`operation=vector_store_acquisition`) and short-circuit behavior.
- Added tests in `src/backend/tests/services/test_agent_service.py`:
  - timeout case (slow `get_vector_store`) returns fallback response and skips coordinator.
  - normal case (fast `get_vector_store`) proceeds through full runtime path.

### Useful logs
- Unit tests:
  - `============================== 25 passed in 4.95s ==============================`
- Backend restart/state:
  - `Container agent-search-backend  Restarting`
  - `Container agent-search-backend  Started`
  - `docker compose ps` showed `backend`, `frontend`, `db` up (`db` healthy).
- Health/API:
  - `{"status":"ok"}` from `GET /api/health`
  - `POST /api/agents/run` returned HTTP `200` with unchanged response shape.
- Runtime/containers:
  - Backend logs include normal runtime progression and no change-specific backend traceback for this section.
  - Frontend logs show Vite dev server ready on `http://localhost:5173/`.
  - DB logs show startup/checkpoint activity; historical warnings observed (`there is already a transaction in progress`) but no new section-4 blocker.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> pass (`25 passed`).
- `docker compose restart backend` -> pass.
- `curl -sS http://localhost:8000/api/health` -> pass (`{"status":"ok"}`).
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> pass (HTTP `200`).
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=80 frontend`, `docker compose logs --tail=80 db` -> reviewed for visibility.

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

### Completion notes (March 6, 2026)
- Updated `run_runtime_agent(...)` in `src/backend/services/agent_service.py` to guardrail the initial context-build block with `_run_with_timeout(...)` using `INITIAL_SEARCH_TIMEOUT_S`.
- Wrapped both calls (`search_documents_for_context(...)` and `build_initial_search_context(...)`) in one timeout operation (`initial_search_context_build`) so the entire context pre-step is bounded.
- Added timeout fallback behavior that does not fail the run: if the operation times out, runtime now logs a warning and continues with `initial_search_context = []`.
- Added two tests in `src/backend/tests/services/test_agent_service.py`:
  - timeout path: slow initial search triggers timeout, decomposition/answer generation receive empty context and run continues.
  - normal path: initial search within timeout preserves built context and passes it through decomposition + initial answer generation.

### Useful logs
- `Runtime guardrail timeout operation=initial_search_context_build timeout_s=1`
- `Initial decomposition context timeout; continuing with empty context query=... timeout_s=1`
- `Initial decomposition context built query=... docs=... k=5 score_threshold=None`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`
- `docker compose ps` shows `backend` up and `db` healthy after restart.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `27 passed`
- `docker compose restart backend` -> pass
- `curl -sS http://localhost:8000/api/health` -> pass (`{"status":"ok"}`)
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> pass (HTTP `200`)
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no change-specific backend exceptions

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

### Completion notes (March 6, 2026)
- Updated `run_runtime_agent(...)` in `src/backend/services/agent_service.py` to execute `_run_decomposition_only_llm_call(...)` through `_run_with_timeout(...)` with `DECOMPOSITION_LLM_TIMEOUT_S`.
- Added non-failing timeout fallback behavior: when decomposition exceeds timeout, runtime now logs a warning and uses a single normalized fallback sub-question derived from the original user query.
- Kept decomposition parse flow unchanged by serializing timeout fallback into the same JSON-array shape consumed by `_parse_decomposition_output(...)`.
- Added two tests in `src/backend/tests/services/test_agent_service.py`:
  - timeout path: slow decomposition call triggers guardrail and coordinator input uses fallback normalized sub-question.
  - normal path: decomposition call within timeout preserves returned decomposition output and coordinator receives it.

### Useful logs
- `Runtime guardrail timeout operation=decomposition_llm_call timeout_s=1`
- `Decomposition LLM timeout; continuing with fallback sub-question query=... timeout_s=1 fallback=...`
- `Runtime timeout config loaded vector_store=20s initial_search=20s decomposition_llm=60s coordinator_invoke=90s ... refined_answer=60s`
- `docker compose restart backend` -> `Container agent-search-backend Restarting` / `Started`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `INFO: ... "POST /api/agents/run HTTP/1.1" 200 OK`

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `29 passed`
- `docker compose restart backend` -> pass
- `curl -sS http://localhost:8000/api/health` -> pass (`{"status":"ok"}`)
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> pass (HTTP `200` with `main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no change-specific backend exceptions

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

### Completion notes (March 6, 2026)
- Updated `run_runtime_agent(...)` in `src/backend/services/agent_service.py` to execute coordinator `agent.invoke(...)` via `_run_with_timeout(...)` using `COORDINATOR_INVOKE_TIMEOUT_S`.
- Added non-failing timeout fallback behavior: on coordinator timeout, runtime now continues with partial captured callback data when present, otherwise seeds minimal `sub_qa` from decomposition output.
- Added fallback helper `_build_fallback_sub_qa_from_decomposition(...)` for decomposition-derived minimal `sub_qa` when no coordinator messages are available.
- Added safe coordinator-output handling: if no final coordinator message exists (timeout path), runtime logs and continues synthesis from `sub_qa` without failing.
- Added tests in `src/backend/tests/services/test_agent_service.py`:
  - timeout path: slow coordinator invoke triggers guardrail and fallback `sub_qa` is used.
  - normal path: coordinator invoke within timeout preserves coordinator-derived `sub_qa` behavior.

### Useful logs
- `Runtime guardrail timeout operation=coordinator_invoke timeout_s=1`
- `Coordinator invoke timeout; continuing with fallback sub_qa query=... timeout_s=1 decomposition_sub_question_count=...`
- `Coordinator timeout fallback sub_qa seeded from decomposition count=...`
- `docker compose restart backend` -> `Container agent-search-backend Restarting` / `Started`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `POST /api/agents/run` runtime check -> `keys=['main_question','output','sub_qa']`, non-empty `sub_qa`, HTTP `200`
- `docker compose ps` -> backend/frontend/db all up; db healthy
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` reviewed; no new change-specific backend exceptions

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `31 passed`
- `docker compose restart backend` -> pass
- `curl -sS http://localhost:8000/api/health` -> pass (`{"status":"ok"}`)
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> pass (HTTP `200`; response keys `main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=200 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility

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

### Completion notes (March 6, 2026)
- Updated `_run_pipeline_for_single_subquestion(...)` in `src/backend/services/agent_service.py` to execute `_apply_document_validation_to_sub_qa([working_item])[0]` through `_run_with_timeout(...)` using `DOCUMENT_VALIDATION_TIMEOUT_S`.
- Added non-failing fallback for per-item validation timeouts: on timeout, the pipeline logs a warning and continues with the existing retrieved output unchanged for that sub-question (validation skipped), then proceeds through reranking/generation/verification.
- Added tests in `src/backend/tests/services/test_agent_service.py`:
  - timeout path: slow document validation triggers timeout guardrail and the sub-question keeps original `sub_answer`.
  - normal path: document validation within timeout applies the validated `sub_answer`.

### Useful logs
- `Runtime guardrail timeout operation=document_validation_subquestion timeout_s=1`
- `Per-subquestion document validation timeout; continuing without validation sub_question=... timeout_s=1`
- `Per-subquestion document validation start count=1 min_relevance_score=...`
- `Per-subquestion pipeline item complete sub_question=... answerable=... reason=...`
- `docker compose restart backend` -> `Container agent-search-backend Restarting` / `Started`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `POST /api/agents/run` runtime check -> HTTP `200` with response keys `main_question`, `sub_qa`, `output`
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` reviewed for visibility.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `33 passed`
- `docker compose restart backend` -> pass
- `curl -sS http://localhost:8000/api/health` -> pass (`{"status":"ok"}`)
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> pass (HTTP `200`; response keys `main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no change-specific backend exceptions

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

### Completion notes (March 6, 2026)
- Updated `_run_pipeline_for_single_subquestion(...)` in `src/backend/services/agent_service.py` to execute reranking through `_run_with_timeout(...)` with operation name `rerank_subquestion` and timeout `RERANK_TIMEOUT_S`.
- Added non-failing fallback behavior for reranking timeouts: pipeline now keeps existing document order (no rerank mutation), logs a warning, and continues to subanswer generation and verification.
- Added tests in `src/backend/tests/services/test_agent_service.py`:
  - timeout path: slow reranking triggers guardrail and preserves pre-rerank `sub_answer`.
  - normal path: reranking within timeout applies updated reranked output.

### Useful logs
- `Runtime guardrail timeout operation=rerank_subquestion timeout_s=1`
- `Per-subquestion reranking timeout; continuing with original document order sub_question=What changed in NATO policy? timeout_s=1`
- `docker compose restart backend` -> `Container agent-search-backend Restarting` / `Started`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `POST /api/agents/run` runtime check -> HTTP `200` with response keys `main_question`, `sub_qa`, `output`
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` reviewed for visibility.

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `35 passed`
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py::test_run_pipeline_for_single_subquestion_skips_reranking_on_timeout -o log_cli=true --log-cli-level=WARNING'` -> `1 passed` (with rerank timeout warning logs)
- `docker compose restart backend` -> pass
- `curl -sS http://localhost:8000/api/health` -> pass (`{"status":"ok"}`)
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> pass (HTTP `200`; response keys `main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no reranking-guardrail runtime exceptions

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

### Completion notes (March 6, 2026)
- Updated `_run_pipeline_for_single_subquestion(...)` in `src/backend/services/agent_service.py` to execute `_apply_subanswer_generation_to_sub_qa([working_item])[0]` through `_run_with_timeout(...)` with operation name `subanswer_generation_subquestion` and timeout `SUBANSWER_GENERATION_TIMEOUT_S`.
- Added non-failing timeout fallback behavior for subanswer generation: when the subanswer generation step times out, the pipeline now sets subanswer text to `Answer not available in time.` and continues to verification/synthesis.
- Added timeout visibility logs for subanswer generation fallback with sub-question and timeout seconds.
- Added tests in `src/backend/tests/services/test_agent_service.py`:
  - timeout path: slow subanswer generation triggers guardrail and fallback text is used.
  - normal path: subanswer generation within timeout applies generated subanswer.

### Useful logs
- `Runtime guardrail timeout operation=subanswer_generation_subquestion timeout_s=1`
- `Per-subquestion subanswer generation timeout; continuing with fallback text sub_question=... timeout_s=1`
- `docker compose restart backend` -> `Container agent-search-backend Restarting` / `Started`
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> HTTP `200` with keys `main_question`, `sub_qa`, `output`
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility; no change-specific backend exceptions

### Tests run
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py'` -> `37 passed`
- `docker compose restart backend` -> pass
- `curl -sS http://localhost:8000/api/health` -> pass (`{"status":"ok"}`)
- `curl -sS -X POST http://localhost:8000/api/agents/run -H 'Content-Type: application/json' -d '{"query":"What is pgvector used for?"}'` -> pass (HTTP `200`; response keys `main_question`, `sub_qa`, `output`)
- `docker compose logs --tail=220 backend`, `docker compose logs --tail=120 frontend`, `docker compose logs --tail=120 db` -> reviewed for visibility
