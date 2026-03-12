# Pitfalls Research

**Domain:** LangGraph migration for a brownfield, production RAG pipeline (SDK-backed, OpenAI baseline retained)
**Researched:** 2026-03-12
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: "Node lift-and-shift" that keeps old monolith steps

**What goes wrong:**
Teams map the old orchestrator into a few oversized LangGraph nodes (for example, one node does decompose + validate + search + synthesis). Checkpoint boundaries become too coarse, so retries and resume replay too much work and duplicate side effects.

**Why it happens:**
Migration pressure favors "minimal rewrites," and teams underestimate how much durable execution semantics depend on node boundaries.

**How to avoid:**
Split nodes by failure domain and side-effect boundary (decompose, validate, semantic search, subanswers, synthesis, guardrails/retry control). Keep each node single-purpose, with explicit retry policy and clear input/output state keys.

**Warning signs:**
- Single node has multiple provider calls and external writes.
- Resume from interruption re-runs expensive upstream work.
- One node has mixed retry needs (rate-limit retries + business validation + irreversible side effects).

**Phase to address:**
Phase 1 - Graph decomposition and state contract design

---

### Pitfall 2: Non-deterministic or side-effectful code outside tasks

**What goes wrong:**
On resume, nodes restart from the beginning and replay logic. If API calls, random/time-based branching, or writes are not encapsulated properly, retries/resumes trigger duplicate actions and divergent control flow.

**Why it happens:**
Teams treat LangGraph resume like "resume from line," not "replay from node/task boundary."

**How to avoid:**
Wrap non-determinism and side effects in tasks/nodes with idempotency keys and dedupe checks; enforce a "no external side effects outside task wrappers" rule in code review.

**Warning signs:**
- Duplicate downstream writes during recovery tests.
- Same run ID produces different branch paths after resume.
- Time/random-dependent routing in node logic.

**Phase to address:**
Phase 2 - Durable execution hardening (determinism + idempotency)

---

### Pitfall 3: Missing or unstable `thread_id` strategy

**What goes wrong:**
State does not persist correctly across turns, interrupts, or retries; conversations appear to "forget" context, or wrong state is resumed.

**Why it happens:**
Teams rely on ephemeral IDs, reuse IDs across tenants/sessions, or fail to wire thread identity through all SDK entry points.

**How to avoid:**
Define a canonical thread identity contract early: `{tenant_id}:{conversation_id}:{environment}`. Enforce in API schema, test fixtures, logs, and migration docs. Add negative tests for missing/wrong `thread_id`.

**Warning signs:**
- "Messages are overwritten/replaced" behavior across turns.
- Resuming after interrupt starts a new flow unexpectedly.
- Cross-user state bleed in lower environments.

**Phase to address:**
Phase 2 - Persistence and thread identity design

---

### Pitfall 4: Reducer misuse causes state corruption (especially with subgraphs)

**What goes wrong:**
List channels duplicate or nest unexpectedly (e.g., `operator.add` behavior in subgraph contexts), message history becomes noisy, and retrieval/synthesis consumes malformed context.

**Why it happens:**
Default/append reducers are applied without field-by-field semantics; teams assume "append" always means "merge correctly."

**How to avoid:**
Define reducers per channel intentionally:
- use `add_messages` for message channels,
- custom dedupe/merge reducers for list/state aggregates,
- explicit overwrite semantics for scalar fields.
Add contract tests for parent/subgraph state transitions.

**Warning signs:**
- Duplicated items after subgraph execution.
- Unexpected nested list structures in persisted state.
- Token usage spikes from repeated history fragments.

**Phase to address:**
Phase 3 - State schema and reducer verification

---

### Pitfall 5: Interrupt flow implemented incorrectly

**What goes wrong:**
Human-in-the-loop pauses fail silently, resume values bind to the wrong prompt, or pre-interrupt side effects re-run and duplicate actions.

**Why it happens:**
Interrupt mechanics are exception-driven and index-based in multi-interrupt scenarios; teams place interrupt inside `try/except`, perform side effects before interrupt, or use wrong resume form.

**How to avoid:**
Adopt strict interrupt rules:
- `interrupt()` before any non-idempotent work in that node,
- never wrap `interrupt()` in `try/except`,
- for parallel interrupts, resume with ID-to-value mapping,
- use `Command(resume=...)` only for resumption.

**Warning signs:**
- Interrupt payload never appears in stream output.
- Resume applies answer to the wrong pending question.
- Approval steps trigger action twice after resumption.

**Phase to address:**
Phase 4 - Guardrails and human-review flow migration

---

### Pitfall 6: Retry policy without idempotency boundaries

**What goes wrong:**
Transient failures recover, but repeated attempts duplicate tool/API effects (duplicate records, duplicate notifications, repeated writes).

**Why it happens:**
Retry configuration is added at graph/node level, but external systems are not idempotent and no request keying strategy exists.

