# Phase 5: Major Release and Migration Documentation - Research

**Researched:** 2026-03-12
**Domain:** Python SDK major release management, LangGraph migration communication, and docs synchronization
**Confidence:** HIGH

## Summary

Phase 5 should be planned as a release-engineering + documentation hardening phase, not as runtime feature work. The repo already has the right release skeleton: a tagged release workflow, trusted-publishing-compatible GitHub Action usage, and OpenAPI drift checks. The planning focus should be on turning these into a strict release train for `1.0.0` and ensuring all user-facing surfaces (SDK README, migration guide, OpenAPI references, application HTML docs, and examples) tell one consistent LangGraph story.

For migration communication, the standard pattern is: (1) publish a major version for breaking changes, (2) ship a stepwise migration guide with old-to-new API mappings, (3) keep deprecated APIs callable for one transition window, and (4) document deprecations and removals explicitly in changelog/release notes. This matches SemVer, LangChain/LangGraph deprecation guidance, and Python ecosystem expectations for backwards compatibility communication.

Current repo signals to leverage in planning: `run()` is already a deprecated alias to `advanced_rag()`, release automation is tag-driven (`agent-search-core-v*`), and OpenAPI parity + SDK drift validation already exists. The phase plan should convert these ingredients into a publish-ready, migration-safe `1.0.0` documentation package.

**Primary recommendation:** Plan Phase 5 around a single release candidate checklist that gates `1.0.0` on migration docs completeness, OpenAPI/reference parity, and runnable LangGraph-first examples.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Semantic Versioning | 2.0.0 spec | Defines major/minor/patch and breaking-change signaling | Canonical release compatibility contract across ecosystems |
| Keep a Changelog | 1.0.0 format | Human-readable release notes structure | Standardized changelog sections for deprecations/removals |
| PyPI Trusted Publishing (`pypa/gh-action-pypi-publish`) | `release/v1` | Tokenless secure publishing from CI | Official PyPA-recommended publishing path |
| FastAPI OpenAPI metadata + operation docs | FastAPI `0.115.12` (repo pin) | Accurate API/reference docs generation | OpenAPI is source for generated SDK and API docs parity |
| LangGraph/LangChain migration docs | LangGraph v1 docs | Canonical migration language and deprecation framing | Prevents project docs from inventing non-standard migration semantics |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `build` + `twine` | Latest in CI/tooling | Build/check wheel + sdist | Release candidate verification before publish |
| OpenAPI Generator CLI | Docker image `openapitools/openapi-generator-cli` | Regenerate Python HTTP SDK from `openapi.json` | Any API schema change affecting `sdk/python` |
| `uv` | Project standard | Deterministic command execution for backend scripts | Exporting OpenAPI and running parity commands |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Trusted Publishing (OIDC) | Long-lived PyPI API tokens | Easier initial setup, weaker security posture and token-rotation burden |
| Keep a Changelog sections | Free-form GitHub release text only | Faster to write, lower migration clarity and weaker deprecation visibility |
| OpenAPI-driven reference docs | Hand-written API reference pages | More narrative control, high risk of contract drift |

**Installation:**
```bash
python -m pip install --upgrade build twine
```

## Architecture Patterns

### Recommended Project Structure
```text
docs/
├── application-documentation.html      # Human-oriented architecture/runtime docs
├── migration-v1.md                     # Stepwise legacy -> LangGraph migration guide
└── deprecation-map.md                  # Legacy API status, replacement, and removal targets

sdk/core/
├── pyproject.toml                      # Canonical SDK package version (major bump here)
└── README.md                           # SDK install/usage/migration quickstart

sdk/examples/
└── *.py                                # Runnable examples aligned with v1 API

openapi.json                            # Canonical API schema
sdk/python/                             # Generated HTTP client from openapi.json
```

### Pattern 1: Release Train With Explicit Gates
**What:** Make release docs and migration assets first-class release artifacts, not post-release follow-ups.
**When to use:** Every major release, especially with architecture migration.
**Example:**
```yaml
# Source: https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.x"
      - run: python3 -m pip install build --user
      - run: python3 -m build
  publish-to-pypi:
    if: startsWith(github.ref, 'refs/tags/')
    permissions:
      id-token: write
```

