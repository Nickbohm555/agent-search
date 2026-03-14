# Phase 5: Prompt Customization and Guidance - Research

**Researched:** 2026-03-13  
**Domain:** Prompt override contracts for subanswer/synthesis in FastAPI + SDK runtime  
**Confidence:** HIGH

## Summary

Phase 5 should be implemented as a contract-and-plumbing change, not a prompt-engineering rewrite. The current runtime hardcodes two prompt strings in `services/subanswer_service.py` and `services/initial_answer_service.py`, and those prompts are invoked indirectly through runtime nodes (`answer` and `synthesize`). The safest path is to add two explicit prompt override fields (`subanswer` and `synthesis`) in run request/config models, then thread those values into the two generation services while preserving existing citation and fallback guardrails.

For PRM-03, the SDK already has a `config` map pattern and a `RuntimeConfig.from_dict(...)` flow. Extend this with a nested, mutable `custom_prompts` map so SDK consumers can set client-level defaults once, and optionally override per call. This aligns with current architecture and avoids introducing a new SDK client abstraction in this phase.

Documentation work (PRM-04) should be treated as first-class acceptance criteria: define default prompt text, prompt scope/responsibility boundaries, precedence rules (defaults -> client map -> per-run override), and safety caveats. Guidance must explicitly state that prompt customization influences wording/strategy but does not bypass citation/fallback contracts enforced by runtime nodes.

**Primary recommendation:** Add a typed `custom_prompts` contract with two keys (`subanswer`, `synthesis`), propagate it end-to-end (API -> SDK config -> runtime services), and keep citation/fallback enforcement outside prompt text so safety behavior is invariant under overrides.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.12 | Run request contract exposure (`/api/agents/run`, `/run-async`) | Existing backend API surface and OpenAPI source |
| Pydantic | 2.10.6 | Prompt override model validation and aliasing | Existing request/config schema system across backend + SDK |
| langchain-openai / ChatOpenAI | >=0.3.0 | Prompt execution for subanswer/synthesis generation | Current LLM invocation path in both services |
| agent-search core SDK (`advanced_rag`) | internal package (`agent-search-core`) | Client-level config/default propagation | Existing supported SDK entrypoint already accepts config |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pytest | project standard | Contract + behavior regression tests | Verify prompt override influence and default compatibility |
| Vitest + Testing Library | vitest 2.1.9 / @testing-library/react 16.2.0 | Frontend/API payload tests (if UI fields are added) | Validate run payload includes prompt options without UI regressions |
| OpenAPI generated Python client | sdk/python current generated model set | HTTP SDK request shape parity | If Phase 5 extends API request schema in this milestone |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Typed `custom_prompts` model | Free-form `dict[str, Any]` prompt payload | Faster initially, but weak validation/docs and higher drift risk |
| Runtime-level prompt injection via node input/config | Environment variables only (`SUBANSWER_*`, `INITIAL_ANSWER_*`) | Env-only cannot satisfy per-run user overrides (PRM-01/02) |
| Extend existing SDK `config` contract | Introduce new SDK client class in Phase 5 | New class is larger scope and overlaps Phase 6 release-hardening work |

**Installation:**
```bash
# No new dependencies required for Phase 5 implementation.
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── backend/
│   ├── schemas/agent.py                  # Add prompt fields to run request models
│   ├── agent_search/config.py            # Add typed custom_prompts config section
│   ├── agent_search/public_api.py        # Parse/merge config defaults + per-run overrides
│   ├── routers/agent.py                  # Forward prompt fields into SDK config mapping
│   ├── services/subanswer_service.py     # Consume effective subanswer prompt
│   └── services/initial_answer_service.py# Consume effective synthesis prompt
├── sdk/core/src/agent_search/
│   ├── config.py                         # SDK-side config parser for custom_prompts map
│   └── public_api.py                     # Client-level mutable defaults + request-level override
└── docs/ and SDK READMEs                 # Prompt responsibilities, defaults, override precedence
```

### Pattern 1: Two-key prompt contract with explicit scope
**What:** Define only two prompt override keys: one for subanswer generation and one for final synthesis generation.  
**When to use:** Always for PRM-01/PRM-02 to prevent ambiguous prompt responsibilities.  
**Example:**
```python
# Source: project schema/config pattern (adapted)
class RuntimeCustomPrompts(BaseModel):
    subanswer: str | None = Field(default=None, min_length=1)
    synthesis: str | None = Field(default=None, min_length=1)
```

### Pattern 2: Effective prompt resolution with precedence
**What:** Resolve prompt text via deterministic precedence: built-in defaults -> SDK mutable defaults map -> per-run request override.  
**When to use:** SDK and API entrypoints before runtime invocation.  
**Example:**
```python
# Source: existing RuntimeConfig.from_dict + config propagation pattern (adapted)
effective_subanswer_prompt = (
    run_config.custom_prompts.subanswer
    or sdk_client_defaults.custom_prompts.get("subanswer")
    or DEFAULT_SUBANSWER_PROMPT
)
```

