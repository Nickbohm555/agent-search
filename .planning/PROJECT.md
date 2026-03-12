# LangGraph State Graph Migration for Agent Search

## What This Is

This project migrates the existing RAG orchestration from custom runtime flow logic to a LangGraph state-graph architecture. It preserves the current value of decomposition, validation, semantic retrieval, sub-answer generation, and final synthesis while making state transitions and node I/O explicit and controllable. The primary audience is SDK consumers and application operators who need a more maintainable, observable, and releasable orchestration core.

## Core Value

Every query run executes end-to-end through a LangGraph-native state graph that is reliable in remote environments and produces production-ready answers.

## Requirements

### Validated

- ✓ Users can submit agent queries asynchronously and poll structured run status/results through backend APIs and frontend flows — existing
- ✓ The system supports staged RAG processing (decompose, search, rerank, sub-answering, synthesis) using current runtime orchestration — existing
- ✓ Internal data can be ingested asynchronously and used for semantic vector retrieval in Postgres/pgvector-backed search flows — existing
- ✓ The project ships both application surfaces and an SDK distribution path with OpenAPI/client artifacts and PyPI release workflow — existing

### Active

- [ ] Replace the current custom orchestration path with a LangGraph-native state graph for the full RAG flow (decomposition, validation, semantic search, sub-answers, synthesis, guardrails/retries)
- [ ] Ensure the migrated state graph architecture runs successfully in both remote Docker Compose deployments and fresh remote pip-installed SDK environments
- [ ] Deliver a major SDK release that documents architecture migration, examples, and deprecation guidance for the old flow
- [ ] Update application HTML docs under `docs/` and API/reference documentation to reflect the new state graph architecture and usage
- [ ] Keep OpenAI as the provider stack baseline (from env-configured key) while migrating orchestration internals

### Out of Scope

- Adding authentication/authorization to API routes in this milestone — important but orthogonal to state-graph migration goal
- Re-platforming database, vector store, or frontend framework choices — migration scope is orchestration architecture, not full-stack rewrite
- Backward compatibility guarantees for old orchestration APIs/behavior — major release and breaking changes are explicitly accepted

## Context

The existing codebase is a brownfield FastAPI + React + Postgres/pgvector system with a graph-like runtime implemented through custom orchestration modules. Current architecture and stack mapping already show clear pipeline stages but also coupling and duplication hotspots, especially around orchestration ownership and runtime mirrors. The project already uses LangChain/OpenAI integrations for decomposition and answer generation; this migration introduces LangGraph as the explicit state orchestration substrate so node contracts, transitions, and monitoring are first-class. Documentation and SDK packaging are already present, so this effort extends those channels with migration-focused updates and release artifacts.

## Constraints

- **Tech stack**: Adopt LangGraph-native state/node patterns while preserving existing FastAPI, React, Postgres/pgvector, and LangChain/OpenAI baseline — minimizes unrelated churn
- **Provider dependency**: Keep OpenAI provider path env-driven and operational during migration — required by current usage and deployment assumptions
- **Timeline**: Balanced delivery window (approximately 1-2 weeks) — target solid quality without long-horizon overengineering
- **Release**: Ship as a major SDK version with explicit migration/deprecation documentation — breaking changes are expected and must be clear
- **Validation**: Must prove runtime in both remote Compose and fresh remote pip-install environments — acceptance is deployment-realistic, not local-only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full orchestration migration (not partial/flagged) | Reduce dual-path complexity and commit to the target architecture | — Pending |
| LangGraph-native modeling for state and node I/O | Make transitions explicit, testable, and observable | — Pending |
| Major release with breaking changes allowed | Enables cleaner architecture without preserving accidental legacy behaviors | — Pending |
| Documentation update in three surfaces (PyPI/package docs, API docs, app HTML docs) | Migration must be understandable and adoptable by both SDK users and app operators | — Pending |
| Remote-environment acceptance as quality bar | Confirms architecture is production-usable beyond local development | — Pending |

---
*Last updated: 2026-03-12 after initialization*
