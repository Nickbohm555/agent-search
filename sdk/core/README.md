# agent-search core SDK

In-process Python SDK for `agent-search`.

The PyPI package is intentionally narrow: consumers should call `advanced_rag(...)` and treat that as the supported entrypoint.

The SDK always requires both:
- A **chat model** (for example `langchain_openai.ChatOpenAI`)
- A **vector store** that implements `similarity_search(query, k, filter=None)`

It does not auto-build these dependencies for you.

## Install (PyPI)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install agent-search-core
python -c "import agent_search; print(agent_search.__file__)"
```

## Quick start

```python
from langchain_openai import ChatOpenAI
from agent_search import advanced_rag
from agent_search.vectorstore.langchain_adapter import LangChainVectorStoreAdapter

vector_store = LangChainVectorStoreAdapter(your_langchain_vector_store)
model = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)

response = advanced_rag(
    "What is pgvector?",
    vector_store=vector_store,
    model=model,
)
print(response.output)
```

## Contract notes for 1.0.14

Use these canonical names in new `config` payloads:

- `custom_prompts`
- `runtime_config`

Compatibility notes:

- `custom-prompts` is still accepted as an input alias, but new code should send `custom_prompts`.
- `advanced_rag(...)` remains the supported sync entrypoint for `agent-search-core`.
- For HITL flows, use the checkpointed runtime runner described below.
- Langfuse tracing is no longer supported in the SDK/runtime.

## Human-in-the-loop (HITL)

`agent-search-core` supports one opt-in review stage on `advanced_rag(...)`:

- `hitl_subquestions=True` pauses after decomposition so the caller can review or edit subquestions.
- Subquestion review is the only HITL checkpoint in the SDK.
- Query expansion no longer has a separate review checkpoint.

The SDK returns a normalized `review` object when a run pauses, and resume calls use SDK-owned decision helpers instead of raw backend payloads.

HITL checkpoint persistence is optional overall because non-HITL runs do not need it. For HITL or resume flows, provide one of these:

- `checkpoint_db_url="postgresql+psycopg://..."` when you want the SDK to create and own the LangGraph Postgres checkpointer for the call.
- `checkpointer=existing_checkpointer` when you already manage a ready-to-use LangGraph checkpoint saver instance.

Do not pass both at once.

When you use `checkpoint_db_url`, the caller must provide the checkpoint Postgres database explicitly on every checkpointed call:

- Provision a reachable Postgres database for LangGraph checkpoints before enabling HITL.
- Pass `checkpoint_db_url="postgresql+psycopg://..."` to `advanced_rag(...)` for the initial HITL call and every resume call.
- The runtime uses that caller-provided Postgres DB for checkpoint persistence only.
- On first use, the runtime checks whether that DB already has LangGraph checkpoint tables (`checkpoint_migrations`, `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`) and bootstraps them only when missing.

If you inject `checkpointer`, that saver is used as-is and the SDK does not create or bootstrap a new one for you.

Example paused result for subquestion review:

```python
from agent_search import advanced_rag

outcome = advanced_rag(
    "Summarize the customer feedback themes.",
    vector_store=vector_store,
    model=model,
    hitl_subquestions=True,
    checkpoint_db_url="postgresql+psycopg://agent_user:agent_pass@localhost:5432/agent_search",
)
print(outcome.status)  # "paused"
print(outcome.review.kind)  # "subquestion_review"
print(outcome.review.items[0].text)
```

Resume with SDK helpers:

```python
resume = outcome.review.with_decisions(
    outcome.review.items[0].approve(),
    outcome.review.items[1].edit("Theme 2 (billing and invoices)"),
)

resumed = advanced_rag(
    "Summarize the customer feedback themes.",
    model=model,
    vector_store=vector_store,
    resume=resume,
    checkpoint_db_url="postgresql+psycopg://agent_user:agent_pass@localhost:5432/agent_search",
)
print(resumed.response.output)
```

Reuse an existing checkpointer instead of passing a DSN:

```python
from agent_search import advanced_rag
from langgraph.checkpoint.postgres import PostgresSaver

with PostgresSaver.from_conn_string(
    "postgresql+psycopg://agent_user:agent_pass@localhost:5432/agent_search"
) as checkpointer:
    outcome = advanced_rag(
        "Summarize the customer feedback themes.",
        vector_store=vector_store,
        model=model,
        hitl_subquestions=True,
        checkpointer=checkpointer,
    )
```

For simple approval flows:

```python
resume = outcome.review.approve_all()
```

Detailed end-to-end example:

```python
from langchain_openai import ChatOpenAI
from agent_search import advanced_rag
from agent_search.vectorstore.langchain_adapter import LangChainVectorStoreAdapter