**How to avoid:**
For every side-effecting node, require:
- deterministic idempotency key,
- write-before-send or send-with-ledger pattern,
- compensating action policy,
- replay tests that force provider/network failures.

**Warning signs:**
- Retry metrics improve while downstream data quality degrades.
- Duplicate transaction artifacts after controlled chaos tests.
- "Exactly once" claims without dedupe key evidence.

**Phase to address:**
Phase 4 - Retry and side-effect safety controls

---

### Pitfall 7: Recursion and loop controls missing in decomposition/subanswer cycles

**What goes wrong:**
Graphs spin in agent/tool/search loops until `GraphRecursionError` or token/cost blowups, especially in decompose -> search -> subanswer refinement cycles.

**Why it happens:**
Custom orchestrators had implicit guards; migration drops or weakens them and relies only on model behavior.

**How to avoid:**
Set explicit recursion limits, instrument step counters, and implement graceful degradation path (fallback synthesis and stop condition). Add bounded-iteration tests on adversarial prompts.

**Warning signs:**
- Step count rises near recursion limit frequently.
- Long-tail latency spikes with repeated "thinking" steps.
- Cost per request variance widens after migration.

**Phase to address:**
Phase 3 - Control-flow safety and bounded execution

---

### Pitfall 8: Checkpointer setup and durability mode mismatched to SLOs

**What goes wrong:**
Production loses recoverability guarantees (or suffers avoidable latency overhead) because durability mode and checkpointer provisioning are not aligned with failure tolerance goals.

**Why it happens:**
Teams carry dev defaults into production (e.g., in-memory saver, uninitialized persistence), or choose durability mode without explicit RPO/RTO tradeoff analysis.

**How to avoid:**
Treat checkpointing as release-critical infra:
- use production checkpointer backend,
- run initial setup/migrations explicitly,
- document `sync` vs `async` vs `exit` durability policy by endpoint,
- validate crash-recovery behavior in staging.

**Warning signs:**
- Memory saver or local defaults in deployment manifests.
- Mid-run crash resumes from too early or cannot resume.
- Latency regressions without matching durability gains.

**Phase to address:**
Phase 2 - Persistence infrastructure and SLO policy

---

### Pitfall 9: OpenAI baseline drift during orchestration migration

**What goes wrong:**
The migration unintentionally changes model behavior (tool-call formats, structured output handling, refusal handling), creating quality regressions that get misattributed to LangGraph.

**Why it happens:**
Migration mixes orchestration changes with provider/model/response-format changes in the same release.

**How to avoid:**
Lock provider/model baseline first:
- freeze model snapshots and key OpenAI parameters,
- keep output schema strategy stable (Structured Outputs vs JSON mode) during initial cutover,
- run parity eval suite per pipeline node before and after graph migration.

**Warning signs:**
- Validation/synthesis pass rates drop without graph errors.
- Refusal handling suddenly increases in strict schema paths.
- Tool-call parsing failures appear only after model upgrade.

**Phase to address:**
Phase 1 - Baseline freeze and migration acceptance criteria

---

### Pitfall 10: Missing migration guidance for active threads and topology changes

**What goes wrong:**
Major release breaks in-flight sessions/interrupted threads when node names/topology change without a transition plan, causing stuck or invalid resumptions.

**Why it happens:**
Teams treat schema/graph updates like stateless deploys and skip thread lifecycle policy in release docs.

**How to avoid:**
Ship explicit migration runbook:
- classify compatible vs incompatible graph changes,
- drain/complete interrupted threads before incompatible changes,
- version graph definitions and route old threads to old graph until completion.

**Warning signs:**
- Resumption errors appear after deployment with no code exceptions pre-release.
- Interrupted sessions fail only on upgraded environment.
- Support tickets mention "resume no longer works."

