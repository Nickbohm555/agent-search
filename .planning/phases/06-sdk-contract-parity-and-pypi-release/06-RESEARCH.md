# Phase 6: SDK Contract Parity and PyPI Release - Research

**Researched:** 2026-03-13  
**Domain:** OpenAPI/SDK contract parity plus `agent-search-core` release and migration documentation  
**Confidence:** HIGH

## Summary

Phase 6 should be executed as a release-hardening phase, not a feature-creation phase. The project already has most of the required mechanics: backend schema-driven OpenAPI generation, generated HTTP client refresh scripts, drift gates in CI, and a tag-triggered PyPI publishing workflow for `agent-search-core`. The planning-critical work is to ensure all Phase 1-5 contract changes (HITL fields, run controls, prompt options, additive `sub_answers`) are represented consistently across backend schemas, `openapi.json`, generated `sdk/python`, and `sdk/core` runtime models before publication.

The current repo shows a strong baseline but also two release risks that planning must absorb: (1) contract naming/alias drift (`sub_qa` legacy vs additive `sub_answers`, `runtime_config`/`controls`, potential hyphenated aliases) and (2) generator/release reproducibility drift (generated SDK metadata already shows a `7.21.0-SNAPSHOT` generator string). Phase 6 should lock parity with explicit artifact gates, then produce release/migration docs that tell consumers exactly how to adopt HITL/control/prompt features with compatibility-safe defaults.

The PyPI pipeline is already close to standard practice: `release-sdk.yml` builds artifacts, checks them, and publishes with `pypa/gh-action-pypi-publish` under `id-token: write` (Trusted Publishing pattern). Planning should treat this as the canonical release path and avoid introducing parallel/manual publish flows except for emergency rollback procedures.

**Primary recommendation:** make Phase 6 a strict contract-and-release gate: finalize backend schema surfaces from Phases 1-5, regenerate and verify both SDKs in one atomic change, then publish `agent-search-core` via the existing Trusted Publishing workflow with migration docs that define exact field mappings, defaults, and compatibility behavior.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.12 | Backend request/response schema source for OpenAPI | Existing source of truth for API contracts |
| Pydantic | 2.10.6 | Contract modeling and aliasing for compatibility-safe schema evolution | Already used end-to-end for API + SDK schema surfaces |
| OpenAPI Generator (python) | CLI image (`openapitools/openapi-generator-cli`) | Regenerates `sdk/python` from `openapi.json` | Existing automated repo workflow (`generate_sdk.sh`, `validate_openapi.sh`) |
| `agent-search-core` packaging via Hatchling | hatchling>=1.25.0 | Build backend/runtime SDK artifacts for PyPI | Existing package build backend in `sdk/core/pyproject.toml` |
| PyPA publish action | `pypa/gh-action-pypi-publish@release/v1` | Trusted Publishing upload to PyPI | Already configured in `.github/workflows/release-sdk.yml` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `build` + `twine` | installed in release job | Build/check wheel + sdist | Local/CI pre-publish validation (`scripts/release_sdk.sh`) |
| GitHub Actions artifacts | v4 actions in workflow | Build once, publish exactly built artifacts | Prevents "rebuild on publish" drift |
| CI drift gate scripts | repo scripts | Assert OpenAPI + generated SDK parity | Every PR touching contracts or schemas |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Existing Trusted Publishing workflow | Manual `twine upload` from local shell | Faster ad hoc, but weaker auditability/reproducibility |
| Generated HTTP SDK from committed OpenAPI | Hand-maintained API client | High long-term drift risk and duplicated contract logic |
| Additive compatibility fields (`sub_answers` + legacy `sub_qa`) | Breaking rename in same release | Cleaner shape, but breaks existing consumers and violates compatibility objective |

**Installation:**
```bash
# Contract update + client regeneration
./scripts/update_sdk.sh
./scripts/validate_openapi.sh

# SDK package build/check
./scripts/release_sdk.sh

# Publish (when release is approved)
PUBLISH=1 TWINE_API_TOKEN=*** ./scripts/release_sdk.sh
```

## Architecture Patterns

### Recommended Project Structure
```text
src/backend/
├── schemas/agent.py                       # canonical API models (HITL/controls/prompts/sub_answers)
├── routers/agent.py                       # request mapping to SDK config
└── agent_search/public_api.py             # runtime config application for sync/async SDK entrypoints

openapi.json                               # canonical exported OpenAPI artifact
sdk/python/                                # generated HTTP SDK, committed
sdk/core/src/schemas/agent.py              # in-process SDK model mirror
sdk/core/src/agent_search/public_api.py    # in-process SDK behavior entrypoints
docs/migration-guide.md                    # migration instructions for existing consumers
docs/releases/*.md                         # release notes and compatibility policy
.github/workflows/ci.yml                   # parity gate execution
.github/workflows/release-sdk.yml          # release/publish pipeline
scripts/update_sdk.sh                      # export + regenerate
scripts/validate_openapi.sh                # drift/parity checks
scripts/release_sdk.sh                     # build/check/publish package
```

