# Project Research Summary

**Project:** Agent Search LangGraph Migration (major release)
**Domain:** Brownfield RAG orchestration migration to LangGraph-native state graphs
**Researched:** 2026-03-12
**Confidence:** HIGH

## Executive Summary

This project is a production migration of an existing RAG system from a custom orchestrator to LangGraph-native `StateGraph` execution while preserving FastAPI/React contracts and OpenAI provider behavior. Experts in this space consistently treat this as a reliability-first re-platforming effort: freeze external behavior, move orchestration internals to typed state graphs, and prove parity under real operational conditions before feature expansion.

The recommended approach is to keep retrieval/storage and API contracts stable, introduce an orchestration adapter that supports legacy and LangGraph side-by-side, and adopt Postgres-backed checkpointing early with strict `thread_id` discipline. The MVP should ship explicit state contracts, durable resume/replay semantics, observability with streaming lifecycle events, retrieval parity adapters, and release hygiene (semver + migration docs). This sequence minimizes migration risk and supports gradual cutover through shadow mode, canary, and progressive ramp.

The main risks are deterministic replay failures, state corruption from reducer misuse, side-effect duplication during retries/resume, and baseline drift if model/provider behavior changes during the same release. Mitigation is clear: isolate side effects in task boundaries with idempotency keys, enforce reducer contracts with tests, freeze OpenAI/model settings during cutover, and require parity/evidence gates for each rollout step.

## Key Findings

### Recommended Stack

The stack guidance is strongly aligned with official LangGraph production patterns and fits the current FastAPI + Postgres/pgvector architecture. Use Python 3.12 runtime, LangGraph `~1.1`, and `langgraph-checkpoint-postgres ~3.0` as core orchestration infrastructure, while keeping OpenAI baseline through `langchain-openai ~1.1` and `openai ~2.26`.

Durability and observability are first-class, not optional add-ons. Postgres checkpointer (`PostgresSaver` or async variant), typed Pydantic v2 state/contracts, and trace instrumentation (LangSmith-compatible) are required to validate remote reliability and migration parity before deprecating legacy orchestration.

**Core technologies:**
- `LangGraph (~1.1)`: durable `StateGraph` orchestration runtime - explicit control-flow, typed state, and production execution semantics.
- `langgraph-checkpoint-postgres (~3.0)`: checkpoint persistence - required for resume/replay/interrupt in remote environments.
- `langchain-openai (~1.1)` + `openai (~2.26)`: OpenAI baseline - preserves provider behavior while changing orchestration internals.
- `FastAPI (~0.135)` + `Pydantic (~2.12)`: stable API/schema layer - keeps external contracts intact through migration.
- `Postgres + pgvector + SQLAlchemy/psycopg`: existing retrieval/data platform - avoids simultaneous datastore churn during major-release migration.

### Expected Features

The research is clear that v1 success is defined by parity and reliability, not by adding novel orchestration capabilities first. Table stakes are explicit state contracts, durable checkpoints, streaming lifecycle visibility, observability, retrieval parity, and remote reliability primitives. These are prerequisites for a credible cutover.

Differentiators should follow only after parity stabilizes: dual-run diff harness, time-travel replay UX, and integrated evaluation loops provide outsized value for operating and evolving the system post-migration. Marketplace-style subgraph composition and policy packs are strategic but should not block major-release delivery.

**Must have (table stakes):**
- Explicit typed state + node I/O contracts - foundation for safe graph behavior and versioning.
- Durable execution with checkpointed resume - mandatory for failure recovery and HITL continuity.
- Streaming lifecycle + trace observability - required for debugging and trust in remote environments.
- Retrieval parity adapters - preserves answer quality across migration.
- SDK release hygiene (semver + migration/deprecation docs) - protects integrators during breaking-change window.

**Should have (competitive):**
- Dual-run migration harness with output diff scoring - objective parity confidence and safer cutover.
- Time-travel/branch replay workflows - faster incident triage and debugging.
- Evaluation loops (offline regression + online monitors) - sustained quality governance after launch.

**Defer (v2+):**
- Cost/latency optimization advisor from telemetry.
- Policy-as-code orchestration packs and broader reusable subgraph marketplace.

### Architecture Approach

