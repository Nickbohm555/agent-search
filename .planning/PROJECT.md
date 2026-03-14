# Agent Search HITL + Prompt Customization Milestone

## What This Is

This project extends an existing Agent Search product by adding Human-in-the-Loop (HITL) control points for subquestions and query expansion in the advanced RAG flow. It includes coordinated backend API, frontend UI, and SDK/PyPI surface updates so users can approve, edit, deny, or skip HITL checkpoints before the run proceeds. It also adds prompt customization controls for subanswer and final synthesis behavior.

## Core Value

Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.

## Requirements

### Validated

- ✓ Users can run asynchronous agent workflows and observe staged outputs from frontend + backend runtime contracts — existing
- ✓ The runtime already supports decompose, query expansion, search, rerank, answer, and synthesize stages — existing
- ✓ Frontend and SDK already integrate with backend `/api/agents/*` contracts for advanced RAG operations — existing
- ✓ The project already ships Python SDK artifacts to PyPI with documented release tooling — existing

### Active

- [ ] Add optional HITL for subquestions with approve/edit/deny/skip behavior before downstream execution
- [ ] Add optional HITL for query expansion with approve/edit/deny/skip behavior before downstream execution
- [ ] Expose rerank and query-expansion enable/disable controls in backend API, frontend UI, and SDK request surfaces
- [ ] Keep HITL opt-in by default for advanced RAG (off unless explicitly enabled)
- [ ] Return `sub_answers` in output contracts (backend schemas, SDK models, frontend rendering/typing)
- [ ] Add custom prompt configuration for subanswer and synthesis prompts through the SDK/client surface
- [ ] Document prompt defaults, prompt responsibilities, and prompt override usage for backend/API/SDK consumers
- [ ] Publish an updated SDK release to PyPI with these contract changes

### Out of Scope

- HITL for every pipeline stage beyond subquestions and query expansion in this milestone — keeps scope focused on the highest-value intervention points
- Re-platforming the current async job infrastructure away from in-memory tracking — not required to deliver HITL and prompt customization
- Full auth/role-based reviewer workflows for HITL approvals — current product is unauthenticated and this milestone focuses on functional controls

## Context

The codebase is a brownfield monolith with a FastAPI backend, React frontend, and duplicated runtime/contract surfaces mirrored into SDK core and generated Python OpenAPI client artifacts. The existing flow already has multi-stage async execution and UI stage visualization, making it a good fit for introducing explicit pause/approve/edit checkpoints. Contract drift risk is high because schema updates must stay synchronized across backend Pydantic models, frontend TypeScript guards/types, and SDK models. This milestone intentionally includes PyPI publishing and documentation to ensure external SDK users can adopt HITL and prompt customization safely.

## Constraints

- **Tech stack**: Must remain aligned with existing FastAPI + React/TypeScript + SDK-core/OpenAPI split — minimizes architecture churn and keeps compatibility
- **Compatibility**: Existing advanced RAG behavior must continue working when HITL is not enabled — avoids regressions for current consumers
- **Release**: SDK changes must be versioned and shipped to PyPI in this milestone — external users need the new controls
- **UX**: HITL must allow approve/edit/deny and explicit skip/no-HITL options — user requested operator control without forcing manual checkpoints
- **Scope control**: Do not run a full build pipeline for this effort (`do not build`) — keep validation focused on targeted checks/docs/contracts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| HITL scope includes subquestions and query expansion only | These are the requested intervention points and highest leverage before retrieval/answer composition | — Pending |
| HITL defaults to off (opt-in) | Preserves existing advanced RAG defaults and avoids surprise workflow changes | — Pending |
| Expose rerank/query-expansion toggles while preserving existing defaults | Adds control for advanced users without forcing behavior changes | — Pending |
| SDK prompt customization via mutable client-level dictionary (`agent_search.custom_prompts`) | Matches requested ergonomics and keeps prompt defaults overridable | — Pending |
| Include backend + frontend + SDK + docs + PyPI release in one milestone | Prevents partial rollout and contract mismatch across surfaces | — Pending |

---
*Last updated: 2026-03-13 after initialization*
