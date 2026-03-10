# agent-search core SDK workspace

This workspace contains packaging metadata for the distributable in-process `agent_search` SDK boundary.

## Scope

- Separates SDK packaging from backend application packaging.
- Excludes backend-only web and DB dependencies.
- Produces standalone wheel/sdist artifacts.

## Build

```bash
cd sdk/core
python -m build
```

## Runtime API surface

Primary functions exposed by `agent_search`:

- `run`
- `run_async`
- `get_run_status`
- `cancel_run`

Config and errors exposed by `agent_search`:

- `RuntimeConfig`, `RuntimeTimeoutConfig`, `RuntimeRetrievalConfig`, `RuntimeRerankConfig`
- `SDKError`, `SDKConfigurationError`, `SDKRetrievalError`, `SDKModelError`, `SDKTimeoutError`

## Vector store compatibility

Runtime SDK expects `similarity_search(query, k, filter=None)`.
For LangChain-backed stores, use:

- `agent_search.vectorstore.langchain_adapter.LangChainVectorStoreAdapter`

## PyPI release guide

Run all release commands from the repository root.

### Prerequisites

1. Package version in `sdk/core/pyproject.toml` must match the git tag version.
2. Release tag format is `agent-search-core-vX.Y.Z`.
3. For publish, `TWINE_API_TOKEN` must be set for the target PyPI account.

Example version/tag alignment for version `0.1.0`:

- `sdk/core/pyproject.toml`: `version = "0.1.0"`
- release tag: `agent-search-core-v0.1.0`

### Dry-run (build + Twine validation, no upload)

```bash
./scripts/release_sdk.sh
```

Optional explicit tag validation in dry-run mode:

```bash
RELEASE_TAG=agent-search-core-v0.1.0 ./scripts/release_sdk.sh
```

### Publish to PyPI

```bash
PUBLISH=1 TWINE_API_TOKEN=*** ./scripts/release_sdk.sh
```

Optional explicit tag validation during publish:

```bash
RELEASE_TAG=agent-search-core-v0.1.0 PUBLISH=1 TWINE_API_TOKEN=*** ./scripts/release_sdk.sh
```

`scripts/release_sdk.sh` behavior summary:

- Always: clean `sdk/core/dist`, build wheel/sdist, run `twine check`.
- With `PUBLISH=1`: require `TWINE_API_TOKEN`, then upload artifacts.

## SDK install smoke test (clean venv, no Docker)

Run from any temporary host directory with Python 3.11+.

Install from PyPI (post-publish):

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "agent-search-core==0.1.0"
```

Minimal in-process smoke script:

```python
from __future__ import annotations

import json
import logging

from agent_search.public_api import run

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


class FakeVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        logging.info(
            "FakeVectorStore.similarity_search called query=%s k=%s has_filter=%s",
            query,
            k,
            filter is not None,
        )
        return []


response = run(
    "What does the smoke test validate?",
    vector_store=FakeVectorStore(),
    model=object(),
)
print(json.dumps(response.model_dump(), indent=2))
```

Expected smoke output characteristics:

- Logs include SDK run lifecycle lines and one `FakeVectorStore.similarity_search` call.
- JSON output includes:
  - `main_question` set to the input query.
  - `sub_qa` as a list.
  - `output` as a non-empty string.

Troubleshooting:

- If install fails with a Python version error, use Python `>=3.11,<3.14`.
- If import fails with `ModuleNotFoundError: No module named 'agent_search.public_api'`, the published artifact does not yet include runtime API modules and must be repackaged before this smoke test can pass.