### Pattern 3: Guardrails outside prompts
**What:** Keep citation and support checks in runtime nodes/services, not only inside prompt instructions.  
**When to use:** Always; prevents prompt overrides from silently bypassing quality constraints.  
**Example:**
```python
# Source: existing runtime node contracts
if missing_citations:
    return AnswerSubquestionNodeOutput(
        sub_answer="nothing relevant found",
        answerable=False,
        verification_reason="missing_citation_markers",
    )
```

### Anti-Patterns to Avoid
- **Single free-form mega-prompt field:** Do not use one prompt to control both subanswer and synthesis behavior.
- **Prompt-only safety assumptions:** Do not rely on prompt wording alone for citation enforcement.
- **Global mutable defaults hidden in module state:** Do not make unscoped global prompt overrides that leak across tests/runs.
- **Undocumented precedence rules:** Do not ship prompt overrides without explicit "who wins" documentation.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request/config parsing for prompt maps | Manual nested dict parsing in handlers | Pydantic models with typed fields | Central validation + OpenAPI schema + fewer edge-case bugs |
| API key shape translation (`custom-prompts` JSON) | Custom serializer/deserializer code | Pydantic field aliasing (`alias`, `validation_alias`) | Official, tested alias handling for hyphenated keys |
| Mutable defaults behavior | Shared mutable dict literals across instances | `Field(default_factory=dict)` for maps | Predictable instance isolation and clear intent |
| Citation safety in synthesis | Prompt post-processing heuristics only | Existing node-level contract enforcement | Runtime already validates citation indices against available rows |

**Key insight:** Prompt customization should alter instruction text, not contract invariants. Keep contracts (citations/fallbacks/shape) in code paths that are independent of user prompts.

## Common Pitfalls

### Pitfall 1: Prompt override added but not threaded into runtime calls
**What goes wrong:** Request accepts override fields, but services still use hardcoded prompt strings.  
**Why it happens:** Plumbing stops at API/SDK model layer; runtime node/service signatures are unchanged.  
**How to avoid:** Add tests that assert passed prompt text reaches `generate_subanswer` and `generate_final_synthesis_answer` callsites.  
**Warning signs:** API accepts prompt fields, but outputs are identical to baseline in deterministic fixtures.

### Pitfall 2: Prompt override weakens citation behavior unexpectedly
**What goes wrong:** Model responses become uncited or use invalid citation indices after override.  
**Why it happens:** Override text omits citation instructions and no code-level fallback check exists at the same layer.  
**How to avoid:** Keep existing `answer` and `synthesize` node citation enforcement unchanged; test override prompts that intentionally omit citation wording.  
**Warning signs:** Increased `missing_citation_markers` or `missing_supporting_source_rows` fallback rates.

### Pitfall 3: Mutable defaults leak between SDK runs/tests
**What goes wrong:** One test/user mutates prompt defaults and subsequent runs inherit unintended values.  
**Why it happens:** Shared mutable object reused globally without controlled merge/reset behavior.  
**How to avoid:** Use per-instance maps (`default_factory=dict`) and explicit copy/merge semantics at call boundaries.  
**Warning signs:** Flaky tests with order-dependent prompt behavior.

### Pitfall 4: Alias mismatch for `custom-prompts` vs `custom_prompts`
**What goes wrong:** One surface sends hyphenated key while another expects snake_case; overrides are silently ignored.  
**Why it happens:** Inconsistent alias settings (`by_alias`/`validate_by_name`) across models/serialization.  
**How to avoid:** Define one canonical internal field (`custom_prompts`) and explicit alias for external JSON keys where needed; add integration tests for both API and SDK paths.  
**Warning signs:** Request payload contains prompt map but backend resolved config shows `None` prompts.

## Code Examples

Verified/adapted patterns for this phase:

### Add prompt overrides to run request model
```python
# Source: current schemas/agent.py pattern + Pydantic field docs (adapted)
class RuntimeAgentRunRequest(BaseModel):
    query: str = Field(min_length=1)
    thread_id: str | None = None
    custom_prompts: dict[str, str] | None = Field(
        default=None,
        validation_alias="custom-prompts",
        serialization_alias="custom-prompts",
    )
```

### Resolve effective prompts in SDK/public API
```python
# Source: existing advanced_rag config flow (adapted)
runtime_config = RuntimeConfig.from_dict(config)
effective_prompts = {
    "subanswer": (
        runtime_config.custom_prompts.subanswer
        or sdk_prompt_defaults.get("subanswer")
        or DEFAULT_SUBANSWER_PROMPT
    ),
    "synthesis": (
        runtime_config.custom_prompts.synthesis
        or sdk_prompt_defaults.get("synthesis")
        or DEFAULT_SYNTHESIS_PROMPT
    ),
}
```

