# Project Research Summary

**Project:** Agent Search HITL + Prompt Customization Milestone
**Domain:** Brownfield advanced RAG enhancement with opt-in human checkpoints, prompt controls, and synchronized API/UI/SDK contracts
**Researched:** 2026-03-13
**Confidence:** HIGH

## Executive Summary

This is a brownfield product enhancement, not a platform rewrite. The core product remains a FastAPI + React + Python SDK advanced RAG workflow, and the milestone adds optional human-in-the-loop (HITL) checkpoints at two high-leverage points: subquestion generation and query expansion. Expert guidance converges on a contract-first approach: keep existing non-HITL behavior unchanged, add explicit approve/edit/reject semantics, and make pause/resume durable through checkpoint persistence and stable run identity.

The recommended implementation path is additive and cross-surface synchronized. Standardize one canonical decision schema, project it consistently through backend models, frontend event handling, and SDK types, and stream typed lifecycle/checkpoint events over SSE. Pair this with explicit toggle and prompt precedence resolution so query-expansion/rerank controls and prompt overrides behave deterministically across all clients.

Primary risks are identity drift during resume, decision-order mismatches in multi-action interrupts, idempotency failures on replay, and contract drift between backend and SDK/UI releases. Mitigation is straightforward and opinionated: strict `thread_id`/`job_id`/`checkpoint_id` continuity, deterministic ordered decision validation, idempotency keys around side effects, compatibility tests against N-1 clients, and release gating that couples backend contract changes to SDK/PyPI publication.

## Key Findings

### Recommended Stack

Research strongly favors keeping the existing architecture and adopting HITL primitives directly from LangChain/LangGraph guidance. FastAPI native SSE, Postgres-backed checkpointing, and typed schemas are foundational for safe pause/resume and cross-surface consistency. Version constraints should stay conservative to avoid simultaneous migration risk while enabling the needed features.

**Core technologies:**
- `Python 3.12.x` (`>=3.11,<3.14` support): backend + SDK runtime baseline — matches current repo constraints while staying on a mature ecosystem line.
- `LangChain >=1.2,<2` + `LangGraph >=1.0.10,<2`: HITL middleware + interrupt semantics — canonical model for approve/edit/reject + durable resume.
- `langgraph-checkpoint-postgres >=3.0.4,<4`: persisted checkpoints — required for resume across async review delays and restarts.
- `FastAPI >=0.135,<0.136` + `Pydantic >=2.10,<3`: typed API + native SSE transport — contract stability and evented UI integration.
- `React 18.x` + TypeScript `5.8+`: review UX + typed event handling — safer evolution of pause/resume controls.

### Expected Features

The launch bar is clear: ship a complete opt-in HITL loop that works consistently in backend API, frontend UX, and SDK. That includes stage-scoped checkpoints, decision submission/resume endpoints, typed lifecycle events, additive `sub_answers`, query-expansion/rerank controls, and prompt customization for subanswer + synthesis. Behavior when HITL is off must remain backward compatible by default.

**Must have (table stakes):**
- Explicit `approve` / `edit` / `reject` decision contract with durable pause/resume.
- Stage-scoped HITL at `subquestions` and `query_expansion` with default-off compatibility.
- Typed run/checkpoint events and usable review UI for pending actions.
- API + SDK parity for decision submission and resume payloads.
- Additive `sub_answers` output + docs for no-HITL and HITL usage paths.

**Should have (competitive):**
- Diff-first edit review UX to reduce operator error and speed approvals.
- SDK convenience helpers/callback patterns for interrupt handling.
- Persona-based docs (backend integrator, frontend operator, SDK consumer).

**Defer (v2+):**
- Reviewer routing/escalation workflows (RBAC-heavy governance).
- Prompt experimentation framework and richer analytics dashboards.

### Architecture Approach

The recommended architecture is a thin HITL slice over existing runtime boundaries: keep current endpoints and graph stages, introduce typed interrupt payload objects, validate ordered decisions in resume, and persist lifecycle state in jobs/checkpointer. Backend schemas remain source-of-truth; frontend guards and SDK models mirror them. This minimizes churn while preventing contract drift.

**Major components:**
1. API/contract layer (`/run-async`, `/run-status`, `/run-events`, `/run-resume`) — stable endpoint topology with additive HITL fields.
2. Runtime orchestration + HITL checkpoint logic — emit pause payloads at subquestions/query expansion and resume deterministically.
3. Job lifecycle + persistence layer — enforce paused-only resume transitions and store interrupt metadata with canonical IDs.
4. Frontend review workflow — consume typed SSE events via `addEventListener(...)`, render decisions, resume runs.
5. SDK mirror + generated client — preserve contract parity and provide typed resume ergonomics.

### Critical Pitfalls

