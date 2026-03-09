# SDK directory

This directory holds both SDK surfaces used by `agent-search`:

- Primary: in-process runtime SDK (`agent_search`) under `src/backend/agent_search`
- Secondary: generated HTTP client SDK under `sdk/python`

## Primary SDK: `agent_search` (in-process)

Public functions:

- `run(query, *, vector_store, model, config=None)`
- `run_async(query, *, vector_store, model, config=None)`
- `get_run_status(job_id)`
- `cancel_run(job_id)`

Return contract:

- Sync: `RuntimeAgentRunResponse { main_question, sub_qa[], output }`
- Async start/status/cancel response models in `schemas`

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
