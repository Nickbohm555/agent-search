# agent-search core SDK package workspace

This directory contains packaging metadata for the distributable in-process
`agent_search` SDK boundary.

## Scope

- Dedicated package workspace separate from backend app packaging.
- Excludes backend-only web and database dependencies from this package.
- Built as a standalone Python sdist/wheel workspace.

## Build

```bash
cd sdk/core
python -m build
```

## Dependency boundary

This package intentionally excludes backend web/DB dependencies such as:

- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `psycopg`
- `alembic`
- `pgvector`