vector_store = LangChainVectorStoreAdapter(your_langchain_vector_store)
model = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)
question = "Summarize the customer feedback themes from the support archive."

first = advanced_rag(
    question,
    vector_store=vector_store,
    model=model,
    hitl_subquestions=True,
    checkpoint_db_url="postgresql+psycopg://agent_user:agent_pass@localhost:5432/agent_search",
)
assert first.status == "paused"
assert first.review.kind == "subquestion_review"

for item in first.review.items:
    print(item.item_id, item.text)

resume = first.review.with_decisions(
    first.review.items[0].approve(),
    first.review.items[1].edit("What billing and invoice complaints show up most often?"),
    first.review.items[2].reject(),
)

final = advanced_rag(
    question,
    vector_store=vector_store,
    model=model,
    resume=resume,
    checkpoint_db_url="postgresql+psycopg://agent_user:agent_pass@localhost:5432/agent_search",
)
assert final.status == "completed"
print(final.response.output)
```

Decision semantics:

- `approve()` keeps the item unchanged.
- `edit("...")` replaces the item text before the run continues.
- `reject()` removes the item from the next stage entirely.
- `approve_all()` is the shortcut when you want to resume without per-item changes.

Advanced callers can still pass raw `config["controls"]["hitl"]`, but the top-level HITL review toggles are now the preferred public API.

## Optional parameters

`advanced_rag(...)` supports these optional keyword parameters:

- `rerank_enabled`: Explicit per-call override for whether the rerank node runs.
- `query_expansion_enabled`: Explicit per-call override for whether the query-expansion node runs.
- `config`: Runtime controls and prompt overrides. Use this for `rerank`, `query_expansion`, `hitl`, `runtime_config`, and `custom_prompts`.
- `callbacks`: LangChain-compatible callbacks that should observe the run.
- `hitl_subquestions`: Enables the supported SDK HITL pause after decomposition.
- `resume`: Resume payload for a paused HITL run. The preferred form is the SDK `review.with_decisions(...)` result.
- `checkpoint_db_url`: Optional for normal runs. Required only for HITL or resume flows if you are not passing `checkpointer`.
- `checkpointer`: Optional injected LangGraph checkpoint saver. Use this instead of `checkpoint_db_url` when you already manage a ready-to-use saver instance.

Normal non-HITL runs can omit both `checkpoint_db_url` and `checkpointer`.

## Prompt customization

The SDK currently exposes two prompt override keys:

- `custom_prompts.subanswer`
- `custom_prompts.synthesis`

If you do not override them, the runtime uses these built-in defaults. These overrides only replace the instruction block. The SDK always appends the live `main_question`, `sub_question`, and evidence sections itself, so caller-provided prompt text cannot replace runtime inputs.

Current default `subanswer` instructions:

```text
You answer one sub-question using the full reranked evidence list below.
Requirements:
- Use only the evidence provided below.
- Treat each evidence line index as a citation key and cite claims with [index], e.g. [1] or [2][3].
- Keep citation indices from the provided evidence lines; do not invent new indices.
- Keep it to 1-3 sentences.
- Do not summarize the evidence list; directly answer the sub-question using cited evidence.
- If evidence is insufficient, explicitly say so.
```

Current default `synthesis` instructions:

```text
You synthesize the initial answer for the user's question.
Use both sources of input:
1) Initial retrieval context from the original question.
2) Per-subquestion answers with verification status.

Requirements:
- Return a concise answer (2-5 sentences).
- Prefer answerable/verified sub-question answers when present.
- If evidence is partial, say what is uncertain.
- Preserve citation markers from sub-question answers exactly, e.g. [1], [2][3].
- Do not collapse cited evidence into an uncited summary.
- Include at least one source attribution in parentheses, e.g. (source: ...).
- If initial retrieval context is used, reference its source field explicitly.
```

Keep reusable prompt defaults in the existing `config` map, then override only the keys you need per run.

```python
from copy import deepcopy

from langchain_openai import ChatOpenAI
from agent_search import advanced_rag
from agent_search.vectorstore.langchain_adapter import LangChainVectorStoreAdapter

vector_store = LangChainVectorStoreAdapter(your_langchain_vector_store)
model = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)

client_config = {
    "custom_prompts": {
        "subanswer": "Answer each sub-question with concise cited evidence only.",
        "synthesis": "Write a short final synthesis that preserves citation markers.",
    },
}

