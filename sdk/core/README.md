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
