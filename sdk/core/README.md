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

## Release guidance

Use the repository release script from project root:

```bash
./scripts/release_sdk.sh
```

Publish flow (requires `TWINE_API_TOKEN`):

```bash
PUBLISH=1 TWINE_API_TOKEN=*** ./scripts/release_sdk.sh
```

Tag format used by CI release workflow:

- `agent-search-core-v<version>`