### Pattern 2: Migration Guide As Old-to-New Task Map
**What:** Organize migration docs as "legacy call/site -> v1 replacement -> verification step".
**When to use:** Any release with renamed APIs, deprecated aliases, or behavior changes.
**Example:**
```markdown
| Legacy usage | v1 usage | Action |
|---|---|---|
| `run(query, ...)` | `advanced_rag(query, ...)` | Replace import and function call |
| `langfuse_settings=...` only | `langfuse_callback=...` | Build and pass explicit callback |
```

### Pattern 3: State-Graph Reference Examples
**What:** Show typed state + node update examples in docs to make architecture concrete.
**When to use:** Reference docs and examples for LangGraph-first v1 adoption.
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/use-graph-api
from typing_extensions import TypedDict
from langgraph.graph import StateGraph

class State(TypedDict):
    messages: list

def node(state: State):
    return {"messages": state["messages"] + ["hello"]}

graph = StateGraph(State).add_node(node).set_entry_point("node").compile()
```

### Anti-Patterns to Avoid
- **Release-by-tag only:** Publishing `1.0.0` without migration/deprecation docs creates adoption risk and support load.
- **Dual source of truth for API docs:** Maintaining hand-edited API docs that diverge from `openapi.json` and generated SDK.
- **Silent deprecations:** Keeping deprecated aliases without explicit guide/changelog entries and removal horizon.
- **Example drift:** Shipping examples that still demonstrate legacy orchestration calls after major migration messaging.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Versioning semantics | Custom "major release" wording | SemVer 2.0.0 rules | Integrators need unambiguous compatibility signal |
| Changelog taxonomy | Ad hoc release text categories | Keep a Changelog sections | Makes deprecations/removals discoverable and consistent |
| PyPI auth | Long-lived secrets management flow | Trusted Publishing (OIDC) | Short-lived tokens reduce credential risk |
| API reference docs | Manual endpoint tables | FastAPI OpenAPI + generated SDK docs | Eliminates schema/docs drift |
| Deprecation lifecycle | Informal "will remove later" notes | Structured deprecation map with target versions | Enables predictable migration planning |

**Key insight:** In this phase, communication standards are part of product correctness; custom release/doc conventions create hidden compatibility risk.

## Common Pitfalls

### Pitfall 1: Major Version Bump Without Public API Boundary
**What goes wrong:** `1.0.0` is published but public API changes are not crisply documented.
**Why it happens:** Version bump is treated as a packaging action only.
**How to avoid:** Define explicit v1 public API section in release notes + migration guide before tagging.
**Warning signs:** Changelog lists generic "refactor/migration" entries with no old->new mapping.

### Pitfall 2: Migration Guide Missing Verification Steps
**What goes wrong:** Integrators change code but cannot confirm they migrated correctly.
**Why it happens:** Guide explains "what to edit" but not "how to validate".
**How to avoid:** Add a test command or runtime check for every migration step.
**Warning signs:** Guide has no "expected output/behavior" checkpoints.

### Pitfall 3: OpenAPI and SDK Drift During Final Docs Edits
**What goes wrong:** `openapi.json`, generated `sdk/python`, and narrative docs diverge at release time.
**Why it happens:** Last-minute endpoint/schema edits without regeneration.
**How to avoid:** Make `scripts/validate_openapi.sh` a release gate for Phase 5 completion.
**Warning signs:** CI drift failures or unstaged generated diffs before release tag.

### Pitfall 4: Deprecation Map Without Removal Horizon
**What goes wrong:** Legacy paths remain indefinitely because no target removal version/date exists.
**Why it happens:** Team avoids committing to deprecation timeline.
**How to avoid:** For each deprecated item, include "introduced deprecation in X, earliest removal in Y".
**Warning signs:** Deprecation map has replacements but blank/unknown removal columns.

### Pitfall 5: Example Code Not Updated to v1 Narrative
**What goes wrong:** Docs say "LangGraph-first", examples still show old orchestration entrypoints.
**Why it happens:** Example updates are treated as optional.
**How to avoid:** Add runnable example validation to release checklist.
**Warning signs:** Example imports/functions contradict migration guide recommendations.

## Code Examples

Verified patterns from official sources:

### Deprecating Public Interfaces Explicitly
```python
# Source: https://fastapi.tiangolo.com/tutorial/path-operation-configuration/
@app.get("/elements/", tags=["items"], deprecated=True)
async def read_elements():
    return [{"item_id": "Foo"}]
```

### LangGraph Typed State + Compile Pattern
```python
# Source: https://docs.langchain.com/oss/python/langgraph/use-graph-api
from typing_extensions import TypedDict
from langgraph.graph import StateGraph