Use a layered architecture with a stable API/SDK boundary on top, an orchestration adapter in the middle, and LangGraph subgraphs plus persistence/integration services below. Keep legacy and LangGraph runtimes coexisting during migration so rollout can be feature-flagged and reversible without client changes.

**Major components:**
1. **FastAPI routers + SDK facade** - preserve external contracts and map requests to orchestration boundary.
2. **Orchestrator adapter** - selects legacy vs LangGraph path by flag/version/tenant and supports shadow/canary rollout.
3. **LangGraph runtime (entry graph + subgraphs)** - decomposition, retrieval, synthesis, guardrails with typed state/reducers.
4. **Services layer (retrieval/LLM/embedding)** - encapsulates I/O and retry policy outside graph wiring.
5. **Checkpoint + observability layer** - Postgres checkpointer, `thread_id` continuity, traces/metrics for parity evidence.

### Critical Pitfalls

1. **Monolithic node lift-and-shift** - split by failure and side-effect boundary; avoid giant nodes that break replay efficiency.
2. **Side effects outside deterministic task discipline** - wrap provider/external writes in idempotent task boundaries with replay-safe keys.
3. **Unstable `thread_id` strategy** - enforce canonical thread identity contract across API, SDK, logs, and tests.
4. **Reducer misuse in parent/subgraph flows** - define per-channel reducer semantics and test append/overwrite/dedupe behaviors.
5. **OpenAI baseline drift during orchestration migration** - freeze model/provider settings for migration; optimize provider behavior only after parity gates pass.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Baseline Freeze + State Contract Foundation
**Rationale:** All downstream graph work depends on stable provider behavior and explicit state semantics.  
**Delivers:** Canonical `RAGState`, node I/O contracts, reducer definitions, OpenAI/model baseline freeze, migration acceptance criteria.  
**Addresses:** Explicit state contracts, retrieval parity prerequisites, release hygiene foundations.  
**Avoids:** Monolithic lift-and-shift, provider drift, uncontrolled contract changes.

### Phase 2: Durability and Identity Infrastructure
**Rationale:** Remote reliability requirements require persistence and replay correctness before user-visible cutover.  
**Delivers:** Postgres checkpointer integration, `thread_id` contract rollout, idempotency envelope, crash/replay validation.  
**Uses:** `langgraph-checkpoint-postgres`, Postgres/pgvector existing platform, tracing hooks.  
**Implements:** Checkpoint store and continuity flows in architecture.

### Phase 3: Retrieval + Answer Subgraph Migration Behind Adapter
**Rationale:** Move highest-value orchestration paths while preserving rollback and API parity.  
**Delivers:** Orchestrator adapter, retrieval subgraph migration, answer/citation subgraph migration, compatibility mappers.  
**Addresses:** Retrieval parity, streaming/event mapping, progressive shadow validation.  
**Avoids:** API contract rewrites, hidden branch logic, coarse retry surfaces.

### Phase 4: Guardrails, Interrupts, and Retry Safety
**Rationale:** Production cutover requires human-review correctness and side-effect-safe fault handling.  
**Delivers:** HITL interrupt/resume flows, retry/idempotency policy enforcement, loop/recursion bounds, fallback strategies.  
**Addresses:** Human-in-the-loop, policy/confidence gates, operational safety controls.  
**Avoids:** Interrupt misbinding, duplicate side effects, runaway recursion/cost blowups.

### Phase 5: Progressive Rollout, Evaluation, and Legacy Retirement
**Rationale:** Controlled exposure with evidence-based gates prevents high-blast-radius regressions.  
**Delivers:** Shadow -> canary -> ramp execution plan, parity/evaluation reporting, active-thread migration runbook, legacy deprecation.  
**Addresses:** SDK migration confidence, release operations, post-cutover governance.  
**Avoids:** Active-thread breakage, unverified parity cutover, irrecoverable rollback gaps.

### Phase Ordering Rationale