**Phase to address:**
Phase 5 - Release migration docs and thread transition operations

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep one giant "orchestrate" node | Fastest initial migration | Poor replay granularity, hard debugging, expensive retries | Only for throwaway spike/prototype |
| Use default reducer behavior everywhere | Less schema work up front | Silent state corruption and duplicate accumulation | Never for production migration |
| Delay idempotency until post-launch | Faster time-to-demo | Recovery bugs become data integrity incidents | Never for side-effecting nodes |
| Mix provider/model upgrades with graph migration | One combined release | Impossible root-cause attribution on regressions | Only with separate parity gates per change |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OpenAI Chat/Responses | Switching output mode/schema and orchestration in one step | Freeze provider settings first; migrate orchestration with parity tests, then optimize schema mode separately |
| Vector/semantic search service | Returning formatted prompt strings from search node | Return raw retrieval artifacts in state; format at synthesis node |
| External write APIs (ticketing/email/CRM) | Retrying non-idempotent writes without operation key | Enforce idempotency key contract and dedupe ledger per external action |
| Human review UI/API | Using new thread ID on resume path | Persist and reuse original `thread_id` from interrupt through resume |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Unbounded message/state accumulation | Token growth, latency drift, rising model cost | Channel-level retention policy + summarization checkpoints + dedupe reducers | Commonly visible at longer sessions or high-turn workloads |
| Overly synchronous durability on all paths | Elevated p95/p99 latency | Choose durability mode per endpoint criticality; reserve strictest mode for high-value transactions | Under concurrent production traffic |
| Coarse nodes with many external calls | Large replay cost after transient fault | Split by side-effect/failure boundary; task-wrap external calls | During provider/network instability |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging full persisted state including raw user and retrieval content | Sensitive data leakage via logs/telemetry | Redact state channels by policy; structured safe logging fields only |
| Persisting human-review payloads without access controls | Cross-tenant exposure of sensitive draft/tool-call data | Tenant-scoped thread/store keys + strict auth on interrupt/resume APIs |
| Trusting model output as validated policy decision | Guardrail bypass and unsafe actions | Separate deterministic validator nodes and enforce hard policy checks before side effects |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Interrupt pauses without clear pending action | Users think system is stuck | Surface interrupt intent, required input, and SLA timer in UI |
| Retry storms hidden from user | Perceived randomness and duplicate outcomes | Show retried-step status and eventual consistency messaging |
| Migration changes answer style with no explanation | Trust loss after major release | Publish migration notes with behavior deltas and known limitations |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Durable execution:** Replay test proves no duplicate external writes after forced crash/restart.
- [ ] **Interrupt workflows:** Resume path verified with same `thread_id`, including multi-interrupt mapping cases.
- [ ] **State reducers:** Parent/subgraph reducer contract tests cover append, overwrite, dedupe, and nested structures.
- [ ] **OpenAI baseline:** Node-level quality parity report (decompose, validate, search use, subanswers, synthesis, guardrails).
- [ ] **Recursion control:** Bounded execution test confirms graceful fallback before recursion limit exhaustion.
- [ ] **Release docs:** Runbook covers active-thread handling, rollback, and graph-version compatibility rules.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Duplicate side effects due to retries/replay | HIGH | Freeze outbound actions, reconcile by idempotency key, backfill ledger, replay only read-only segments |
| State corruption from reducer errors | MEDIUM-HIGH | Stop new runs on affected graph version, patch reducer, repair malformed checkpoints or fork from clean checkpoint |
| Broken resume after topology change | HIGH | Route affected threads to prior graph version, drain interrupted runs, then reintroduce new topology with migration gate |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Node lift-and-shift monoliths | Phase 1 - Graph decomposition and state contract | Review each node against single-purpose/failure-boundary checklist |
| Non-deterministic side effects outside tasks | Phase 2 - Durable execution hardening | Crash/resume test shows no duplicate writes |
| Missing or unstable `thread_id` | Phase 2 - Persistence and thread identity | Multi-turn + interrupt tests retain correct state per tenant/session |
| Reducer misuse in subgraphs | Phase 3 - State schema and reducer verification | Contract tests assert no duplication/nesting regressions |
| Interrupt misimplementation | Phase 4 - Guardrails and HITL migration | End-to-end approval/reject/edit flows pass with resume correctness |
| Retry policy without idempotency | Phase 4 - Retry and side-effect safety | Chaos tests produce no duplicate external actions |
| Recursion/loop runaway | Phase 3 - Control-flow safety | Recursion-limit/fallback tests pass on adversarial prompts |
| Checkpointer/durability mismatch | Phase 2 - Persistence infrastructure | Failure injection validates chosen durability SLO tradeoff |
| OpenAI baseline drift | Phase 1 - Baseline freeze and acceptance criteria | Pre/post migration parity suite remains within thresholds |
| Active-thread migration breakage | Phase 5 - Release migration docs and ops | Staged deploy validates interrupted thread compatibility policy |

## Sources

- LangGraph Overview (official): https://docs.langchain.com/oss/python/langgraph/overview
- LangGraph Durable Execution (official): https://docs.langchain.com/oss/python/langgraph/durable-execution
- LangGraph Persistence (official): https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph Graph API (official): https://docs.langchain.com/oss/python/langgraph/graph-api
- LangGraph Interrupts (official): https://docs.langchain.com/oss/python/langgraph/interrupts
- Thinking in LangGraph (official): https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph
- Functional API Common Pitfalls (official): https://docs.langchain.com/oss/python/langgraph/functional-api#common-pitfalls
- LangGraph issue on `operator.add` duplicates with subgraph (community + maintainer response): https://github.com/langchain-ai/langgraph/issues/4007
- LangGraph issue on reducer behavior in subgraph flows: https://github.com/langchain-ai/langgraph/issues/3587
- LangGraph issue on `add_messages` expectations and thread/checkpointer usage: https://github.com/langchain-ai/langgraph/issues/1568
- OpenAI Structured Outputs guide (official): https://platform.openai.com/docs/guides/structured-outputs
- OpenAI Function Calling guide (official): https://platform.openai.com/docs/guides/function-calling

---
*Pitfalls research for: LangGraph brownfield migration (RAG orchestration)*
*Researched: 2026-03-12*
