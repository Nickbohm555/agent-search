# Phase 01: Contract Foundation and Compatibility Baseline - Research

**Researched:** 2026-03-13  
**Domain:** Backward-compatible API contract evolution for runtime controls and additive response fields  
**Confidence:** HIGH (repo and framework behavior), MEDIUM (final control field naming choices)

## Summary

Phase 01 should be implemented as a pure contract-evolution phase: add optional request/response fields, keep all existing required fields and endpoint paths unchanged, and preserve current runtime behavior when new fields are omitted. In this codebase, the existing API and runtime are strongly schema-driven (`src/backend/schemas/agent.py`, FastAPI `response_model`, frontend runtime type guards, generated SDK models), so the safest plan is additive-only Pydantic model changes plus explicit mapping logic.

The main planning-critical gap is that per-run controls are not currently threaded through execution. API requests currently carry only `query` and `thread_id`, router config forwarding only includes `thread_id`, and async resume reconstructs payload from `job.query` and `job.thread_id` only. If Phase 01 adds control fields but does not persist and propagate them through jobs/resume paths, controls will be accepted at the HTTP edge but silently dropped during async/retry flows.

Use optional nested control objects in `RuntimeAgentRunRequest`, parse them into `RuntimeConfig`-compatible structures, and preserve defaults that match current behavior. Add `sub_answers` as an additive response alias while retaining `sub_qa` and `output` contract guarantees.

**Primary recommendation:** implement additive nested request controls + additive response `sub_answers`, with explicit default-off HITL and full sync/async payload propagation so omitted fields produce exactly current behavior.

## Standard Stack

The established libraries/tools for this phase:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | `0.115.12` | HTTP contracts and OpenAPI generation | Existing backend router + `response_model` filtering and schema generation |
| Pydantic | `2.10.6` | Request/response model validation | Current contract layer uses Pydantic models; defaults/optionality drive compatibility |
| OpenAPI (via FastAPI) | `3.1.0` output | Contract artifact for clients | `openapi.json` is source for generated Python HTTP SDK |
| Existing runtime config module (`agent_search.config`) | repo-local | Runtime config parsing/defaulting | Already supports nested config parsing with safe fallback on invalid values |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| OpenAPI Generator client (`sdk/python`) | generated | External HTTP client contract mirror | Regenerate whenever request/response schemas change |
| Frontend runtime validators (`src/frontend/src/utils/api.ts`) | repo-local | Runtime safety for browser client | Verify additive response fields do not break existing guards |
| SDK core mirror (`sdk/core/src/schemas/agent.py`) | repo-local | In-process SDK schema parity | Mirror backend schema changes to avoid drift |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Nested `controls` object in request | Flat top-level flags | Flat fields are simpler short-term but increase drift/noise and make future grouping/versioning harder |
| Additive `sub_answers` while keeping `sub_qa` | Rename/replace `sub_qa` | Rename is breaking for frontend + SDK + tests; additive alias preserves compatibility |

**Installation:**
```bash
# No new dependencies required for Phase 01.
# Use existing FastAPI/Pydantic/OpenAPI toolchain.
```

## Architecture Patterns

### Recommended Project Structure
```text
src/backend/
├── schemas/agent.py                  # Request/response schema additions
├── routers/agent.py                  # Request-to-config mapping for sync/async
├── agent_search/public_api.py        # RuntimeConfig resolution from request controls
├── agent_search/runtime/jobs.py      # Persist and replay full request (including controls)
└── services/agent_service.py         # Response mapping adds additive sub_answers
```

### Pattern 1: Additive Request Envelope with Optional Nested Controls
**What:** Extend `RuntimeAgentRunRequest` with optional nested control sections for rerank/query-expansion/HITL.  
**When to use:** Contract phases where old clients must keep working unchanged.  
**Example:**
```python
# Source: project schema pattern in src/backend/schemas/agent.py
class RuntimeAgentRunControls(BaseModel):
    rerank: RuntimeRerankControl | None = None
    query_expansion: RuntimeQueryExpansionControl | None = None
    hitl: RuntimeHitlControl | None = None

class RuntimeAgentRunRequest(BaseModel):
    query: str = Field(min_length=1)
    thread_id: str | None = None
    controls: RuntimeAgentRunControls | None = None  # additive, optional
```

