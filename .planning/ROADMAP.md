# Roadmap: Agent Search HITL + Prompt Customization Milestone

## Overview

This roadmap delivers opt-in HITL controls and prompt customization without changing default advanced RAG behavior for existing users. Phases are derived from requirement boundaries: foundational contract safety, stage-specific HITL loops, operator controls, prompt controls, and external release readiness. Every v1 requirement maps to exactly one phase.

## Phases

### Phase 1 - Contract Foundation and Compatibility Baseline
**Goal:** Users can run the existing flow unchanged while the API contract safely introduces additive HITL-ready fields and default-off behavior.

**Dependencies:** None

**Requirements:**
- CTRL-02
- CTRL-04
- CTRL-05
- REL-01

**Success Criteria:**
1. API run requests accept new control fields while old clients can omit them and still complete runs successfully.
2. HITL behavior stays off by default unless explicitly enabled in the request.
3. Rerank/query-expansion backend flags are accepted and reflected in run configuration handling.
4. Runtime responses include additive `sub_answers` data without removing or breaking existing required response fields.

### Phase 2 - Subquestion HITL End-to-End
**Goal:** Users can review and control subquestions at a checkpoint before downstream execution continues.

**Dependencies:** Phase 1

**Requirements:**
- SQH-01
- SQH-02
- SQH-03
- SQH-04
- SQH-05

**Success Criteria:**
1. Users can enable subquestion HITL for a run through API/SDK request parameters.
2. Users can approve proposed subquestions and the run resumes with approved items.
3. Users can edit subquestions and the run resumes using edited values.
4. Users can deny selected subquestions and denied items are omitted without mandatory feedback text.
5. Users can skip subquestion HITL and continue using the default non-HITL behavior.

### Phase 3 - Query Expansion HITL End-to-End
**Goal:** Users can review and control query expansions before retrieval executes.

**Dependencies:** Phase 1

**Requirements:**
- QEH-01
- QEH-02
- QEH-03
- QEH-04
- QEH-05

**Success Criteria:**
1. Users can enable query-expansion HITL for a run through API/SDK request parameters.
2. Users can approve proposed query expansions and resume execution with approved expansions.
3. Users can edit query expansions and retrieval executes with the edited set.
4. Users can deny selected expansions and denied items are omitted without mandatory feedback text.
5. Users can skip query-expansion HITL and continue using the default non-HITL behavior.

### Phase 4 - Operator Controls and Result Visibility
**Goal:** Users can control retrieval behavior from frontend and SDK surfaces and see sub-answer outputs in the app.

**Dependencies:** Phase 1

**Requirements:**
- CTRL-01
- CTRL-03
- REL-02

**Success Criteria:**
1. Frontend users can toggle rerank and query-expansion behavior when starting a run.
2. SDK users can set rerank/query-expansion run parameters without UI-specific coupling.
3. Frontend run results visibly render `sub_answers` from runtime output.

### Phase 5 - Prompt Customization and Guidance
**Goal:** Users can customize subanswer and synthesis prompting with clear, safe defaults documented for consumers.

**Dependencies:** Phase 1

**Requirements:**
- PRM-01
- PRM-02
- PRM-03
- PRM-04

**Success Criteria:**
1. Users can provide a custom prompt for subanswer generation and observe that prompt influencing subanswer outputs.
2. Users can provide a custom prompt for final synthesis generation and observe that prompt influencing final output.
3. SDK consumers can set client-level mutable prompt defaults through the custom-prompts map.
4. Documentation clearly explains prompt defaults, each prompt's responsibility, and override usage.

### Phase 6 - SDK Contract Parity and PyPI Release
**Goal:** External SDK consumers can adopt HITL, controls, prompt options, and `sub_answers` through a published compatible release.

**Dependencies:** Phases 1, 2, 3, 4, 5

**Requirements:**
- REL-03
- REL-04
- REL-05

**Success Criteria:**
1. SDK/OpenAPI models include HITL fields, run controls, prompt options, and `sub_answers` matching backend contracts.
2. A new `agent-search-core` version is published to PyPI and installable by consumers.
3. Release and migration documentation tells users how to adopt HITL, control flags, prompt customization, and compatibility-safe defaults.

## Requirement Coverage Map

| Requirement | Phase |
|-------------|-------|
| SQH-01 | 2 |
| SQH-02 | 2 |
| SQH-03 | 2 |
| SQH-04 | 2 |
| SQH-05 | 2 |
| QEH-01 | 3 |
| QEH-02 | 3 |
| QEH-03 | 3 |
| QEH-04 | 3 |
| QEH-05 | 3 |
| CTRL-01 | 4 |
| CTRL-02 | 1 |
| CTRL-03 | 4 |
| CTRL-04 | 1 |
| CTRL-05 | 1 |
| PRM-01 | 5 |
| PRM-02 | 5 |
| PRM-03 | 5 |
| PRM-04 | 5 |
| REL-01 | 1 |
| REL-02 | 4 |
| REL-03 | 6 |
| REL-04 | 6 |
| REL-05 | 6 |

## Progress

| Phase | Status | Notes |
|-------|--------|-------|
| 1 | Completed | Additive contract baseline shipped; broader backend service suite still has unrelated red tests |
| 2 | Completed | API, frontend, SDK, and runtime subquestion HITL flow shipped with pause/resume checkpoint coverage |
| 3 | Completed | Query-expansion HITL shipped across contracts, runtime checkpointing, and frontend review/resume UX |
| 4 | Completed | Frontend/SDK runtime controls and sub-answer visibility shipped with regression coverage |
| 5 | Completed | Prompt customization contract, docs, runtime wiring, and SDK precedence coverage shipped |
| 6 | Completed | SDK parity release, PyPI publication, and migration/release guidance shipped |

**Coverage:** 24/24 v1 requirements mapped (100%)

**Milestone status:** Completed
