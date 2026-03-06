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
