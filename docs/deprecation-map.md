# Deprecation Map

This map defines which legacy `agent-search` surfaces are deprecated, which replacement path is supported for `1.0.0`, and what "Removal" means operationally for each item. Use it with the [Migration Guide](migration-guide.md) when scheduling upgrades.

## Status Semantics

| Status | Operational meaning |
|---|---|
| Supported | Primary, documented path for current integrations and new work. |
| Deprecated | Still callable in `1.0.0`, but documentation, examples, and support expectations point to the replacement path. |
| Unsupported | Not part of the public contract. It may still exist internally, but consumers should treat it as unsafe to depend on. |
| Removed | The compatibility surface is no longer callable or documented for production use. |

## Removal Semantics

When a row reaches **Removed**, that means one or more concrete compatibility surfaces are gone:

- Deprecated endpoint removed from FastAPI router surface.
- Deprecated SDK alias removed from `agent_search` public exports.
- Compatibility shim removed from runtime wiring or tracing setup.
- Legacy behavior removed from release docs and migration guidance.

## Deprecated Flow Map

| Deprecated flow | Status | Replacement | Removal horizon | Operational notes |
|---|---|---|---|---|
| `agent_search.run(...)` sync alias | Deprecated | `agent_search.advanced_rag(...)` | Earliest removal: next SemVer-major after `1.0.0` | `run()` still delegates to `advanced_rag()` and logs a deprecation warning. Removal means the alias disappears from public exports and SDK docs. |
| `langfuse_settings` without `langfuse_callback` | Deprecated | `build_langfuse_callback(...)` plus `advanced_rag(..., langfuse_callback=...)` | Earliest removal: next SemVer-major after `1.0.0` | Settings-only behavior is already non-functional for tracing in `1.0.0`; the runtime warns and leaves tracing disabled. Removal means the compatibility argument path is deleted. |
| Legacy orchestration as the primary programming model | Deprecated for external guidance | LangGraph-native runtime state graph and public SDK/API contracts | Effective immediately in `1.0.0` docs; internal removal scheduled with future runtime cleanup work | Legacy orchestration language should not appear in new integration code or migration guidance. Internal compatibility code may remain temporarily, but it is not a supported external contract. |
| Private runtime modules or router internals as integration dependencies | Unsupported | Public exports from `agent_search` and documented `/api/agents/*` routes | No compatibility guarantee; treat as removable in any future release | This includes direct dependence on internal runtime modules, builder internals, or undocumented route shapes. Removal means private imports or undocumented hooks can change or vanish without migration shims. |

## Support Notes

### Deprecated

- Deprecated paths are still observable in `1.0.0`, but only as transition aids for existing adopters.
- Bug fixes and examples should target the replacement path, not the deprecated one.
- New integrations should not start on deprecated surfaces.

### Unsupported

- Unsupported paths are outside the compatibility contract even if repository code still references them internally.
- If you rely on unsupported internals today, migrate before taking further version upgrades.

## Migration Order

1. Replace `run(...)` with `advanced_rag(...)`.
2. Move tracing setup from `langfuse_settings` to `langfuse_callback`.
3. Remove any dependency on private runtime modules or undocumented router behavior.
4. Re-verify the public contract using the checks in the [Migration Guide](migration-guide.md).

## Verify Current State

```bash
rg "deprecated|advanced_rag|langfuse_callback|langfuse_settings" src/backend/agent_search/public_api.py
rg "/api/agents/run|/api/agents/run-async|/api/agents/run-status|/api/agents/run-resume|/api/agents/run-cancel" src/backend/routers/agent.py
rg "Migration Guide|Deprecation Map" docs/releases/1.0.0-langgraph-migration.md README.md
```
