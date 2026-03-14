# Feature Research

**Domain:** Developer-facing HITL-enabled advanced RAG workflow (backend API + frontend UX + SDK + PyPI docs)
**Researched:** 2026-03-13
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Explicit HITL decisions (`approve` / `edit` / `reject`) for risky agent actions | LangChain HITL documents these as core decision types, so developers expect this vocabulary and flow | MEDIUM | Baseline contract for backend, frontend, and SDK; do not rename semantics per surface. |
| Durable pause/resume with thread-scoped state | HITL requires pausing execution and resuming later; users expect no lost context | MEDIUM | Depends on persistent checkpointer + stable `thread_id` usage across API/SDK calls. |
| Step-level HITL policy with safe bypass (`interrupt_on` true/false and allowed decisions) | Teams need both strict-review paths and fast no-HITL paths in the same product | MEDIUM | Critical for milestone requirement to keep default behavior unchanged for existing users. |
| Frontend review UX for pending actions (show proposed payload, allow approve/edit/reject) | Review without context is unusable; operators expect a clear decision console | MEDIUM | Must mirror backend review config and preserve decision ordering when multiple actions pause. |
| Typed run lifecycle events for paused/resumed/completed states | Existing staged async workflows already expose run progress; HITL must integrate into same event model | MEDIUM | SSE/WebSocket events should include interrupt metadata and decision outcomes for auditability. |
| API/SDK surface for submitting decisions and resuming execution | Developer-facing products are expected to be automatable, not UI-only | MEDIUM | Include typed request/response models and helpers for multi-decision resume payloads. |
| Output contract includes `sub_answers` in final run artifact | Developers integrating RAG workflows expect inspectable intermediate reasoning artifacts | LOW | Should be backward compatible: additive field, no contract break for existing consumers. |
| Published docs for PyPI + API + frontend workflow (install, configure, no-HITL defaults, HITL examples) | Developer trust depends on copy-pasteable docs and migration guidance | LOW | Must include "default unchanged" migration note and end-to-end examples for approve/edit/reject. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Targeted HITL gates on subquestion proposal and query expansion (instead of global pauses) | Gives review power where quality risk is highest without slowing every run | MEDIUM | Depends on clear stage boundaries in runtime graph and stage-specific review payload schemas. |
| Query expansion toggle + rerank toggle exposed consistently (UI, API, SDK) | Enables controlled quality/cost tradeoffs per run and cleaner experimentation | LOW | Must preserve previous defaults when omitted; pair with run metadata for later analysis. |
| Prompt customization for subanswer and final synthesis with guardrails | Lets teams adapt domain behavior without forking code paths | MEDIUM | Depends on prompt registry/versioning + validation to prevent malformed runtime prompts. |
| Diff-first review UX for edits (before/after arguments or expanded queries) | Reduces operator error and accelerates approval throughput | MEDIUM | Builds on base approve/edit/reject flow; especially useful for query expansion review. |
| SDK "single-call + callbacks" helper for interrupt handling | Improves DX by minimizing manual thread/interrupt plumbing in client code | MEDIUM | Wraps invoke/stream + resume semantics while preserving explicit low-level APIs. |
| Documentation bundles by persona (backend integrator, frontend operator, SDK user) | Cuts onboarding time and support load by showing the same feature from each interface | LOW | Can be shipped incrementally; highest ROI docs include migration snippets and failure modes. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Enabling HITL by default for all existing users | "Safer by default" sounds appealing | Breaks current behavior and increases latency/friction unexpectedly | Keep current default path unchanged; opt-in HITL per workspace/request/policy |
| "Edit anything" without constraints | Maximizes operator flexibility | Large edits can destabilize agent planning and trigger repeated tool calls | Allow conservative edits only; validate shape and maintain action intent |
| Silent auto-approval fallback when review UI/API is unavailable | Avoids blocked runs | Hides risk and undermines trust/compliance expectations | Use explicit timeout policy: fail-safe reject or configured bypass with audit event |
| Divergent schemas across UI/API/SDK for the same decision object | Teams optimize each surface separately | Creates integration bugs and documentation drift | One canonical decision schema shared across backend models and SDK types |
| Shipping prompt customization without versioning/audit trail | Fast initial implementation | Makes regressions hard to trace and roll back | Version prompts, log selected prompt IDs, and allow per-run override metadata |

## Feature Dependencies