### Pattern 2: Single Mapping Point from API Request to Runtime Config
**What:** Map request controls to one config dict object used by both sync and async paths.  
**When to use:** Any per-run controls that must survive queue/resume/retry.  
**Example:**
```python
# Source: existing _build_thread_config pattern in src/backend/routers/agent.py
def _build_run_config(payload: RuntimeAgentRunRequest) -> dict[str, Any] | None:
    config: dict[str, Any] = {}
    if payload.thread_id is not None:
        config["thread_id"] = payload.thread_id
    if payload.controls is not None:
        # map controls -> runtime config sections
        config.update(payload.controls.to_runtime_config_dict())
    return config or None
```

### Pattern 3: Additive Response Alias for Compatibility
**What:** Add `sub_answers` while retaining existing `sub_qa`.  
**When to use:** Transitional contract phases before deprecating legacy fields.  
**Example:**
```python
# Source: response assembly in services/agent_service.py
response = RuntimeAgentRunResponse(
    main_question=rag_state["main_question"],
    sub_qa=[item.model_copy(deep=True) for item in rag_state["sub_qa"]],
    sub_answers=[item.model_copy(deep=True) for item in rag_state["sub_qa"]],  # additive alias
    output=output,
    final_citations=final_citations,
)
```

### Anti-Patterns to Avoid
- **Edge-only acceptance:** accepting new request flags in router but not persisting them through `runtime/jobs.py` resume/replay paths.
- **Breaking rename:** replacing `sub_qa` with `sub_answers` in-place.
- **Implicit default changes:** defaulting new HITL flag to enabled.
- **Schema-only update:** changing backend schema without frontend validators + SDK mirror updates.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request validation | Manual dict parsing in router/service | Pydantic nested models + field validators | Centralizes defaults and validation errors, keeps OpenAPI in sync |
| Compatibility filtering | Custom response filtering logic | FastAPI `response_model` + Pydantic models | Framework already guarantees output shape/documentation behavior |
| Optional/required semantics | Custom required-field logic | JSON Schema/OpenAPI `required` semantics generated by FastAPI | Tooling and SDK generation already depend on this behavior |
| SDK contract propagation | Hand-edit generated SDK files | `scripts/export_openapi.py` + `scripts/generate_sdk.sh` workflow | Prevents drift and accidental mismatch |

**Key insight:** this phase is contract plumbing; leverage the existing schema/OpenAPI generation pipeline instead of custom compatibility code.

## Common Pitfalls

### Pitfall 1: Controls accepted but dropped in async resume path
**What goes wrong:** controls appear to work for initial request but disappear after pause/resume or replay.  
**Why it happens:** `resume_agent_run_job()` rebuilds `RuntimeAgentRunRequest` from only `query` and `thread_id`.  
**How to avoid:** store full normalized request payload in `AgentRunJobStatus` and reconstruct from that.  
**Warning signs:** resumed run logs show default config despite non-default request controls.

### Pitfall 2: Default behavior changes unintentionally
**What goes wrong:** old clients observe changed runtime behavior when omitting new fields.  
**Why it happens:** new fields default to enabled values (especially HITL).  
**How to avoid:** explicit default-off for HITL and default-preserving values for rerank/query-expansion.  
**Warning signs:** baseline tests fail when posting `{ "query": "..." }`.

### Pitfall 3: Contract drift across backend, frontend, and SDK
**What goes wrong:** backend accepts/returns fields that clients do not model consistently.  
**Why it happens:** schema updates made only in backend without regenerating OpenAPI SDK and updating TS guards.  
**How to avoid:** treat `src/backend/schemas`, `openapi.json`, `sdk/python`, `sdk/core`, and `src/frontend/src/utils/api.ts` as one change set.  
**Warning signs:** generated client tests or frontend shape guards fail after backend schema update.

### Pitfall 4: Idempotency/replay key behavior shifts unexpectedly
**What goes wrong:** idempotent replay cache misses spike after contract changes.  
**Why it happens:** request hashing includes model-dumped payload; additive fields can alter hash shape.  
**How to avoid:** normalize hashing input intentionally (documented include/exclude strategy) before rollout.  
**Warning signs:** duplicate effects for logically same request after deployment.

