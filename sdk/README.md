# SDK directory

This directory holds both SDK surfaces used by `agent-search`:

- Primary: in-process runtime SDK (`agent_search`) under `src/backend/agent_search`
- Secondary: generated HTTP client SDK under `sdk/python`

## Migration And Deprecation Guidance

If you are adopting the LangGraph-native `1.0.0` release, start here before wiring new SDK usage:

- [Migration Guide](../docs/migration-guide.md)
- [Deprecation Map](../docs/deprecation-map.md)

Recommended action:

- Use `advanced_rag(...)` as the primary sync entrypoint for new integrations.
- Move tracing setup to `build_langfuse_callback(...)` plus `langfuse_callback=...` instead of relying on `langfuse_settings` alone.
- Use `hitl_subquestions=True` and `hitl_query_expansion=True` for user-review checkpoints instead of raw `config["controls"]["hitl"]` in new code.

## Primary SDK: `agent_search` (in-process)

Public functions:

- `advanced_rag(query, *, vector_store, model, config=None, hitl_subquestions=False, hitl_query_expansion=False, ...)`

Return contract:

- Sync: `RuntimeAgentRunResponse { main_question, sub_qa[], output }`
- Async start/status/cancel response models in `schemas`

Install from PyPI:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install agent-search-core
```

Minimal usage (you must provide a chat model and a vector store):

```python
from langchain_openai import ChatOpenAI
from agent_search import advanced_rag
from agent_search.vectorstore.langchain_adapter import LangChainVectorStoreAdapter

vector_store = LangChainVectorStoreAdapter(your_langchain_vector_store)
model = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)

response = advanced_rag("What is pgvector?", vector_store=vector_store, model=model)
print(response.output)
```

### Error taxonomy

Consumer-facing exceptions:

- `SDKError` (base)
- `SDKConfigurationError`
- `SDKRetrievalError`
- `SDKModelError`
- `SDKTimeoutError`

### Vector store contract

The SDK expects a compatible vector store that implements:

- `similarity_search(query, k, filter=None)`

Use adapter when wrapping LangChain stores:

- `agent_search.vectorstore.langchain_adapter.LangChainVectorStoreAdapter`

## Secondary SDK: generated OpenAPI client (`sdk/python`)

Generated from root `openapi.json`.

- Output path: `sdk/python`
- Generator script: `./scripts/generate_sdk.sh`

Install locally:

```bash
python3 -m venv .venv-sdk
source .venv-sdk/bin/activate
pip install --upgrade pip
pip install -e sdk/python
```

Health example:

```python
import os
import openapi_client

base_url = os.getenv("AGENT_SEARCH_BASE_URL", "http://localhost:8000")
configuration = openapi_client.Configuration(host=base_url)

with openapi_client.ApiClient(configuration) as api_client:
    api = openapi_client.DefaultApi(api_client)
    print(api.health_api_health_get())
```

## Update workflow

When API/schema changes:

1. Export OpenAPI spec:

```bash
uv run --project src/backend python scripts/export_openapi.py
```

2. Validate spec:

```bash
./scripts/validate_openapi.sh
```

3. Regenerate SDK:

```bash
./scripts/generate_sdk.sh
```

4. Review generated changes:

```bash
git status -- openapi.json sdk/python
```

Optional shortcut:

```bash
./scripts/update_sdk.sh
```

## Repository policy

Generated files under `sdk/python` are committed (not ignored). Keep `openapi.json` and `sdk/python` in sync.
