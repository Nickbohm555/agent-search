# Pitfalls Research

**Domain:** Retrofitting human approval/edit/deny checkpoints and prompt customization into an existing RAG pipeline with synchronized backend/frontend/SDK/PyPI releases
**Researched:** 2026-03-13
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Checkpoint identity drift (`thread_id`/job ID mismatch across API, UI, and SDK)

**What goes wrong:**
An approval request is raised for one run, but resume is posted against a different thread or run identifier. Human decisions are applied to the wrong execution, or resume starts a new execution path.

**Why it happens:**
HITL retrofit is added at backend graph level, while frontend and SDK still treat runs as stateless polling jobs. IDs are transformed or regenerated in one layer.

**How to avoid:**
Define one canonical resume identity contract (`thread_id`, `job_id`, `checkpoint_id`) and expose it unchanged in backend response payloads, SSE events, frontend state, and SDK types. Add contract tests that replay approve/edit/reject through all clients using the same IDs.

**Warning signs:**
- Resume requests succeed with 200 but checkpoint remains pending.
- Approval events appear for a run not currently open in UI.
- Duplicate "new run started" logs immediately after resume.

**Phase to address:**
Phase 1 - Cross-surface contract design (backend/frontend/SDK)

---

### Pitfall 2: Interrupt decision ordering bug for multi-action checkpoints

**What goes wrong:**
When multiple actions are paused together, decisions are sent out of order and approvals/edits/rejections are applied to the wrong action request.

**Why it happens:**
LangChain HITL requires decision order to match action order, but UI sorting/filtering or SDK serialization changes ordering semantics.

**How to avoid:**
Carry explicit `action_id` + index from interrupt payload through UI and SDK, and verify backend enforces deterministic mapping before resume. Include tests with two or more simultaneous action requests and mixed decisions (`approve`, `edit`, `reject`).

**Warning signs:**
- "Approve query expansion" ends up approving subquestion edits.
- Edited arguments appear on the wrong tool call.
- Intermittent failures only when multiple pending actions exist.

**Phase to address:**
Phase 2 - HITL workflow implementation and resume correctness

---

### Pitfall 3: Non-idempotent side effects before interrupt/resume

**What goes wrong:**
Query expansion writes cache rows, metrics, or audit records before interrupt; on resume, node replay re-executes those side effects and duplicates data or outbound calls.

**Why it happens:**
Interrupts resume from node start, and teams assume "resume continues from exact line." They keep side effects before checkpoint without idempotency guards.

**How to avoid:**
Move side effects after human decision when possible; otherwise enforce idempotency keys (`run_id + checkpoint_id + action_id`) and dedupe at write boundaries. Add forced crash/replay tests around each checkpointed node.

**Warning signs:**
- Duplicate expansion rows or duplicate tool invocations after a single approval.
- Audit trail has repeated entries with same logical action.
- Retry/replay test shows non-deterministic counts.

**Phase to address:**
Phase 2 - Durable execution and idempotency hardening

---

### Pitfall 4: Contract drift while adding `sub_answers` and new toggles

**What goes wrong:**
Backend returns new fields (`sub_answers`) or changes toggle semantics (`rerank`, `query_expansion`), but frontend and SDK parse older contracts. Clients silently drop data, fail validation, or mis-render checkpoint details.

**Why it happens:**
Schema evolution is treated as "minor internal change" instead of public API/SDK surface change with compatibility policy.

**How to avoid:**
Version response contracts, mark additive vs breaking changes explicitly, and run compatibility tests against previous SDK and UI builds. Ship default-safe behavior for unknown fields and documented toggle precedence.

**Warning signs:**
- Frontend shows empty sub-answers despite backend logs containing them.
- SDK deserialization errors only on new backend release.
- Users report toggles behave opposite to API docs.

**Phase to address:**
Phase 1 - API schema versioning and compatibility policy

---

### Pitfall 5: Toggle and prompt-customization precedence conflicts

**What goes wrong:**
System prompt, user prompt customization, project defaults, and runtime toggles conflict. Query expansion may run when disabled, or custom prompts bypass intended retrieval/rerank behavior.

**Why it happens:**
No deterministic precedence rules are defined, and each layer applies overrides independently.

