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

## Requirements

- Python `>=3.11,<3.14`
- A compatible vector store and chat model as shown above.

## Build

```bash
cd sdk/core
python -m build
```

## Supported API

The supported callable exported by `agent_search` is:

- `advanced_rag`

Notes about `advanced_rag(...)`:
- It is a synchronous call that runs the full retrieval-and-answer workflow and returns a `RuntimeAgentRunResponse`.
- You supply the model and vector store; the SDK orchestrates the LangGraph-based runtime around them.
- Optional `config={"thread_id": "..."}` lets you pass a stable execution identity into the run.
- If you pass `langfuse_callback=...`, the SDK includes that callback in runtime tracing.
- `langfuse_settings` is accepted for compatibility but ignored unless you provide an explicit `langfuse_callback`.

`advanced_rag(...)` output schema:

```python
RuntimeAgentRunResponse(
  main_question: str,
  thread_id: str,
  sub_qa: list[SubQuestionAnswer],
  output: str,
  final_citations: list[CitationSourceRow],
)
```

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
