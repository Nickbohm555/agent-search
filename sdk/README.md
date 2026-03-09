# SDK directory

This directory stores generated SDK artifacts for this repository.

The generated OpenAPI HTTP client is a secondary integration surface for
network calls to the running API. The primary SDK surface for in-process
usage remains `agent_search` under `src/backend/agent_search`.

## Python SDK

- Output path: `sdk/python`
- Source spec: `openapi.json` at repo root
- Generation command: `./scripts/generate_sdk.sh`

### Install

Create and activate a virtual environment, then install the generated SDK in editable mode:

```bash
python3 -m venv .venv-sdk
source .venv-sdk/bin/activate
pip install --upgrade pip
pip install -e sdk/python
```

### Minimal usage

Set the API base URL (default: `http://localhost:8000`) and call one endpoint.

Health endpoint example:

```python
import os
import openapi_client

base_url = os.getenv("AGENT_SEARCH_BASE_URL", "http://localhost:8000")
configuration = openapi_client.Configuration(host=base_url)

with openapi_client.ApiClient(configuration) as api_client:
    api = openapi_client.DefaultApi(api_client)
    response = api.health_api_health_get()
    print(response)
```

Agents run example:

```python
import os
import openapi_client

base_url = os.getenv("AGENT_SEARCH_BASE_URL", "http://localhost:8000")
configuration = openapi_client.Configuration(host=base_url)

with openapi_client.ApiClient(configuration) as api_client:
    api = openapi_client.AgentsApi(api_client)
    request = openapi_client.RuntimeAgentRunRequest(query="What is pgvector?")
    response = api.run_agent_api_agents_run_post(runtime_agent_run_request=request)
    print(response.output)
```

Run either snippet with:

```bash
AGENT_SEARCH_BASE_URL=http://localhost:8000 python your_script.py
```

### Runnable example script

Use the checked-in example script:

```bash
AGENT_SEARCH_BASE_URL=http://localhost:8000 python sdk/examples/run_health.py
```

### Updating the SDK

When backend routes or schema change, refresh the SDK in this exact order:

1. Re-export the canonical OpenAPI spec (**S1**):

```bash
uv run --project src/backend python scripts/export_openapi.py
```

2. Regenerate the Python SDK from that spec (**S5**):

```bash
./scripts/generate_sdk.sh
```

3. Review generated changes and commit updated `openapi.json` and `sdk/python` files:

```bash
git status -- openapi.json sdk/python
```

Optional one-command refresh:

```bash
./scripts/update_sdk.sh
```

## Repository policy

Generated files under `sdk/python` are committed to git (not ignored).  
When backend API/schema changes, re-export the OpenAPI spec and regenerate the SDK, then commit the updated `sdk/python` contents.
