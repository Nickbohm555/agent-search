# agent-search core SDK

In-process Python SDK for `agent-search`. This package lets you call the runtime directly inside your own app.

The SDK always requires both:
- A **chat model** (e.g. `langchain_openai.ChatOpenAI`)
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
from agent_search import advanced_rag, build_langfuse_callback
from agent_search.vectorstore.langchain_adapter import LangChainVectorStoreAdapter

vector_store = LangChainVectorStoreAdapter(your_langchain_vector_store)
model = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)
langfuse_callback = build_langfuse_callback(sampling_key="customer-123")

response = advanced_rag(
    "What is pgvector?",
    vector_store=vector_store,
    model=model,
    langfuse_callback=langfuse_callback,
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

## Runtime API surface

Primary functions exposed by `agent_search`:

- `advanced_rag`
- `build_langfuse_callback`
- `run`
- `run_async`
- `get_run_status`
- `cancel_run`

`run(...)` remains available as a compatibility alias and delegates to `advanced_rag(...)`.

Tracing behavior for `advanced_rag(...)`:
- If you pass `langfuse_callback=...`, SDK uses that callback for run tracing.
- Or pass `langfuse_settings={...}` and SDK builds the callback from that config.
- If both are omitted, SDK does not trace the run.

Config-driven tracing example:

```python
response = advanced_rag(
    "What is pgvector?",
    vector_store=vector_store,
    model=model,
    langfuse_settings={
        "enabled": True,
        "public_key": "...",
        "secret_key": "...",
        "host": "https://cloud.langfuse.com",
        "environment": "production",
        "release": "agent-search-core-0.1.8",
        "runtime_sample_rate": 1.0,
    },
)
```

`advanced_rag(...)` output schema:

```python
RuntimeAgentRunResponse(
  main_question: str,
  sub_qa: list[SubQuestionAnswer],
  output: str,
  final_citations: list[CitationSourceRow],
)
```

Config and errors exposed by `agent_search`:

- `RuntimeConfig`, `RuntimeTimeoutConfig`, `RuntimeRetrievalConfig`, `RuntimeRerankConfig`
- `SDKError`, `SDKConfigurationError`, `SDKRetrievalError`, `SDKModelError`, `SDKTimeoutError`

## Vector store compatibility

Runtime SDK expects `similarity_search(query, k, filter=None)`.
For LangChain-backed stores, use:

- `agent_search.vectorstore.langchain_adapter.LangChainVectorStoreAdapter`

## Notes

- For the full app (API, DB, UI), run this repo with Docker Compose.
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