## Code Examples

Verified patterns from official sources and current code:

### Pydantic extra-data compatibility baseline
```python
# Source: https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra
class Model(BaseModel):
    model_config = ConfigDict(extra="ignore")  # default behavior
```

### FastAPI response model filtering
```python
# Source: https://fastapi.tiangolo.com/tutorial/response-model/
@router.post("/run", response_model=RuntimeAgentRunResponse)
def runtime_agent_run(payload: RuntimeAgentRunRequest) -> RuntimeAgentRunResponse:
    ...
```

### OpenAPI/JSON Schema required-property model
```json
// Source: https://json-schema.org/understanding-json-schema/reference/object#required-properties
{
  "type": "object",
  "properties": {
    "query": { "type": "string" },
    "controls": { "type": "object" }
  },
  "required": ["query"]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Env-only runtime toggles (`RERANK_*`, `QUERY_EXPANSION_*`) | Per-run request controls plus env defaults | Planned in Phase 01 | Enables contract-driven behavior without breaking existing callers |
| Single legacy `sub_qa` output surface | Dual surface: `sub_qa` (legacy) + additive `sub_answers` | Planned in Phase 01 | Preserves old clients while enabling HITL-oriented response shape |
| Thread-only request config mapping | Unified run-config mapping from request controls | Planned in Phase 01 | Ensures sync/async/retry consistency |

**Deprecated/outdated:**
- Request contracts that rely only on top-level `query` and `thread_id` for all future runtime control needs.

## Open Questions

1. **Exact `query_expansion` control schema for Phase 01**
   - What we know: requirement mandates accepting query-expansion flags per run.
   - What's unclear: whether Phase 01 needs only `enabled` or also tunables (`max_queries`, model, etc.).
   - Recommendation: lock to minimal `enabled` (+ optional safe tunables) and defer advanced knobs to later phase.

2. **`sub_answers` payload shape**
   - What we know: must be additive and not break required fields.
   - What's unclear: should `sub_answers` duplicate full `SubQuestionAnswer` or expose a narrower HITL-focused type.
   - Recommendation: use same shape as `SubQuestionAnswer` in Phase 01 to minimize mapper complexity and drift.

3. **Idempotency hash normalization policy**
   - What we know: payload hashing is request-shape-sensitive.
   - What's unclear: whether changing hash semantics for additive defaults is acceptable in this release.
   - Recommendation: decide explicitly and add regression test for unchanged behavior when controls omitted.

## Sources

### Primary (HIGH confidence)
- Repository contracts and flow:
  - `src/backend/schemas/agent.py`
  - `src/backend/routers/agent.py`
  - `src/backend/agent_search/public_api.py`
  - `src/backend/agent_search/config.py`
  - `src/backend/agent_search/runtime/jobs.py`
  - `src/backend/services/agent_service.py`
  - `src/frontend/src/utils/api.ts`
  - `openapi.json`
  - `sdk/core/src/schemas/agent.py`
  - `sdk/python/openapi_client/models/runtime_agent_run_request.py`
  - `sdk/python/openapi_client/models/runtime_agent_run_response.py`
- Official docs:
  - [Pydantic Config `extra`](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra)
  - [Pydantic model extra-data behavior](https://docs.pydantic.dev/latest/concepts/models/#extra-data)
  - [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/)
  - [OpenAPI 3.1 Schema Object](https://spec.openapis.org/oas/v3.1.0#schema-object)
  - [JSON Schema object required properties](https://json-schema.org/understanding-json-schema/reference/object#required-properties)

### Secondary (MEDIUM confidence)
- `sdk/README.md` update workflow (`export_openapi` -> `validate_openapi` -> `generate_sdk`) used as operational contract guidance.

### Tertiary (LOW confidence)
- General web discussions on API compatibility classification (not used as primary decision authority).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - directly verified in repo dependency and schema/runtime files.
- Architecture patterns: HIGH - traced across router, public API, runtime jobs, and response mapping.
- Pitfalls: HIGH - observed in concrete code paths (especially async resume payload reconstruction).

**Research date:** 2026-03-13  
**Valid until:** 2026-04-12 (or until request/response schema/runtime job flow changes)