1. **Identity drift across surfaces** — enforce one canonical `thread_id`/`job_id`/`checkpoint_id` contract and integration-test it end-to-end.
2. **Decision ordering bugs for multi-action interrupts** — preserve action order/IDs from pause payload and reject non-deterministic resume payloads.
3. **Non-idempotent side effects before interrupt** — defer side effects until approval or protect with `(run_id, checkpoint_id, action_id)` idempotency keys.
4. **Contract drift on `sub_answers`/toggles** — treat schema changes as public API changes; run N-1 compatibility checks before release.
5. **SSE listener mismatch (`onmessage` only)** — consume named events with `addEventListener(...)` and validate in real browser tests.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Contract and Configuration Foundation
**Rationale:** Every downstream change depends on stable cross-surface schemas and deterministic config behavior.  
**Delivers:** Canonical HITL payload/decision schemas, additive `sub_answers`, toggle/prompt precedence resolver, compatibility policy.  
**Addresses:** Table-stakes contract parity, default-off compatibility, query/rerank controls.  
**Avoids:** Identity drift, contract drift, and toggle-precedence ambiguity.

### Phase 2: Runtime HITL Execution and Stream Integration
**Rationale:** Once contracts are fixed, implement real pause/resume behavior and evented UX end-to-end.  
**Delivers:** Stage checkpoints (`subquestions`, `query_expansion`), deterministic resume validation, typed SSE interrupt events, frontend review flow.  
**Uses:** LangChain/LangGraph interrupt semantics + FastAPI SSE + persisted checkpointer state.  
**Implements:** Runtime/job lifecycle boundaries from architecture research.

### Phase 3: Prompt Customization Guardrails
**Rationale:** Prompt controls are valuable but security-sensitive; ship after core HITL correctness.  
**Delivers:** Prompt customization resolver, immutable policy segments, server-side validation/redaction, observability of effective prompt config.  
**Addresses:** Prompt customization requirements without safety regressions.  
**Avoids:** Unsafe prompt override and policy bypass pitfalls.

### Phase 4: SDK, Docs, and PyPI Release Orchestration
**Rationale:** External adoption requires synchronized packaging and clear migration guidance.  
**Delivers:** SDK parity update, generated client refresh, compatibility matrix, release gates, PyPI publication, migration docs.  
**Addresses:** Developer-facing usability and distribution requirements.  
**Avoids:** SDK/backend version desynchronization and dependency-pin traps.

### Phase Ordering Rationale

- Contracts and precedence rules come first because they constrain runtime, UI, and SDK implementation details.
- Runtime/stream integration comes second because it is the highest-risk behavioral layer and needs stable schemas.
- Prompt guardrails follow core HITL correctness to avoid compounding safety and replay risks.
- Packaging/docs last ensures published artifacts reflect proven contracts and validated behavior.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Multi-action decision mapping and replay/idempotency edge cases under concurrency need implementation-specific validation.
- **Phase 3:** Prompt guardrail boundaries and redaction policy may require security-focused design review.
- **Phase 4:** Versioning/deprecation strategy across backend + SDK + PyPI workflow needs release-process calibration.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Schema-first API design and additive compatibility policy are mature, well-documented patterns.
- **SSE transport basics in Phase 2:** FastAPI SSE + browser EventSource are well-established; focus research only on project-specific event contracts.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Strong official-source backing for HITL middleware, interrupts, persistence, SSE, and publishing patterns. |
| Features | HIGH | Requirements align tightly with documented HITL primitives and explicit milestone goals. |
| Architecture | HIGH | Clear fit with current repo boundaries; low need for structural redesign. |
| Pitfalls | HIGH | Risks are concrete, repeatedly observed in HITL/pause-resume systems, and mapped to prevention phases. |

**Overall confidence:** HIGH

### Gaps to Address

- **Decision schema granularity:** finalize exact `edit` payload constraints by checkpoint type (subquestions vs query expansion) during phase planning.
- **Timeout/escalation policy:** define pending-checkpoint TTL and failure behavior (reject, bypass, or fail-fast) before production rollout.
- **Release matrix scope:** specify minimum supported backend/SDK version combinations and N-1 test coverage.
- **Audit requirements:** confirm required reviewer attribution and retention depth for compliance-sensitive environments.

## Sources

### Primary (HIGH confidence)
- [LangChain Human-in-the-Loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) - decision semantics, middleware behavior, pause/resume requirements.
- [LangChain built-in middleware docs](https://docs.langchain.com/oss/python/langchain/middleware/built-in#human-in-the-loop) - integration patterns and checkpointer requirement.
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) - interrupt/resume mechanics and ordering considerations.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) - checkpoint durability and Postgres-backed persistence guidance.
- [FastAPI SSE](https://fastapi.tiangolo.com/tutorial/server-sent-events/) - native typed SSE support.
- [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) - browser event handling behavior for named SSE events.
- [FastAPI client generation](https://fastapi.tiangolo.com/advanced/generate-clients/) - OpenAPI-based client synchronization guidance.
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/) and [GitHub OIDC for PyPI](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-pypi) - secure SDK publish path.

### Secondary (MEDIUM confidence)
- [PyPA publishing with GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/) - release flow details and practical CI recommendations.
- [PyPI publish action marketplace docs](https://github.com/marketplace/actions/pypi-publish) - operational constraints and workflow caveats.

### Tertiary (LOW confidence)
- Existing repository architecture and contract files referenced in `ARCHITECTURE.md` - high local relevance, but still requires implementation-time verification against current branch state.

---
*Research completed: 2026-03-13*
*Ready for roadmap: yes*
