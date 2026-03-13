# Stack Research

**Domain:** HITL-enabled advanced RAG checkpoints in a FastAPI + React app with Python SDK distribution
**Researched:** 2026-03-13
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | Runtime `3.12.x` (package support `>=3.11,<3.14`) | Backend runtime + SDK build target | Matches your existing backend range while staying on a mature Python line for LangChain/LangGraph and packaging tooling. |
| LangChain | `>=1.2,<2` | Agent runtime entrypoint + HITL middleware integration | Official HITL middleware (`HumanInTheLoopMiddleware`) is documented here and integrates directly with LangGraph interrupts/checkpointing. |
| LangGraph | `>=1.0.10,<2` | Durable execution, interrupts, and pause/resume semantics | HITL depends on interrupt-driven pause/resume plus thread-based persistence; this is the standard production path in LangGraph-style runtimes. |
| langgraph-checkpoint-postgres | `>=3.0.4,<4` | Persistent checkpoint store for approvals/rejections/resume | Official LangGraph persistence docs call Postgres saver the production-oriented checkpointer; needed so HITL survives restarts and async review cycles. |
| FastAPI | **Upgrade to** `>=0.135,<0.136` | Backend API + typed SSE stream transport | FastAPI now ships native SSE (`fastapi.sse.EventSourceResponse`), making evented HITL updates first-class without third-party SSE plumbing. |
| Pydantic | `>=2.10,<3` | Contract schema layer for backend, frontend DTO generation, and SDK models | Keeps API payloads strongly typed and stable while evolving contracts for optional HITL fields. |
| React + TypeScript | React `18.x`, TypeScript `5.8+` | Human review UI and event-driven checkpoint controls | EventSource in browsers is stable; React + TS keeps reviewer controls explicit and safer to evolve than ad hoc JSON handling. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langchain-openai` | `>=0.3,<1` (or current repo baseline `>=0.3.0`) | Model provider adapter for existing RAG behavior | Keep provider wiring stable while adding HITL controls; reduce simultaneous migration risk. |
| `httpx` | `>=0.28,<1` | Python SDK HTTP transport | Use in SDK for timeout/retry-ready calls and parity with async/sync client patterns. |
| `@hey-api/openapi-ts` | `latest` (pin exact in lockfile) | Generate frontend TS client from FastAPI OpenAPI 3.1 schema | FastAPI docs explicitly recommend OpenAPI-based SDK generation; this prevents backend/frontend contract drift during HITL evolution. |
| `build` | `>=1.2,<2` | Build wheel/sdist in CI | PyPA’s publishing workflow uses a dedicated build step before publish, enabling artifact promotion and safer releases. |
| `pypa/gh-action-pypi-publish` | `@release/v1` (prefer pinned commit SHA) | Trusted Publishing for SDK releases | Official recommended flow for OIDC tokenless publishing; includes attestations by default in modern versions. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Backend dependency + lock management | Keep one resolver path for backend and SDK package dependencies; avoid mixed ad hoc installs. |
| `pytest` (+ async tests) | Resume/idempotency/contract regression tests | Add targeted tests for interrupt ordering, resume payload validation, and HITL-disabled backward compatibility. |
| GitHub Environments (`pypi`, `testpypi`) | Release gating + manual approvals | PyPA guide recommends environment-based OIDC publishing; use manual approval on `pypi` for release safety. |

## Installation

```bash
# Backend runtime (uv / src/backend)
uv add "langchain>=1.2,<2" "langgraph>=1.0.10,<2" \
  "langgraph-checkpoint-postgres>=3.0.4,<4" \
  "fastapi>=0.135,<0.136" "pydantic>=2.10,<3" \
  "httpx>=0.28,<1"

# Frontend contract tooling (src/frontend)
npm install -D @hey-api/openapi-ts

# SDK/release build tooling (Python packaging workflow)
python -m pip install --upgrade build
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `langgraph-checkpoint-postgres` | `langgraph-checkpoint-sqlite` | Local-only experiments, demos, or single-process dev workflows. |
| FastAPI native SSE | WebSockets | Use WebSockets only if reviewers must send frequent bi-directional low-latency messages over one persistent channel. |
| OpenAPI-generated TS client | Handwritten fetch client | Tiny prototypes; not recommended once backend+frontend+SDK contracts evolve in parallel. |
| OIDC Trusted Publishing | API-token publishing | Only for registries that do not support trusted publishing. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `InMemorySaver` for production HITL | HITL pauses must survive process restarts and delayed human review | `langgraph-checkpoint-postgres` with thread IDs |
| Polling-only checkpoint status for main UX loop | Adds latency, complexity, and race conditions for human review state | SSE stream with named events and resumable thread state |
| `onmessage` as the only frontend SSE handler for named events | Named SSE events are dispatched by event name, not just generic message | `EventSource.addEventListener("event_name", ...)` handlers |
| Long-lived `PYPI_API_TOKEN` secrets as primary release auth | Higher blast radius and rotation burden vs short-lived OIDC exchange | Trusted Publishing with `id-token: write` |
| Trusted publishing inside reusable workflows | Officially unsupported flow today | Top-level release workflow job dedicated to publish step |
| Breaking SDK payload shape in minor releases | Violates compatibility when HITL is disabled and clients expect old models | Add optional fields and versioned schema evolution with semantic versioning discipline |