- State contracts and provider freeze precede graph migration to keep causality clear for regressions.
- Persistence/identity precede broad subgraph migration because replay/resume correctness is core to remote reliability.
- Retrieval/answer migration is grouped to validate end-user output parity while adapter keeps rollback available.
- Guardrails/interrupt/retry hardening lands before broad traffic to prevent safety and data-integrity incidents.
- Legacy retirement is last and only after sustained parity and SLO stability.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4:** Interrupt semantics + multi-interrupt resume mapping + side-effect idempotency patterns need implementation-specific validation.
- **Phase 5:** Active-thread/version transition policy and rollout abort thresholds require environment-specific operational design.
- **Phase 3:** Dual-run parity scoring methodology should be calibrated to product-specific quality criteria and datasets.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Typed state/reducer schema and baseline freeze are well-documented in official LangGraph/OpenAI docs.
- **Phase 2:** Postgres checkpointer wiring and `thread_id` continuity patterns are mature and well established.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Strong alignment with official docs and current package baselines; direct fit with existing infra. |
| Features | HIGH | Table stakes and prioritization are consistent across LangGraph production guidance and migration patterns. |
| Architecture | HIGH | Recommended boundaries and phased cutover are well supported; specific class/module split remains implementation-tunable. |
| Pitfalls | HIGH | Critical pitfalls map to documented LangGraph durability/interrupt behavior plus observed community failure modes. |

**Overall confidence:** HIGH

### Gaps to Address

- **Parity thresholds definition:** Define quantitative acceptance metrics (citation overlap, structure fidelity, latency/error deltas) before canary.
- **Thread/version transition policy:** Specify handling for in-flight threads across incompatible graph topology changes.
- **Durability mode per endpoint:** Finalize `sync/async/exit` policy by endpoint criticality and SLO target.
- **Evaluation dataset coverage:** Build representative regression dataset for decomposition/retrieval/synthesis/guardrail node-level parity checks.
- **Operational rollback automation:** Define abort triggers and automated rollback controls for each rollout stage.

## Sources

### Primary (HIGH confidence)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) - production positioning and architecture baseline.
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) and [Use graph API](https://docs.langchain.com/oss/python/langgraph/use-graph-api) - state graph patterns.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) - checkpointing design and production backends.
- [LangGraph durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution) - determinism, replay, and idempotency requirements.
- [LangGraph interrupts / HITL](https://docs.langchain.com/oss/python/langgraph/interrupts) and [Human-in-the-loop](https://docs.langchain.com/oss/python/langgraph/human-in-the-loop) - pause/resume semantics.
- [LangGraph streaming](https://docs.langchain.com/oss/python/langgraph/streaming) and [Subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) - event and composition patterns.
- [LangGraph RemoteGraph usage](https://docs.langchain.com/langgraph-platform/use-remote-graph) and [Agent Server runtime](https://docs.langchain.com/langgraph-platform/langgraph-server) - remote execution model.
- [LangSmith tracing](https://docs.langchain.com/langsmith/trace-with-langgraph) and [distributed tracing](https://docs.langchain.com/langsmith/agent-server-distributed-tracing) - observability requirements.
- [LangSmith evaluation](https://docs.langchain.com/langsmith/evaluation) - quality gating patterns.
- [LangGraph v1 migration guide](https://docs.langchain.com/oss/python/migrate/langgraph-v1) and [v1 release notes](https://docs.langchain.com/oss/python/releases/langgraph-v1) - migration implications.
- [openai-python README](https://raw.githubusercontent.com/openai/openai-python/main/README.md) - provider API baseline guidance.
- [OpenAI Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs) and [Function calling guide](https://platform.openai.com/docs/guides/function-calling) - output/tooling stability considerations.

### Secondary (MEDIUM confidence)
- [LangGraph add-memory how-to](https://langchain-ai.github.io/langgraph/how-tos/memory/add-memory/) - practical checkpointer setup patterns.
- [Agent Server changelog](https://docs.langchain.com/langsmith/agent-server-changelog) - trend signals affecting rollout planning.

### Tertiary (LOW confidence)
- [Reducer behavior issue #4007](https://github.com/langchain-ai/langgraph/issues/4007) - subgraph reducer edge case evidence, validate in local tests.
- [Reducer behavior issue #3587](https://github.com/langchain-ai/langgraph/issues/3587) - additional community-reported merge behavior caveats.
- [add_messages/thread usage issue #1568](https://github.com/langchain-ai/langgraph/issues/1568) - community troubleshooting signal, not normative spec.

---
*Research completed: 2026-03-12*
*Ready for roadmap: yes*
