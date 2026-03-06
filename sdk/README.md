# SDK directory

This directory stores generated SDK artifacts for this repository.

## Python SDK

- Output path: `sdk/python`
- Source spec: `openapi.json` at repo root
- Generation command: `./scripts/generate_sdk.sh`

## Repository policy

Generated files under `sdk/python` are committed to git (not ignored).  
When backend API/schema changes, re-export the OpenAPI spec and regenerate the SDK, then commit the updated `sdk/python` contents.