### Pattern 1: Backend-first contract finalization, then generated artifacts
**What:** Treat backend schemas as source of truth; regenerate `openapi.json` and `sdk/python` from that, then update `sdk/core` mirrors intentionally.  
**When to use:** Every Phase 6 contract update from Phases 1-5 outputs.  
**Example:**
```bash
# Source: existing repo scripts
uv run --project src/backend python scripts/export_openapi.py --output openapi.json
./scripts/generate_sdk.sh openapi.json sdk/python
./scripts/validate_openapi.sh
```

### Pattern 2: Compatibility aliasing for additive fields
**What:** Keep legacy fields callable while introducing new canonical release fields where required (example: additive `sub_answers` beside `sub_qa`).  
**When to use:** REL-03 parity where older consumers must keep working.  
**Example:**
```python
# Source: Pydantic alias pattern + repo compatibility direction
from pydantic import BaseModel, Field, AliasChoices

class RuntimeAgentRunResponse(BaseModel):
    sub_answers: list[SubQuestionAnswer] = Field(default_factory=list)
    sub_qa: list[SubQuestionAnswer] = Field(
        default_factory=list,
        validation_alias=AliasChoices("sub_qa", "sub_answers"),
        serialization_alias="sub_qa",
    )
```

### Pattern 3: Build-once, publish-once release flow
**What:** Build distributions in one CI job, artifact them, publish exact artifacts in a separate OIDC-authenticated job.  
**When to use:** All official `agent-search-core` releases.  
**Example:**
```yaml
# Source: .github/workflows/release-sdk.yml
permissions:
  id-token: write
steps:
  - uses: actions/download-artifact@v4
  - uses: pypa/gh-action-pypi-publish@release/v1
```

### Anti-Patterns to Avoid
- **Publishing before parity gates:** never release from partial schema updates.
- **Dual truth for contracts:** avoid separate hand-authored SDK model definitions unrelated to backend schema.
- **Undocumented compatibility behavior:** never add HITL/control/prompt fields without migration examples and defaults.
- **Floating generation assumptions:** avoid unpinned generator behavior in release-critical flows without validation snapshots.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PyPI authentication in CI | Long-lived project token secrets in repo settings | Trusted Publishing (`id-token` + PyPI trusted publisher) | Short-lived credentials and lower token leak risk |
| SDK drift detection | Manual checklists or ad hoc diffs | `./scripts/validate_openapi.sh` in CI | Deterministic gate already enforced by workflow |
| API client maintenance | Manual `sdk/python` edits | OpenAPI generation pipeline | Regeneration keeps schema and client synchronized |
| Artifact verification | Custom wheel introspection scripts per release | Existing `scripts/release_sdk.sh` build + `twine check` + wheel package check | Reuses tested release path and avoids one-off tooling |

**Key insight:** Phase 6 should consolidate around existing release automation and schema generation, not introduce parallel contract/release mechanisms.

## Common Pitfalls

### Pitfall 1: Contract parity passes backend tests but fails SDK consumers
**What goes wrong:** backend accepts new fields, but `sdk/python` or `sdk/core` models lag and consumers cannot send/read new contracts.  
**Why it happens:** schema/model updates are merged without regenerating both SDK surfaces.  
**How to avoid:** require one atomic change set across `src/backend/schemas`, `openapi.json`, `sdk/python`, and `sdk/core/src/schemas`.  
**Warning signs:** failing tests in generated models or missing fields in `sdk/python/openapi_client/models/runtime_agent_run_request.py`.

### Pitfall 2: Additive alias breaks serialization expectations
**What goes wrong:** only one of `sub_qa` or `sub_answers` is returned, or aliases deserialize but do not serialize as documented.  
**Why it happens:** incomplete alias configuration (`validation_alias` without `serialization_alias`, or defaults omitted).  
**How to avoid:** define explicit validation + serialization behavior and add response snapshot tests for both old and new client expectations.  
**Warning signs:** response JSON differs across sync/async/status endpoints for the same run payload.

### Pitfall 3: Release artifacts built from stale/generated drift
**What goes wrong:** PyPI package is published while `openapi.json` and generated SDK are out of sync with runtime contracts.  
**Why it happens:** release process bypasses `validate_openapi.sh` or does not gate on drift.  
**How to avoid:** make drift gate mandatory before release-tag workflow; verify local dry-run script output before tagging.  
**Warning signs:** CI drift gate fails after tagging; release notes describe fields absent from published artifacts.

