# Agent-Search Implementation Plan (RAG-focused)

**Goal:** Build a better RAG system. Input: user question. Output: answer based on vectorized docs (with citations where applicable).

Tasks are in **recommended implementation order** (1…n). Each section = **one context window**. Complete one section at a time.

Current section to work on: section 8. (move +1 after each turn)

**Onyx article references:** The "Onyx article" line in each section points to [Onyx: Building the best Deep Research](https://onyx.app/blog/building-the-best-deep-research) for human reading only. Do not read or fetch the article as part of implementation.

---

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

**Test results:** Completed on March 6, 2026.
- `docker compose exec backend uv run pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py` -> 16 passed.
- Live API run logs include:
  - `Decomposition-only LLM output captured ...`
  - `Coordinator decomposition input prepared ...`
  - `POST /api/agents/run HTTP/1.1" 200 OK`

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

**Test results:** Completed on March 6, 2026.
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py'` -> 20 passed.
- Live API run logs include:
  - `Decomposition-only LLM output captured output_length=2 output_preview=[]`
  - `Decomposition output parsed sub_question_count=1 sub_questions=["What changed in NATO policy?"]`
  - `Coordinator decomposition input prepared query=What changed in NATO policy? context_items=0 parsed_sub_questions=1`
  - `POST /api/agents/run HTTP/1.1" 200 OK`

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

**Test results:** Completed on March 6, 2026.
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py'` -> 20 passed.
- Live API run logs include:
  - `Decomposition output parsed sub_question_count=2 sub_questions=["What is pgvector?", "What are the use cases of pgvector?"]`
  - `Coordinator sub-question input prepared parsed_sub_questions=2 sub_questions=["What is pgvector?", "What are the use cases of pgvector?"]`
  - `POST /api/agents/run HTTP/1.1" 200 OK`

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

**Test results:** Completed on March 6, 2026.
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run python -m pytest tests/services/test_agent_service.py tests/agents/test_coordinator_agent.py'` -> 20 passed.
- Live API run logs include:
  - `Coordinator raw output captured output_length=42 output_preview=Delegation complete; subanswers collected.`
  - `Initial answer generation complete via LLM ...`
  - `Runtime agent run complete output_length=523 ...`
  - `POST /api/agents/run HTTP/1.1" 200 OK`

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

**Test results:** Completed on March 6, 2026.
- `docker compose exec backend sh -lc 'cd /app && uv run pytest tests/tools/test_retriever_tool.py'` -> 3 passed.
- Retriever output contract remains:
  - `1. title=Alpha source=wiki://alpha content=First content`
  - `2. title=Beta source=wiki://beta content=Second content`
- Live runtime logs include:
  - `Retriever tool search_database ... citation_contract=index.title.source.content ...`
  - `GET /api/health HTTP/1.1" 200 OK`

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

**Test results:** Completed on March 6, 2026.
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run pytest tests/services/test_document_validation_service.py tests/services/test_agent_service.py'` -> 22 passed.
- Live API run logs include:
  - `Per-subquestion document validation ... contract_lines=0` (runtime visibility added for citation-contract line preservation).
  - `Per-subquestion reranking ... contract_lines=...` (rerank stage now reports citation-contract line count).
  - `POST /api/agents/run HTTP/1.1" 200 OK`

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

**Test results:** Completed on March 6, 2026.
- `docker compose exec backend sh -lc 'cd /app && uv pip install pytest && uv run python -m pytest tests/services/test_subanswer_service.py tests/services/test_agent_service.py'` -> 22 passed.
- Live API run logs include:
  - `Subanswer generation parsed reranked docs sub_question=... doc_count=...`
  - `Per-subquestion subanswer generated sub_question=... generated_len=...`
  - `POST /api/agents/run HTTP/1.1" 200 OK`

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

**Test results:** (Add when section is complete.)

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

**Test results:** (Add when section is complete.)

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

**Test results:** (Add when section is complete.)

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

**Test results:** (Add when section is complete.)

---
