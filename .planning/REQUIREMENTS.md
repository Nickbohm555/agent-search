# Requirements: Agent Search HITL + Prompt Customization Milestone

**Defined:** 2026-03-13
**Core Value:** Users can safely control and customize how the agent thinks (subquestions/query expansion/prompting) without breaking the existing advanced RAG experience.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Subquestion HITL

- [ ] **SQH-01**: User can enable subquestion HITL per run via API and SDK request parameters.
- [ ] **SQH-02**: User can approve proposed subquestions and continue execution.
- [ ] **SQH-03**: User can edit proposed subquestions before downstream stages execute.
- [ ] **SQH-04**: User can deny proposed subquestions and excluded items are omitted from execution without requiring feedback text.
- [ ] **SQH-05**: User can skip subquestion HITL and continue with default non-HITL flow.

### Query Expansion HITL

- [ ] **QEH-01**: User can enable query-expansion HITL per run via API and SDK request parameters.
- [ ] **QEH-02**: User can approve proposed query expansions and continue execution.
- [ ] **QEH-03**: User can edit proposed query expansions before retrieval executes.
- [ ] **QEH-04**: User can deny proposed query expansions and excluded items are omitted from execution without requiring feedback text.
- [ ] **QEH-05**: User can skip query-expansion HITL and continue with default non-HITL flow.

### Runtime Controls

- [ ] **CTRL-01**: Frontend provides rerank and query-expansion controls for interactive app runs.
- [ ] **CTRL-02**: Backend API exposes rerank and query-expansion flags per run request.
- [ ] **CTRL-03**: SDK exposes rerank/query-expansion controls as run parameters (for example `hitl_rerank=true`-style flags), not UI toggles.
- [ ] **CTRL-04**: HITL remains disabled by default unless explicitly enabled by request parameters.
- [ ] **CTRL-05**: Existing behavior defaults remain unchanged when new HITL/toggle fields are omitted.

### Prompt Customization

- [ ] **PRM-01**: User can provide a custom prompt for subanswer generation.
- [ ] **PRM-02**: User can provide a custom prompt for final synthesis generation.
- [ ] **PRM-03**: SDK supports client-level prompt defaults through a mutable custom-prompts map.
- [ ] **PRM-04**: Documentation explains default prompts and clearly describes what each prompt controls.

### Contracts, UX, and Release

- [ ] **REL-01**: Runtime response contracts include additive `sub_answers` output without breaking existing required fields.
- [ ] **REL-02**: Frontend surfaces and uses `sub_answers` in run results.
- [ ] **REL-03**: SDK/OpenAPI models are updated to include HITL fields, controls, prompt options, and `sub_answers`.
- [ ] **REL-04**: Updated `agent-search-core` package is published to PyPI with a new version.
- [ ] **REL-05**: Release/migration docs cover HITL, toggle controls, prompt customization, and compatibility behavior.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### HITL Experience Enhancements

- **HITL-UX-01**: Reviewer sees diff-first edit previews for proposed subquestions/query expansions.
- **HITL-UX-02**: Reviewer can submit batch decisions for multiple pending actions in one operation.
- **HITL-UX-03**: Reviewer analytics dashboard reports approval/edit/reject rates by stage.

### Governance and Workflow

- **GOV-01**: Platform supports role-based reviewer routing and escalation for pending HITL checkpoints.
- **GOV-02**: Platform supports configurable timeout escalation policies for pending HITL decisions.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| HITL enabled by default for all existing runs | Must preserve current non-HITL behavior unless explicitly enabled |
| Unconstrained free-form edits without validation | High risk of unstable runtime behavior and tool/action drift |
| Broad HITL coverage across every runtime stage | Milestone is intentionally limited to subquestions and query expansion |
| Full auth/RBAC reviewer governance in this release | Not required for core functional HITL milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SQH-01 | TBD | Pending |
| SQH-02 | TBD | Pending |
| SQH-03 | TBD | Pending |
| SQH-04 | TBD | Pending |
| SQH-05 | TBD | Pending |
| QEH-01 | TBD | Pending |
| QEH-02 | TBD | Pending |
| QEH-03 | TBD | Pending |
| QEH-04 | TBD | Pending |
| QEH-05 | TBD | Pending |
| CTRL-01 | TBD | Pending |
| CTRL-02 | TBD | Pending |
| CTRL-03 | TBD | Pending |
| CTRL-04 | TBD | Pending |
| CTRL-05 | TBD | Pending |
| PRM-01 | TBD | Pending |
| PRM-02 | TBD | Pending |
| PRM-03 | TBD | Pending |
| PRM-04 | TBD | Pending |
| REL-01 | TBD | Pending |
| REL-02 | TBD | Pending |
| REL-03 | TBD | Pending |
| REL-04 | TBD | Pending |
| REL-05 | TBD | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 0
- Unmapped: 24

---
*Requirements defined: 2026-03-13*
*Last updated: 2026-03-13 after initial definition*
