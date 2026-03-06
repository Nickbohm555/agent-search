# Agent-Search Implementation Plan (RAG-focused)

**Goal:** Build a better RAG system. Input: user question. Output: answer based on vectorized docs (with citations where applicable).

Tasks are in **recommended implementation order** (1…n). Each section = **one context window**. Complete one section at a time.

Current section to work on: section S7. (move +1 after each turn)

---

## SDK creation (OpenAPI Generator)

Steps below turn the agent-search FastAPI API into a generated, schema-driven SDK. Complete in order; each section is exactly one deliverable.

---

## Section S1: Add script to export OpenAPI from FastAPI app to a file

**Single goal:** Add a script that loads the FastAPI app, calls `app.openapi()`, and writes the OpenAPI spec to a file (no running server required).

**Details:**
- Script must be runnable from repo (e.g. `python scripts/export_openapi.py` or from backend dir).
- Output path may be configurable or fixed; schema must include all mounted routes (`/api/health`, `/api/agents/*`, `/api/internal-data/*`).

**Tech stack and dependencies**
- FastAPI (existing). Optional: `pyyaml` if writing YAML; otherwise JSON is fine.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/scripts/export_openapi.py` | Loads app, calls `app.openapi()`, writes spec to a file. |

**How to test:** Run the script; confirm the output file exists and contains OpenAPI 3.x paths and components.

**Test results:** Completed on March 6, 2026.
- `uv run --project src/backend python scripts/export_openapi.py` -> exported `openapi.json` at repo root with OpenAPI `3.1.0`.
- Validation check confirms required paths exist: `/api/health`, `/api/agents/run`, `/api/internal-data/load`, `/api/internal-data/wipe`, `/api/internal-data/wiki-sources`.
- Validation check confirms `components` is present in exported schema.

---

## Section S2: Canonical OpenAPI spec file path and format

**Single goal:** Define a single canonical path and format for the OpenAPI spec file in the repo so all tooling uses the same input.

**Details:**
- Spec file lives at one path (e.g. `agent-search-api.yaml` or `openapi.yaml` at repo root or in a designated folder).
- Export script (S1) must write to this path. YAML preferred for readability; JSON acceptable.

**Tech stack and dependencies**
- None new; export script from S1.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/agent-search-api.yaml` (or chosen path) | Canonical OpenAPI 3.x spec; produced by export script. |

**How to test:** Run export script; confirm file exists at canonical path. Optionally validate with `openapi-generator validate -i <path>` or online validator.

**Test results:** Completed on March 6, 2026.
- `uv run --project src/backend python scripts/export_openapi.py` -> exported canonical spec to `openapi.json` at repo root.
- Validation check confirms JSON OpenAPI schema contains `openapi`, `paths`, and `components`, and includes `/api/health`, `/api/agents/run`, `/api/internal-data/load`, and `/api/internal-data/wipe`.

---

## Section S3: Validate exported OpenAPI spec

**Single goal:** Add a repeatable way to validate the canonical OpenAPI spec (syntax and structure).

**Details:**
- Use OpenAPI Generator’s validate command (e.g. via Docker) or a documented validator; no new app code required.
- Document the validation command in README or script comment.

**Tech stack and dependencies**
- Docker (for `openapi-generator validate`) or another validator; no new app dependencies.

**Files and purpose**

| File | Purpose |
|------|--------|
| Optional: one-line in `scripts/validate_openapi.sh` or in docs | Runs validation against canonical spec file. |

**How to test:** Run validation; fix spec or export if it fails until validation passes.

**Test results:** Completed on March 6, 2026.
- `uv run --project src/backend python scripts/export_openapi.py` -> refreshed canonical spec at `openapi.json` with OpenAPI `3.1.0`.
- `./scripts/validate_openapi.sh` -> OpenAPI Generator validation passed (`No validation issues detected.`).
- `docker compose restart db backend frontend` -> all required services restarted cleanly.
- `docker compose ps` -> `db` healthy; `backend` and `frontend` up.
- `docker compose logs --tail=120 backend`, `docker compose logs --tail=120 frontend`, and `docker compose logs --tail=120 db` reviewed with no startup/runtime errors after restart.

---

## Section S4: Docker command for OpenAPI Generator (Python client)

**Single goal:** Document the exact `docker run` command that generates the Python SDK from the canonical spec, with no local generator install.

**Details:**
- Use image `openapitools/openapi-generator-cli`; mount repo (or spec dir) so `-i` and `-o` point at host paths.
- Output to a dedicated directory (e.g. `sdk/python/` or `agent-search-python-sdk/`). No script yet; command only.

**Tech stack and dependencies**
- Docker.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/README.md` or `agent-search/sdk/README.md` | Document the one-line `docker run ... generate -i ... -g python -o ...` command. |

**How to test:** Run the documented command; confirm output directory exists and contains generated Python client (e.g. `api/`, `models/`, `configuration.py`).

**Test results:** Completed on March 6, 2026.
- Added the exact Docker OpenAPI Generator command to `README.md` under OpenAPI spec, generating Python SDK to dedicated output path `sdk/python`.
- `uv run --project src/backend python scripts/export_openapi.py` -> refreshed canonical spec `openapi.json` (OpenAPI `3.1.0`).
- `docker run --rm -u "$(id -u):$(id -g)" -v "$(pwd):/local" openapitools/openapi-generator-cli generate -i /local/openapi.json -g python -o /local/sdk/python` -> generated client successfully.
- Output verification confirms generated Python client structure present under `sdk/python`, including `openapi_client/api`, `openapi_client/models`, and `openapi_client/configuration.py`.
- Restarted app services with `docker compose restart db backend frontend`; `docker compose ps` shows `db` healthy and `backend`/`frontend` up.
- Reviewed `docker compose logs --tail=120 backend`, `docker compose logs --tail=120 frontend`, and `docker compose logs --tail=120 db`; no blocking startup/runtime errors observed.
- Health check `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}` after restart stabilization.

---

## Section S5: Generate-SDK shell script

**Single goal:** Add a shell script that runs the OpenAPI Generator Docker command so SDK generation is a single invocation.

**Details:**
- Script takes no args (or optional spec path / output path); uses canonical spec path and output dir from S2 and S4.
- Must be runnable from repo root or a documented cwd.

**Tech stack and dependencies**
- Docker; no new pip/npm deps.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/scripts/generate_sdk.sh` | Invokes `docker run ... openapi-generator-cli generate` with correct `-i`, `-g python`, `-o`. |