**How to avoid:**
Publish a single precedence matrix (system > policy guardrails > user prompt customization > request toggles, or your chosen order) and enforce it in one backend resolver. Echo resolved config in responses for observability.

**Warning signs:**
- Same request payload yields different behavior by client.
- Debugging requires checking multiple files to know "effective prompt."
- Support tickets mention "toggle says off but behavior is on."

**Phase to address:**
Phase 1 - Configuration resolution design

---

### Pitfall 6: Unsafe prompt customization path (policy and data-leak regressions)

**What goes wrong:**
Editable prompts allow bypassing safety instructions, injecting hidden directives into tool arguments, or leaking internal retrieval context through user-visible outputs.

**Why it happens:**
Prompt customization is exposed as raw text replacement without policy-layer validation or redaction boundaries.

**How to avoid:**
Split customizable template variables from non-editable policy prompt sections, run server-side validation on allowed prompt fields, and redact sensitive retrieval/internal metadata before rendering approval payloads.

**Warning signs:**
- Prompt edits contain policy terms that should be immutable.
- Increased unsafe tool-call proposals after prompt customization launch.
- Internal retrieval snippets appear in approval UI unexpectedly.

**Phase to address:**
Phase 3 - Prompt customization guardrails and security review

---

### Pitfall 7: Frontend SSE listener mismatch for typed checkpoint events

**What goes wrong:**
UI listens only to default `message` events while backend emits typed events (e.g., `checkpoint.pending`, `checkpoint.resolved`). HITL appears frozen because state transitions are never consumed.

**Why it happens:**
Existing run-progress implementation uses generic `onmessage`; retrofit introduces named events without updating client listeners.

**How to avoid:**
Use `addEventListener(...)` for every emitted event type and maintain an event contract test suite shared by backend and frontend. Include fallback/error events and reconnection handling.

**Warning signs:**
- Network tab shows SSE frames but no UI state change.
- Only initial run status updates render; checkpoint transitions do not.
- Behavior differs between local mocks and real browser.

**Phase to address:**
Phase 2 - Frontend stream integration for HITL events

---

### Pitfall 8: SDK/PyPI release desynchronization and dependency pin traps

**What goes wrong:**
Backend ships new HITL payloads first, but SDK release lags or is pinned with strict `==` dependency constraints. Integrators cannot install compatible versions or unknowingly run incompatible pairs.

**Why it happens:**
Release process does not treat backend API contract + SDK package + docs + PyPI publish as one atomic compatibility unit.

**How to avoid:**
Adopt explicit compatibility matrix and SemVer policy for API/SDK; avoid strict `==` in published dependency specs unless required for app lockfiles. Gate PyPI publish on contract tests against target backend version and publish migration notes with deprecation windows.

**Warning signs:**
- "Works on main branch, fails from pip install."
- Support issues spike immediately after package publish.
- Users blocked by dependency resolver conflicts.

