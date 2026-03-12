# Roadmap: LangGraph State Graph Migration

## Overview

This roadmap is derived directly from the v1 requirements for LangGraph migration, reliability, observability, and release readiness. The phases are ordered by dependency so each phase delivers a coherent, verifiable capability that unblocks the next one. Coverage is complete: every v1 requirement maps to exactly one phase.

## Phases

### Phase 1 - State Contract Foundation

**Goal:** Users and integrators can rely on a stable, typed state and node contract baseline for LangGraph execution.

**Dependencies:** None

**Requirements:**
- SGF-01
- SGF-02
- SGF-03

**Success Criteria:**
1. SDK consumers can import and use a canonical typed `RAGState` contract without custom state shims.
2. Engineers can identify explicit input/output schemas for every defined graph node from the code and reference docs.
3. Repeated runs of equivalent graph transitions produce consistent state merge outcomes under documented reducer semantics.

### Phase 2 - Durable Execution and Identity Semantics

**Goal:** Graph execution is resilient to failures and can safely pause, resume, and replay without corrupting run state.

**Dependencies:** Phase 1

**Requirements:**
- REL-01
- REL-02
- REL-03
- REL-04

**Success Criteria:**
1. An interrupted run can resume from persisted Postgres checkpoints instead of restarting from the beginning.
2. The same `thread_id` is visible and consistent across API responses, SDK interactions, and execution records for a run.
3. Retried or replayed runs do not duplicate externally visible side effects and preserve correct run outcomes.
4. Human-in-the-loop pause/resume flows complete successfully without invalid state transitions or data loss.

### Phase 3 - End-to-End LangGraph RAG Cutover

**Goal:** Production query orchestration runs fully through LangGraph nodes for the full RAG lifecycle.

**Dependencies:** Phase 1, Phase 2

**Requirements:**
- SGF-04

**Success Criteria:**
1. A production query executes decomposition, validation, semantic retrieval, sub-answer generation, synthesis, and guardrails/retries through LangGraph path only.
2. Query responses remain production-ready in structure and quality while using the migrated LangGraph orchestration path.
3. Legacy custom orchestration is no longer required for v1 query completion in the main runtime path.

### Phase 4 - Observability and Remote Runtime Validation

**Goal:** Operators can observe graph behavior in detail and verify runtime reliability in required remote environments.

**Dependencies:** Phase 3

**Requirements:**
- OBS-01
- OBS-02
- REL-05

**Success Criteria:**
1. Users and operators can observe streaming lifecycle events that show graph progress from run start through completion/failure.
2. Traces correlate node-level execution, thread context, and final outcome for troubleshooting and auditability.
3. The migrated system is proven to run successfully in both remote Docker Compose and fresh remote pip-installed SDK environments.

**Plans:** 3 plans

Plans:
- [x] 04-01-PLAN.md - Runtime lifecycle streaming contract and SSE delivery
- [x] 04-02-PLAN.md - Trace correlation tuple propagation and contract validation
- [x] 04-03-PLAN.md - Remote Compose + pip SDK validation matrix and evidence

### Phase 5 - Major Release and Migration Documentation

**Goal:** Integrators can adopt the LangGraph architecture via a clear major release, migration path, and updated docs.

**Dependencies:** Phase 4

**Requirements:**
- DOC-01
- DOC-02
- DOC-03
- DOC-04
- DOC-05
- DOC-06

**Success Criteria:**
1. A major SDK version is published and installable with release notes clearly describing the LangGraph migration.
2. Existing integrators can migrate from legacy orchestration by following a stepwise migration guide and deprecation map.
3. API/reference docs and application HTML docs under `docs/` accurately describe the new state-graph architecture and interfaces.
4. Updated examples run successfully and demonstrate LangGraph-based usage patterns expected in v1.

## Progress

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 1 - State Contract Foundation | Stable typed state and node contracts | SGF-01, SGF-02, SGF-03 | Completed |
| 2 - Durable Execution and Identity Semantics | Replay-safe durability and thread identity | REL-01, REL-02, REL-03, REL-04 | Completed |
| 3 - End-to-End LangGraph RAG Cutover | Full RAG flow runs via LangGraph | SGF-04 | Completed |
| 4 - Observability and Remote Runtime Validation | Streaming/tracing and remote deployment proof | OBS-01, OBS-02, REL-05 | Completed |
| 5 - Major Release and Migration Documentation | Release adoption and migration clarity | DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06 | Pending |

## Coverage Validation

- Total v1 requirements: 17
- Mapped requirements: 17
- Unmapped requirements: 0
- Duplicate mappings: 0
