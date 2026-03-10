
Tasks are in **required implementation order** (1...n). Each section = one context window. Complete one section at a time.

Current section to work on: section 5. (move +1 after each turn)

---

## Section 1: Release readiness check - version and dry-run build

**Single goal:** Confirm SDK version/tag alignment and dry-run release workflow readiness.

**Details:**
- Verify `sdk/core/pyproject.toml` version matches the intended tag format (`agent-search-core-vX.Y.Z`).
- Run `scripts/release_sdk.sh` in dry-run mode (no publish).

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies; use existing build/twine tooling defined in `sdk/core/pyproject.toml`.
- Tooling (uv, poetry, Docker): no Docker changes; use `scripts/release_sdk.sh` on host.

**Files and purpose**

| File | Purpose |
|------|--------|
| scripts/release_sdk.sh | Dry-run build + twine check verification. |
| sdk/core/pyproject.toml | Source of SDK version metadata for tag alignment. |
| .github/workflows/release-sdk.yml | Reference tag naming for release. |

**How to test:** Run `scripts/release_sdk.sh` (dry-run) and confirm version/tag alignment.

**Test results:** (Add when section is complete.)
- Command and outcome.

---

## Section 2: Public SDK release - PyPI publish

**Single goal:** Publish the core SDK package to PyPI as a public release.

**Details:**
- Use the existing `scripts/release_sdk.sh` workflow with `PUBLISH=1`.
- Tag must already exist and match the package version.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies; use existing build/twine tooling defined in `sdk/core/pyproject.toml`.
- Tooling (uv, poetry, Docker): no Docker changes; use `scripts/release_sdk.sh` on host.

**Files and purpose**

| File | Purpose |
|------|--------|
| scripts/release_sdk.sh | Publish flow (build + twine check + upload when `PUBLISH=1`). |
| sdk/core/pyproject.toml | Source of SDK version metadata for release. |
| .github/workflows/release-sdk.yml | Reference tag naming and publish workflow. |

**How to test:** Run `scripts/release_sdk.sh` with `PUBLISH=1`.

**Test results:** (Add when section is complete.)
- Command and outcome.
- 2026-03-10: `PUBLISH=1 ./scripts/release_sdk.sh` -> blocked/fail: build+twine-check passed, publish step aborted with `PUBLISH=1 requires TWINE_API_TOKEN`; no `agent-search-core-v*` git tag found locally to validate release-tag precondition.
- 2026-03-10 (rerun): `PUBLISH=1 ./scripts/release_sdk.sh` -> blocked/fail again: build+twine-check passed; publish gate failed with `PUBLISH=1 requires TWINE_API_TOKEN`; validated local tag precondition still unmet (`agent-search-core-v0.1.0` not present).

---

## Section 3: PyPI publish documentation - release steps

**Single goal:** Document the PyPI publish steps and prerequisites for the core SDK.

**Details:**
- Document the required tag format and version alignment (`agent-search-core-vX.Y.Z`).
- Document the `scripts/release_sdk.sh` dry-run and publish commands.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies; documentation only.
- Tooling (uv, poetry, Docker): no Docker changes; reference existing scripts/workflows.

**Files and purpose**

| File | Purpose |
|------|--------|
| sdk/core/README.md | Publish instructions for SDK consumers/maintainers. |
| README.md | Top-level release summary and pointer to SDK publish docs. |

**How to test:** Manually verify docs match the release workflow and script arguments.

**Test results:** (Add when section is complete.)
- 2026-03-10: `./scripts/release_sdk.sh` -> passed; built `agent_search_core-0.1.0` wheel/sdist, `twine check` passed, upload skipped (`PUBLISH=0`).
- 2026-03-10: `RELEASE_TAG=agent-search-core-v0.1.0 ./scripts/release_sdk.sh` -> passed; explicit tag validation matched package version and dry-run completed successfully.

---

## Section 4: SDK install smoke test - clean venv run

**Single goal:** Validate the published SDK installs cleanly and can execute a minimal in-process smoke run.

**Details:**
- Create a clean virtual environment, install the released `agent_search_core` package, and run a minimal `run()` call with a protocol-compatible fake vector store and mock model.
- The smoke test must not require backend services or Docker.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies; use the published package and standard venv tooling.
- Tooling (uv, poetry, Docker): no Docker changes; use host Python for venv.

**Files and purpose**

| File | Purpose |
|------|--------|
| sdk/core/README.md | Document the smoke test commands and expected output. |

**How to test:** Run the documented venv install + minimal script to confirm import and execution.

**Test results:** (Add when section is complete.)
- 2026-03-10: `python3 -m venv .venv && . .venv/bin/activate && python -m pip install "agent-search-core==0.1.0"` -> failed: no published distribution available (`No matching distribution found for agent-search-core==0.1.0`).
- 2026-03-10: `./scripts/release_sdk.sh` -> passed; built local wheel/sdist and `twine check` passed.
- 2026-03-10: `python3.11 -m venv .venv && . .venv/bin/activate && python -m pip install sdk/core/dist/agent_search_core-0.1.0-py3-none-any.whl` -> passed install.
- 2026-03-10: `python smoke_run.py` (clean venv, wheel install) -> failed import smoke gate: `ModuleNotFoundError: No module named 'agent_search.public_api'` (artifact currently ships only `agent_search/__init__.py`).

---