class State(TypedDict):
    messages: list

builder = StateGraph(State)
builder.add_node(node)
builder.set_entry_point("node")
graph = builder.compile()
```

### Trusted Publishing Job Requirements
```yaml
# Source: https://docs.pypi.org/trusted-publishers/
publish:
  permissions:
    id-token: write
  environment:
    name: pypi
  steps:
    - uses: pypa/gh-action-pypi-publish@release/v1
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Token-based PyPI publish with long-lived secrets | OIDC Trusted Publishing via GitHub Actions | PyPA modern guidance era | Better release security and less secret management burden |
| Free-form release notes | Structured changelog + migration/deprecation sections | Mature OSS release practices | Faster integrator upgrade decisions |
| Legacy LangGraph prebuilt (`create_react_agent`) | LangChain `create_agent` with LangGraph runtime | LangGraph v1 | Migration docs must call out deprecated APIs explicitly |
| API docs as narrative-only markdown | OpenAPI-driven docs + generated client parity checks | FastAPI/OpenAPI-first workflows | Lower risk of contract drift |

**Deprecated/outdated:**
- Implicit migration communication ("breaking changes sprinkled across commits"): replace with dedicated migration guide and deprecation map.
- Token-only publish strategy for CI: replace with Trusted Publishing where possible.

## Open Questions

1. **What is the exact v1 deprecation removal target for `run()` alias and `langfuse_settings` behavior?**
   - What we know: `run()` logs deprecation and delegates; `langfuse_settings` is warned/ignored without callback.
   - What's unclear: Removal version/date commitment is not documented.
   - Recommendation: Define explicit deprecation horizon in `deprecation-map.md` during planning.

2. **Should `sdk/python` (generated HTTP client) receive its own migration guide section distinct from `agent-search-core`?**
   - What we know: It is versioned separately and generated from OpenAPI.
   - What's unclear: Whether DOC-01 major release scope includes this package or only `agent-search-core`.
   - Recommendation: Lock release scope in plan; if excluded, state that clearly in release notes.

3. **Do we require TestPyPI verification before tagging production `agent-search-core-v1.0.0`?**
   - What we know: Workflow currently supports PyPI publish path with trusted publishing.
   - What's unclear: Whether staged TestPyPI gate is mandatory for this repo.
   - Recommendation: Decide this in planning; if yes, add explicit pre-tag checklist task.

## Sources

### Primary (HIGH confidence)
- https://semver.org/spec/v2.0.0.html - semantic versioning major/minor/patch and deprecation implications.
- https://keepachangelog.com/en/1.0.0/ - changelog structure and deprecation/removal communication norms.
- https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/ - recommended PyPI publishing workflow with OIDC and artifact flow.
- https://docs.pypi.org/trusted-publishers/ - trusted publishing model and token lifetime/security details.
- https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-pypi - GitHub-side OIDC configuration constraints.
- https://docs.langchain.com/oss/python/migrate/langgraph-v1 - LangGraph v1 migration/deprecations.
- https://docs.langchain.com/oss/python/releases/langgraph-v1 - LangGraph v1 release notes context.
- https://docs.langchain.com/oss/python/release-policy - LangChain/LangGraph deprecation and major-release policy.
- https://docs.langchain.com/oss/python/versioning - versioning expectations and stability labels.
- https://fastapi.tiangolo.com/tutorial/metadata/ - OpenAPI/docs metadata practices.
- https://fastapi.tiangolo.com/tutorial/path-operation-configuration/ - endpoint-level docs/deprecated flags.
- https://peps.python.org/pep-0387/ - deprecation timeline and compatibility communication discipline.

### Secondary (MEDIUM confidence)
- Repo sources: `scripts/release_sdk.sh`, `.github/workflows/release-sdk.yml`, `scripts/validate_openapi.sh`, `scripts/update_sdk.sh`, `scripts/export_openapi.py`, `sdk/core/README.md`, `sdk/README.md`, `src/backend/main.py`, `src/backend/routers/agent.py`.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - backed by official SemVer, PyPA, FastAPI, and LangChain/LangGraph docs plus repo implementation.
- Architecture: HIGH - release/doc patterns verified by official guidance and existing project scripts/workflows.
- Pitfalls: MEDIUM - derived from common failure modes and current repo state; some are preventive rather than observed incidents.

**Research date:** 2026-03-12
**Valid until:** 2026-04-11 (30 days)