### Pitfall 4: Migration docs describe behavior not present in defaults
**What goes wrong:** docs claim default-off compatibility for HITL/controls/prompts, but runtime defaults differ.  
**Why it happens:** docs updated independently of runtime config defaults and tests.  
**How to avoid:** tie each migration claim to a test and explicit config default in schemas/config parser.  
**Warning signs:** old clients experience behavior changes without sending new fields.

### Pitfall 5: Generator reproducibility drift
**What goes wrong:** generated client diffs fluctuate across environments/releases.  
**Why it happens:** unpinned generator image/tooling changes over time.  
**How to avoid:** pin generator version/image digest or record generator version in release checklist and enforce deterministic generation in CI.  
**Warning signs:** unrelated generated file churn on repeated `generate_sdk.sh` runs.

## Code Examples

Verified patterns from official/project sources:

### Contract parity gate in CI
```yaml
# Source: .github/workflows/ci.yml
- name: Validate OpenAPI and generated SDK drift
  run: ./scripts/validate_openapi.sh
```

### Trusted Publishing in release workflow
```yaml
# Source: .github/workflows/release-sdk.yml
publish:
  permissions:
    id-token: write
  environment:
    name: pypi
  steps:
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        packages-dir: dist
```

### Release script dry-run then publish
```bash
# Source: scripts/release_sdk.sh
./scripts/release_sdk.sh
PUBLISH=1 TWINE_API_TOKEN=*** ./scripts/release_sdk.sh
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual token-based PyPI uploads | OIDC Trusted Publishing via GitHub Actions | Current workflow | Better security posture and auditable CI publication |
| Manual API client sync | Generated `sdk/python` from committed `openapi.json` + drift gate | Current workflow | Reduces contract mismatch risk |
| Feature docs as optional post-release updates | Migration/release docs treated as release criteria | 1.0.0 release discipline | Better consumer adoption and fewer breaking surprises |

**Deprecated/outdated:**
- Publishing from local-only workflows as primary release path.
- Treating `sdk/python` generation as optional after backend contract changes.

## Open Questions

1. **Canonical request/response field names for Phase 6 docs**
   - What we know: planning artifacts reference `controls`, `runtime_config`, `custom_prompts`, and additive `sub_answers`.
   - What's unclear: final canonical naming/alias policy across REST JSON, SDK config dicts, and generated OpenAPI models.
   - Recommendation: lock a single canonical external shape in Phase 6, then document accepted aliases explicitly as compatibility behavior.

2. **Scope of SDK parity: `sdk/core` only or both `sdk/core` and generated `sdk/python` as release-blocking**
   - What we know: repository policy commits `sdk/python`, and `agent-search-core` is published separately.
   - What's unclear: whether REL-03 gate requires both SDK surfaces to expose all new fields at release cut.
   - Recommendation: treat both as release-blocking to prevent dual-surface drift.

3. **TestPyPI staging policy**
   - What we know: production publish workflow exists; no explicit TestPyPI lane in current workflow.
   - What's unclear: whether a pre-prod TestPyPI publish is required before production tags.
   - Recommendation: add optional TestPyPI staging step or documented dry-run policy before production publish.

## Sources

### Primary (HIGH confidence)
- Project code/workflows/scripts:
  - `src/backend/schemas/agent.py`
  - `src/backend/routers/agent.py`
  - `src/backend/agent_search/public_api.py`
  - `src/backend/agent_search/config.py`
  - `openapi.json`
  - `sdk/core/pyproject.toml`
  - `sdk/core/README.md`
  - `sdk/core/src/schemas/agent.py`
  - `sdk/python/pyproject.toml`
  - `sdk/python/openapi_client/models/runtime_agent_run_request.py`
  - `sdk/python/openapi_client/models/runtime_agent_run_response.py`
  - `scripts/export_openapi.py`
  - `scripts/generate_sdk.sh`
  - `scripts/update_sdk.sh`
  - `scripts/validate_openapi.sh`
  - `scripts/release_sdk.sh`
  - `.github/workflows/ci.yml`
  - `.github/workflows/release-sdk.yml`
  - `docs/migration-guide.md`
  - `docs/releases/1.0.0-langgraph-migration.md`
  - `docs/deprecation-map.md`

### Secondary (MEDIUM confidence)
- [Python Packaging User Guide: Publishing package distribution releases using GitHub Actions CI/CD workflows](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [PyPI Trusted Publishers documentation](https://docs.pypi.org/trusted-publishers/)
- [OpenAPI Generator python generator docs](https://openapi-generator.tech/docs/generators/python/)
- [Pydantic alias documentation](https://docs.pydantic.dev/latest/concepts/alias/)

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - directly verified in project manifests/workflows plus official packaging docs.
- Architecture: HIGH - concrete file-level parity and release touchpoints are already in repo.
- Pitfalls: HIGH - grounded in observable drift, alias, and release workflow constraints.

**Research date:** 2026-03-13  
**Valid until:** 2026-04-12