**Phase to address:**
Phase 4 - SDK packaging, versioning, and release orchestration

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Add HITL as `if needs_approval:` branches inside existing nodes | Minimal code churn | Replay/idempotency bugs and fragile control flow | Only in short-lived spike branches |
| Keep checkpoints "backend-only" without SDK typings | Faster backend merge | Broken external integrations and unclear contracts | Never for public SDK surfaces |
| Use strict `==` dependency pins in published SDK | Predictable local testing | Security-fix and compatibility deadlocks for consumers | Rarely; only internal app lockfiles, not library metadata |
| Let prompt customization be free-form raw override | Quick feature demo | Safety regressions and irreproducible behavior | Never in production without guardrails |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| LangChain HITL middleware | Assuming resume can use reordered decision arrays | Preserve action order/IDs from interrupt payload and validate before `Command(resume=...)` |
| LangGraph persistence/checkpointer | Using inconsistent thread identifiers across layers | Standardize `thread_id` lifecycle and persist it through UI + SDK |
| Frontend SSE client | Listening only with `onmessage` | Use named `addEventListener` handlers for typed events and contract tests |
| PyPI publishing pipeline | Publishing SDK without compatibility test against backend contract | Block publish until end-to-end compatibility matrix checks pass |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Human checkpoints with no timeout/escalation path | Long-running pending runs and queue buildup | Add checkpoint TTLs, escalation rules, and cancellation semantics | Moderate concurrency with limited reviewers |
| Re-running retrieval/expansion after each edit without cache keying | Token/cost spikes during review loops | Cache by `(query, toggle set, prompt revision)` and invalidate intentionally | Frequent edit-based HITL workflows |
| Streaming full state snapshots each event | High SSE payload volume and UI lag | Emit compact delta events with stable schema and version field | Multi-tab or high-frequency status updates |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Unauthenticated approve/edit/reject endpoints | Unauthorized action execution | Require reviewer authz scoped to tenant/run/checkpoint and audit every decision |
| Storing raw prompt edits and retrieval snippets in logs | Sensitive data leakage | Redact or hash sensitive prompt/context fields in logs and traces |
| Allowing prompt customization to alter policy/system blocks | Safety and compliance bypass | Keep policy prompt immutable and expose only bounded user-customizable fields |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No diff view for `edit` actions | Reviewers cannot tell what changed | Show structured before/after diffs for tool arguments and prompt revisions |
| No explainability for deny path | Users see random refusal loops | Surface rejection reason and how agent used feedback on retry |
| Hidden toggle effective state | Users mistrust results | Display resolved toggle state and prompt profile used for each run |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Checkpoint correctness:** Mixed approve/edit/reject test passes for multi-action interrupts in deterministic order.
- [ ] **Identity integrity:** Same `thread_id`/`job_id` is preserved from interrupt to resume across API, UI, and SDK.
- [ ] **Contract compatibility:** `sub_answers` and toggle fields validated against current and previous SDK versions.
- [ ] **Prompt safety:** Customization path cannot modify immutable policy blocks and passes security review tests.
- [ ] **SSE behavior:** Typed checkpoint events are received via `addEventListener` in real browser tests.
- [ ] **Release readiness:** PyPI package publish is gated by backend-frontend-SDK end-to-end compatibility checks.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong decision applied to wrong action | HIGH | Freeze approvals, reconcile from decision audit log, replay pending checkpoints with corrected mapping, patch ordering bug |
| Contract drift breaks SDK clients | MEDIUM-HIGH | Ship patch release with backward-compatible serializer, add temporary compatibility shim, publish migration advisory |
| Prompt customization causes unsafe outputs | HIGH | Disable customization feature flag, rotate to safe prompt profile, review logs for policy breach impact, relaunch behind stricter validation |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Checkpoint identity drift | Phase 1 - Cross-surface contract design | Integration test proves resume uses identical IDs end-to-end |
| Multi-action decision ordering bug | Phase 2 - HITL workflow implementation | Test suite covers mixed decisions with deterministic mapping |
| Non-idempotent side effects before interrupt | Phase 2 - Durable execution hardening | Replay/crash tests show no duplicate writes or calls |
| `sub_answers` and toggle contract drift | Phase 1 - API schema/version policy | Backward-compat tests pass for N-1 SDK/client |
| Toggle/prompt precedence conflicts | Phase 1 - Configuration resolution design | Snapshot tests assert resolved config determinism |
| Unsafe prompt customization | Phase 3 - Prompt guardrails/security | Policy immutability and redaction tests pass |
| SSE typed-event listener mismatch | Phase 2 - Frontend stream integration | Browser E2E confirms named events drive state changes |
| SDK/PyPI release desync | Phase 4 - Packaging and release orchestration | Release gate enforces compatibility matrix and migration notes |

## Sources

- LangChain Human-in-the-Loop (required, official): https://docs.langchain.com/oss/python/langchain/human-in-the-loop
- LangGraph Interrupts (official): https://docs.langchain.com/oss/python/langgraph/interrupts
- Python Packaging User Guide - Packaging Python Projects (official): https://packaging.python.org/en/latest/tutorials/packaging-projects/
- Python Packaging - Version Specifiers (official): https://packaging.python.org/en/latest/specifications/version-specifiers/
- Semantic Versioning 2.0.0 (official): https://www.semver.org/
- MDN EventSource (official web platform reference): https://developer.mozilla.org/en-US/docs/Web/API/EventSource

---
*Pitfalls research for: HITL retrofit + contract evolution + SDK/PyPI release synchronization*
*Researched: 2026-03-13*