```text
[Persistent checkpoints + thread_id discipline]
    └──requires──> [Pause/resume API contract]
                       └──enables──> [approve/edit/reject decision flow]
                       └──enables──> [targeted HITL on subquestion/query-expansion stages]

[Canonical decision schema]
    └──requires──> [Backend validation models]
                       └──enables──> [Frontend decision UI]
                       └──enables──> [SDK typed decision helpers]

[Stage lifecycle events]
    └──requires──> [staged async runtime integration]
                       └──enables──> [interrupt surfaced in UI]
                       └──enables──> [auditable pause/resume timeline]

[Query expansion + rerank toggles]
    └──requires──> [request-level config plumbing]
                       └──conflicts──> [hardcoded global defaults]

[Prompt customization]
    └──requires──> [prompt registry/versioning]
                       └──enables──> [subanswer customization]
                       └──enables──> [final synthesis customization]

[Output contract: sub_answers]
    └──requires──> [stable subanswer aggregation]
                       └──must remain additive to──> [existing response schema]
```

### Dependency Notes

- **Pause/resume depends on checkpoint durability:** without persisted state and stable `thread_id`, HITL cannot reliably resume.
- **Targeted HITL depends on stage identity:** subquestion and query-expansion review need explicit stage boundaries and payload contracts.
- **No-HITL compatibility depends on policy defaults:** default request path must keep `interrupt_on` off unless explicitly enabled.
- **Prompt customization depends on versioned prompt definitions:** unversioned free-text prompts make regression analysis and rollback fragile.
- **`sub_answers` depends on additive schema evolution:** return shape should add fields without changing required existing fields.

## MVP Definition

### Launch With (v1)

Minimum viable product - what's needed to validate the concept.

- [x] Approve/edit/reject decision contract and resume API for HITL actions.
- [x] Opt-in HITL at subquestion proposal and query expansion stages, with no-HITL default preserved.
- [x] Query expansion toggle and rerank toggle exposed in backend API and frontend controls.
- [x] Prompt customization inputs for subanswer and final synthesis with basic validation.
- [x] Additive output contract including `sub_answers`.
- [x] Updated SDK + PyPI docs covering enable/disable HITL paths and decision payload examples.

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Diff-first edit UX and batch decision handling for multiple simultaneous interrupts.
- [ ] Rich policy presets (e.g., approve-only vs approve/reject) by stage and environment.
- [ ] Interrupt analytics dashboard (approval rate, edit rate, rejection reasons by stage).

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Role-based reviewer routing and escalation workflows for enterprise governance.
- [ ] A/B experimentation framework for prompt variants tied to quality metrics.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Approve/edit/reject decision contract | HIGH | MEDIUM | P1 |
| Durable pause/resume with `thread_id` | HIGH | MEDIUM | P1 |
| Stage-scoped HITL (subquestion + query expansion) | HIGH | MEDIUM | P1 |
| No-HITL default compatibility path | HIGH | LOW | P1 |
| Query expansion + rerank toggles | HIGH | LOW | P1 |
| Prompt customization (subanswer + synthesis) | MEDIUM | MEDIUM | P1 |
| Additive `sub_answers` response field | HIGH | LOW | P1 |
| SDK helper for interrupt handling | MEDIUM | MEDIUM | P2 |
| Diff-first/batch decision UX | MEDIUM | MEDIUM | P2 |
| Interrupt analytics | MEDIUM | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Competitor A (LangChain/LangGraph HITL baseline) | Competitor B (custom in-house RAG flows) | Our Approach |
|---------|---------------------------------------------------|-------------------------------------------|--------------|
| Decision model | Explicit `approve` / `edit` / `reject` decisions | Often ad hoc approve-only patterns | Adopt explicit three-decision model end-to-end |
| Pause/resume semantics | Checkpointer + `thread_id` required for safe resume | Frequently process-memory only, brittle across restarts | Persisted thread-scoped resume in API/SDK |
| Per-action policy control | `interrupt_on` supports true/false and allowed decisions | Typically global on/off toggles | Stage-scoped policies with default-off compatibility |
| Multiple pending actions | Decision ordering and per-action responses are defined | Usually ambiguous batching behavior | Deterministic ordering + optional batch tooling |
| Docs posture | Official examples for middleware and interrupt resume | Usually sparse internal docs | Persona-based docs for backend, frontend, SDK, and PyPI |

## Sources

- [LangChain Human-in-the-Loop Middleware](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) (HIGH, primary)
- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) (HIGH)
- [FastAPI Features (OpenAPI + automatic docs)](https://fastapi.tiangolo.com/features/) (HIGH)
- [Python Packaging User Guide - Packaging Python Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/) (HIGH)

---
*Feature research for: HITL-enabled advanced RAG workflow milestone (subquestion/query-expansion review, toggles, prompt customization, additive output contract)*
*Researched: 2026-03-13*