## Stack Patterns by Variant

**If HITL is disabled (backward-compatibility mode):**
- Keep current RAG path default.
- Do not require checkpoint decision fields in request/response payloads.
- Emit no-op/default review metadata so old clients continue to function.

**If HITL is enabled for subquestions/query-expansion controls:**
- Gate tool actions with `HumanInTheLoopMiddleware(interrupt_on=...)`.
- Persist checkpoints with Postgres saver and stable `thread_id`.
- Stream typed checkpoint events to React via SSE; resume via explicit decision APIs.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `langchain>=1.2,<2` | `langgraph>=1.0.10,<2` | LangChain HITL middleware is built on LangGraph interrupt/persistence primitives. |
| `langgraph>=1.0.10,<2` | `langgraph-checkpoint-postgres>=3.0.4,<4` | Package family alignment for production checkpointer usage. |
| `fastapi>=0.135,<0.136` | `pydantic>=2,<3` | FastAPI SSE feature set and schema typing on current Pydantic generation. |
| React `18.x` | Browser `EventSource` API | Stable native client for SSE with named event listeners. |
| `pypa/gh-action-pypi-publish@release/v1` | PyPI Trusted Publisher config + `id-token: write` | Standard tokenless release flow with attestations support. |

## Prescriptive Implementation Notes (for this repo)

1. **Keep architecture fixed:** FastAPI backend + React frontend + Python SDK remain first-class; add HITL as an additive capability, not a rewrite.
2. **Upgrade FastAPI first:** current repo uses `0.115.12`; native SSE guidance relies on `0.135+`.
3. **Model HITL as optional contracts:** add nullable/optional review metadata fields so old clients and SDK calls remain valid.
4. **Use one canonical event stream path:** stream checkpoint lifecycle events (pending/approved/edited/rejected/resumed) over SSE.
5. **Harden SDK release pipeline:** build once, publish artifacts via OIDC trusted publisher jobs (TestPyPI then PyPI).

## Sources

- [LangChain HITL docs (required source)](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) — middleware behavior, decision types, thread/checkpointer requirements, streaming patterns (**HIGH**)
- [LangChain built-in middleware docs](https://docs.langchain.com/oss/python/langchain/middleware/built-in#human-in-the-loop) — `HumanInTheLoopMiddleware` integration point and checkpointer requirement (**HIGH**)
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) — `interrupt()`/`Command(resume=...)`, JSON payload rules, idempotency caveats (**HIGH**)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) — production checkpointer options and Postgres saver recommendation (**HIGH**)
- [FastAPI SSE](https://fastapi.tiangolo.com/tutorial/server-sent-events/) — native SSE support (`EventSourceResponse`) and operational behavior (**HIGH**)
- [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) — named event handling (`addEventListener`) and SSE transport characteristics (**HIGH**)
- [FastAPI generating SDKs](https://fastapi.tiangolo.com/advanced/generate-clients/) — OpenAPI 3.1 client generation path for TS consumers (**HIGH**)
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/) — OIDC tokenless publishing model and short-lived token behavior (**HIGH**)
- [GitHub OIDC for PyPI](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-pypi) — required workflow permissions and trust configuration (**HIGH**)
- [PyPA GitHub Actions publishing guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/) — recommended build/publish job split, TestPyPI/PyPI flow, attestations note (**HIGH**)
- [PyPI Publish GitHub Action marketplace docs](https://github.com/marketplace/actions/pypi-publish) — trusted publishing constraints (including reusable workflow limitation) and security recommendations (**HIGH**)
- [Python Packaging versioning guidance](https://packaging.python.org/en/latest/discussions/versioning/) — semver/calver tradeoffs and compatibility communication for SDK evolution (**HIGH**)

---
*Stack research for: HITL-enabled advanced RAG controls (subquestions/query expansion)*
*Researched: 2026-03-13*