response = advanced_rag(
    "What changed in NATO maritime policy?",
    vector_store=vector_store,
    model=model,
    rerank_enabled=False,
    config=client_config,
)
print(response.output)
```

Per-run overrides should be merged into a fresh copy so one call does not mutate the reusable defaults for the next call.

```python
run_config = deepcopy(client_config)
run_config["custom_prompts"] = {
    **run_config.get("custom_prompts", {}),
    "synthesis": "Return a two-paragraph answer and keep every citation marker.",
}

response = advanced_rag(
    "Summarize the policy shift for shipping operators.",
    vector_store=vector_store,
    model=model,
    config=run_config,
)
```

Merge and fallback behavior:

- Built-in runtime defaults apply when `custom_prompts` is omitted.
- Client-level `config["custom_prompts"]` replaces built-ins on a per-key basis.
- Per-run merged values replace only the keys you override for that call.
- Use `custom_prompts` in Python code; the supported keys are `subanswer` and `synthesis`.
- Prompt overrides change generation instructions only. Citation validation and fallback behavior remain enforced in runtime code.

You can keep reusable prompt defaults at the top level and place per-run overrides in `runtime_config.custom_prompts`:

```python
response = advanced_rag(
    "Which runtime controls stay default-off?",
    vector_store=vector_store,
    model=model,
    config={
        "custom_prompts": {
            "subanswer": "Answer each sub-question with concise cited evidence only.",
            "synthesis": "Write a short synthesis with citations.",
        },
        "runtime_config": {
            "custom_prompts": {
                "synthesis": "Return a two-paragraph answer and keep every citation marker."
            }
        },
    },
)
```

`runtime_config` is additive. Omit it to preserve the prior prompt behavior.

## Requirements

- Python `>=3.11,<3.14`
- A compatible vector store and chat model as shown above.

## Build

```bash
cd sdk/core
python -m build
```

## Example script

A self-contained HITL walkthrough that imports the SDK and simulates pause/resume decisions lives at `examples/hitl_walkthrough.py`.

Run it from the package root:

```bash
cd sdk/core
python examples/hitl_walkthrough.py
```

## Supported API

The supported callable exported by `agent_search` is:

- `advanced_rag`

Notes about `advanced_rag(...)`:
- It is a synchronous call that runs the full retrieval-and-answer workflow and returns a `RuntimeAgentRunResponse`.
- You supply the model and vector store; the SDK orchestrates the LangGraph-based runtime around them.
- Optional `rerank_enabled=` and `query_expansion_enabled=` let one call override those runtime steps directly.
- Optional `hitl_subquestions=True` opts into subquestion review checkpoints.
- Checkpointed runs must also pass `checkpoint_db_url` so the SDK can use that Postgres DB for LangGraph checkpoints.
- Optional `config={"custom_prompts": {...}}` lets you override prompt instructions per run.

`advanced_rag(...)` output schema:

```python
RuntimeAgentRunResponse(
  main_question: str,
  thread_id: str | None,
  sub_items: list[tuple[str, str]],
  output: str,
  final_citations: list[CitationSourceRow],
)
```

`sub_items` contains the sub-question text and corresponding sub-answer text as tuples.

Read sub-items like this:

```python
for sub_question, sub_answer in response.sub_items:
    print(sub_question, sub_answer)
```

If you need the plain decomposed question list without answers, read `decomposition_sub_questions` from the async status payload instead of `RuntimeAgentRunResponse`:

```python
status = client.get_run_status(job_id)

for sub_question in status.decomposition_sub_questions:
    print(sub_question)

for sub_question, sub_answer in status.sub_items:
    print(sub_question, sub_answer)
```

Those fields are intentionally separate:

- `decomposition_sub_questions`: `list[str]` of generated sub-questions only.
- `sub_items`: `list[tuple[str, str]]` with question-and-answer pairs.

## Vector store compatibility

Runtime SDK expects `similarity_search(query, k, filter=None)`.
For LangChain-backed stores, use:

- `agent_search.vectorstore.langchain_adapter.LangChainVectorStoreAdapter`

## Notes

- This package is the SDK surface only. For the full app experience, run the repository with Docker Compose.
- The PyPI package is intentionally narrower than the backend internals; consumer integrations should rely on `advanced_rag(...)` only.
- For SDK-only use, install from PyPI and supply your own model + vector store.

## Release guidance

Use the repository release script from project root:

```bash
./scripts/release_sdk.sh
```

The release script verifies the built wheel includes the `agent_search` package before upload.

Publish flow (requires `TWINE_API_TOKEN`):

```bash
PUBLISH=1 TWINE_API_TOKEN=*** ./scripts/release_sdk.sh
```

Tag format used by CI release workflow:

- `agent-search-core-v<version>`