### Pass effective prompts to generation services
```python
# Source: existing node -> service call pattern (adapted)
generated_sub_answer = generate_subanswer(
    sub_question=node_input.sub_question,
    reranked_retrieved_output=reranked_output,
    prompt_template=effective_prompts["subanswer"],
    callbacks=callbacks,
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded prompt strings in services | Typed prompt contracts with per-run/per-client overrides | Planned in Phase 5 | Enables safe customization without changing default behavior |
| Env-only behavior tuning | Request/config-driven runtime behavior | Introduced in earlier phases for runtime controls; extended in Phase 5 | Better multi-tenant and per-run flexibility |
| Implicit prompt ownership | Explicit "subanswer vs synthesis" responsibility docs | Planned in Phase 5 docs work | Reduces misuse and support burden |

**Deprecated/outdated:**
- Treating prompt text as unchangeable internals only.
- Using undocumented prompt tweaks as implicit integration behavior.

## Open Questions

1. **Exact SDK "client-level" surface for mutable defaults**
   - What we know: SDK currently exposes function-based APIs (`advanced_rag`, `run_async`) with `config` dict.
   - What's unclear: Whether Phase 5 should add a formal SDK client object now or represent "client-level" as a reusable mutable map passed into calls.
   - Recommendation: In Phase 5, implement mutable defaults map in existing config workflow; defer new class abstraction unless required by Phase 6 release criteria.

2. **External key naming for docs/examples**
   - What we know: Requirement text uses `custom-prompts` (hyphenated).
   - What's unclear: Whether all surfaces (Python SDK, REST JSON, frontend TS) should expose hyphenated key, snake_case, or both.
   - Recommendation: Support both for input validation where practical, document one canonical external form (`custom-prompts`) and one internal form (`custom_prompts`).

3. **Frontend scope in this phase**
   - What we know: Success criteria require users and SDK consumers to provide custom prompts; frontend requirement is not explicit.
   - What's unclear: Whether "users" implies app UI controls now or API/SDK users only.
   - Recommendation: Treat API/SDK as required; make frontend prompt fields optional unless explicitly required in phase planning.

## Sources

### Primary (HIGH confidence)
- Project codebase:
  - `src/backend/services/subanswer_service.py` - hardcoded subanswer prompt and call path.
  - `src/backend/services/initial_answer_service.py` - hardcoded synthesis prompt and final synthesis wrapper.
  - `src/backend/agent_search/runtime/nodes/answer.py` - citation contract enforcement for subanswers.
  - `src/backend/agent_search/runtime/nodes/synthesize.py` - citation contract enforcement/fallback for final answer.
  - `src/backend/schemas/agent.py` - current run request model shape.
  - `src/backend/routers/agent.py` - REST payload to SDK config mapping point.
  - `src/backend/agent_search/public_api.py` and `sdk/core/src/agent_search/public_api.py` - existing config entrypoints and SDK behavior.
  - `src/backend/agent_search/config.py` and `sdk/core/src/agent_search/config.py` - runtime config parser pattern.
  - `src/backend/pyproject.toml` and `sdk/core/pyproject.toml` - dependency/version baseline.

### Secondary (MEDIUM confidence)
- [Pydantic Fields](https://docs.pydantic.dev/latest/concepts/fields/) - `default_factory`, mutable defaults behavior, field alias usage.
- [Pydantic Alias](https://docs.pydantic.dev/latest/concepts/alias/) - alias/validation/serialization precedence and config behavior.
- [FastAPI Body - Nested Models](https://fastapi.tiangolo.com/tutorial/body-nested-models/) - nested request body modeling and dict handling.
- [FastAPI Body - Fields](https://fastapi.tiangolo.com/tutorial/body-fields/) - using `Field` for validation/schema metadata.
- [LangChain ChatOpenAI integration docs](https://docs.langchain.com/oss/python/integrations/chat/openai) - current `invoke(...)` usage patterns for chat model calls.

### Tertiary (LOW confidence)
- [WebSearch synthesis: OpenAI prompt best-practice pages](https://platform.openai.com/docs/guides/gpt-best-practices) - directional guidance for safe prompt defaults; should be re-checked during implementation if policy-sensitive behavior is added.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - grounded in repository manifests and active code paths.
- Architecture: HIGH - directly derived from existing runtime/service/SDK layering.
- Pitfalls: HIGH - based on concrete current contracts (citation enforcement, config propagation) plus official model/alias docs.

**Research date:** 2026-03-13  
**Valid until:** 2026-04-12

