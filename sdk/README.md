# SDK directory

This directory stores generated SDK artifacts for this repository.

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

## Repository policy

Generated files under `sdk/python` are committed to git (not ignored).  
When backend API/schema changes, re-export the OpenAPI spec and regenerate the SDK, then commit the updated `sdk/python` contents.