**How to test:** Run `./scripts/generate_sdk.sh`; confirm SDK output directory is created/updated with generated code.

**Test results:** Completed on March 6, 2026.
- Added `scripts/generate_sdk.sh` with canonical defaults (`openapi.json` -> `sdk/python`), optional path overrides, and timestamped INFO/ERROR logs.
- `uv run --project src/backend python scripts/export_openapi.py` -> refreshed canonical spec at `openapi.json`.
- `./scripts/generate_sdk.sh` -> generated/updated SDK under `sdk/python` via Docker OpenAPI Generator.
- `docker compose restart` -> restarted `backend`, `frontend`, `db`, and `chrome`; `docker compose ps` shows app services up and `db` healthy.
- `docker compose logs --tail=140` reviewed for all running services; no blocking startup/runtime errors observed.
- `curl -sS http://localhost:8000/api/health` -> `{"status":"ok"}`.

---

## Section S6: SDK output location and repo policy

**Single goal:** Decide where the generated SDK lives in the repo and whether it is committed or gitignored.

**Details:**
- One chosen path (e.g. `sdk/python/` or `agent-search-python-sdk/`). Document in README or sdk/README.
- Either add that path to `.gitignore` (regenerate only) or commit generated files; document the choice.

**Tech stack and dependencies**
- None.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/.gitignore` and/or `agent-search/sdk/README.md` | Ignore or commit policy for generated SDK directory; document location. |

**How to test:** Run generate script; confirm output is at the documented path; confirm git state matches policy.

**Test results:** (Add when section is complete.)

---

## Section S7: SDK install and usage documentation

**Single goal:** Document how to install the generated SDK and call one endpoint (e.g. health or agents run).

**Details:**
- Install steps (e.g. `pip install -e sdk/python` or from generated folder).
- Minimal code example: import client, set base URL, call one method. No new code deliverable; docs only.

**Tech stack and dependencies**
- Generated SDK’s own dependencies only.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/sdk/README.md` or main `README.md` | Install instructions and minimal usage example (copy-pasteable). |

**How to test:** Follow the doc in a clean venv; confirm install and one successful call (against running API or mock).

**Test results:** (Add when section is complete.)

---

## Section S8: Minimal runnable example script using generated SDK

**Single goal:** Add one runnable example script that uses the generated client to call the API.

**Details:**
- Single file (e.g. `sdk/examples/run_health.py` or `sdk/examples/run_agent.py`); uses generated client; base URL configurable via env or arg.
- No new libraries; only the generated SDK.

**Tech stack and dependencies**
- Generated SDK from S5.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/sdk/examples/run_health.py` (or similar) | Calls one endpoint (e.g. health or agents/run) using generated client. |

**How to test:** Install SDK, set base URL, run example script; confirm no import or runtime errors against running API.

**Test results:** (Add when section is complete.)

---

## Section S9: Document “Updating the SDK” workflow

**Single goal:** Document the steps to refresh the SDK when the API or spec changes (re-export spec, then re-run generator).

**Details:**
- Add “Updating the SDK” subsection to README or sdk/README: run export script, then generate script; link to S1 and S5.
- No automation required in this section; docs only.

**Tech stack and dependencies**
- None.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/README.md` or `agent-search/sdk/README.md` | “Updating the SDK” subsection with ordered steps. |

**How to test:** Change a route or schema, follow the documented steps, confirm generated SDK reflects the change.

**Test results:** (Add when section is complete.)

---

## Section S10: Optional orchestration script (export + generate)

**Single goal:** Add a single script or Make target that runs export then generate (optional one-command SDK refresh).

**Details:**
- Script runs export_openapi (or equivalent) then generate_sdk; may assume cwd or accept paths.
- Optional: only add if the team wants one-command refresh; can be skipped.

**Tech stack and dependencies**
- Same as S1 and S5.

**Files and purpose**

| File | Purpose |
|------|--------|
| `agent-search/scripts/update_sdk.sh` or Makefile target | Runs export script then generate_sdk script. |

**How to test:** Run orchestration script; confirm spec file and SDK output are both updated.

**Test results:** (Add when section is complete.)

---

**MANDATORY before marking section complete or moving to `agent-search/completed.md`:**
1. **Restart the application** after all code for this section is built (e.g. stop then start the app/server/containers).
2. **Check all logs** (app logs, build logs, runtime logs) and **run all relevant tests** (unit, integration, or commands from "How to test").
3. **If anything fails** (startup error, test failure, bad logs, browser/API errors): read the logs and test output, fix the cause, then **repeat from step 1** (restart and re-check). Do **not** call the section "completed" or add it to `completed.md` until everything passes.
4. Only after a successful restart and passing checks (and browser check when applicable), record outcomes under **Test results** and then mark the section complete / move to `completed.md`.


---
