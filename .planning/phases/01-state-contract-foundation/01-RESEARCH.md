# Phase 1: State Contract Foundation - Research

**Researched:** 2026-03-12
**Domain:** LangGraph state contracts, node schema contracts, deterministic reducer semantics
**Confidence:** HIGH

## Summary

Phase 1 should establish a single canonical graph state contract that is first-class in the SDK and directly compatible with LangGraph's `StateGraph` model (`State -> Partial`). The current codebase already has strongly typed Pydantic models for state and node I/O (`AgentGraphState`, `DecomposeNodeInput`, `SearchNodeOutput`, etc.) in both backend and `sdk/core`, but it does not yet expose a canonical `RAGState` contract and does not define reducer behavior as an explicit contract artifact.

LangGraph's official API supports `TypedDict`, dataclass, and Pydantic for state schemas, with `TypedDict` as the primary documented shape and reducer behavior encoded per-key (via `Annotated[..., reducer]`). Official error guidance (`INVALID_CONCURRENT_GRAPH_UPDATE`) confirms that parallel updates to the same key require reducers to avoid runtime ambiguity. This directly maps to SGF-03 and should be codified now, before deeper durability/cutover work.

Planning should therefore center on three concrete deliverables: (1) canonical `RAGState` contract exported from SDK surface, (2) explicit per-node input/output schema contracts with a traceable mapping to graph nodes, and (3) deterministic merge rules documented and regression-tested with repeat-run assertions.

**Primary recommendation:** Define and export one canonical `RAGState` (plus reducer map) in `sdk/core`, make backend/runtime consume that same contract, and add determinism tests that prove stable merge outcomes under parallel fanout.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | `1.0.10` (from `uv.lock`) | Graph runtime (`StateGraph`, reducers, fanout semantics) | Official orchestration layer for stateful graph execution and reducer-driven merges |
| `langchain` | `1.2.10` (from `uv.lock`) | Host framework that pulls `langgraph` integration and model abstractions | Existing project dependency baseline; aligned with current runtime |
| `pydantic` | `2.10.6` (pinned in project) | Runtime validation/serialization for schema boundaries | Already used extensively for SDK/API contracts and node payload models |
| `typing_extensions` / `typing` | project runtime | `TypedDict`, `Annotated`, `Literal`, etc. for static contracts | Native way to express reducer-bearing state keys and schema constraints |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langgraph-checkpoint` | `4.0.1` (transitive in lockfile) | Checkpoint/persistence substrate for future phases | Keep compatible now; Phase 2 will depend on this |
| `langgraph-prebuilt` | `1.0.8` (transitive in lockfile) | Prebuilt helpers | Use only if a prebuilt primitive exactly fits; not required for SGF-01/02/03 |
| `pytest` | existing test stack | Determinism/regression tests for merge semantics | Required for repeatability proof and contract non-regression |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `TypedDict` state schema | Pydantic `BaseModel` state schema | Pydantic adds runtime validation but LangGraph docs note lower performance; `TypedDict` is the primary documented graph-state path |
| Reducer-per-key with `Annotated` | Ad-hoc merge logic in node code | Ad-hoc merges are harder to reason about, less composable, and bypass LangGraph's conflict/error model |

**Installation:**
```bash
cd src/backend && uv add langgraph
```

Note: `langgraph` is already present transitively via `langchain`; keep explicit dependency visibility if this phase makes direct imports first-class.

## Architecture Patterns

### Recommended Project Structure
```text
sdk/core/src/
├── agent_search/state_contract.py          # canonical RAGState + reducer annotations
├── agent_search/node_contracts.py          # explicit NodeInput/NodeOutput schemas and node registry metadata
├── agent_search/runtime/graph_builder.py   # StateGraph wiring, reducer-aware channels
└── schemas/agent.py                        # compatibility models / transport models

src/backend/
├── agent_search/runtime/                   # consume sdk/core canonical contracts
└── tests/contracts/                        # deterministic reducer + contract compatibility tests
```

### Pattern 1: Canonical Contract Module
**What:** Define one `RAGState` as the authoritative orchestration-state contract and export it from the SDK package root.
**When to use:** Always; this is SGF-01's core artifact.
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/graph-api#state
from typing import Annotated
from typing_extensions import TypedDict
import operator

class RAGState(TypedDict):
    main_question: str
    decomposition_sub_questions: list[str]
    # Reducer-bearing channels for fanout/fanin phases
    stage_events: Annotated[list[dict], operator.add]
```

### Pattern 2: Node Contract Pairing
**What:** Every graph node has explicit `NodeInput` and `NodeOutput` schema types with a stable name mapping.
**When to use:** For all defined nodes (`decompose`, `expand`, `search`, `rerank`, `answer`, `synthesize_final`).
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/use-graph-api#define-input-and-output-schemas
class SearchNodeInput(BaseModel):
    sub_question: str
    expanded_queries: list[str] = Field(default_factory=list)

class SearchNodeOutput(BaseModel):
    retrieved_docs: list[CitationSourceRow] = Field(default_factory=list)
```

### Pattern 3: Reducer-First Parallel Design
**What:** Any state key updated by multiple branches in one super-step must have reducer semantics defined in the state contract.
**When to use:** Fanout/fanin, `Send` map-reduce, parent/subgraph shared key updates.
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/errors/INVALID_CONCURRENT_GRAPH_UPDATE
from typing import Annotated
import operator

class State(TypedDict):
    aggregate: Annotated[list[str], operator.add]
```

### Anti-Patterns to Avoid
- **Implicit merge behavior:** relying on "whatever order branches finish" without reducer semantics leads to brittle state updates and possible runtime errors.
- **Split state definitions across backend and SDK without a canonical source:** duplicated contracts drift and break SGF-01.
- **Undocumented node payload contracts:** relying on inferred dict shapes instead of typed classes undermines SGF-02.
- **Reducer bypass without intent:** using overwrite-like behavior casually erases accumulated data and breaks determinism guarantees.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent branch state merge | Custom merge ordering in executor callbacks | LangGraph key-level reducers (`Annotated[..., reducer]`) | Official semantics already handle parallel updates and conflict detection |
| Chat message append/update semantics | Manual list append/update logic with ad-hoc ID handling | `add_messages` reducer | Handles append + same-ID replacement + message normalization |
| State overwrite escape hatch | Custom "reset" branch logic | `Overwrite` type | Explicitly documents reducer bypass semantics and failure mode on multiple overwrites |
| Node contract docs generation | Hand-maintained prose disconnected from code | Schema-driven docs from typed `NodeInput`/`NodeOutput` models | Prevents drift and keeps SGF-02 verifiable from code |

**Key insight:** LangGraph already defines the state-update algebra; implementing custom merge semantics outside reducer channels increases nondeterminism risk and future migration cost.

## Common Pitfalls

### Pitfall 1: Parallel key updates without reducers
**What goes wrong:** Graph raises `INVALID_CONCURRENT_GRAPH_UPDATE` when multiple nodes in the same super-step write the same key.
**Why it happens:** Key has default overwrite semantics and no reducer.
**How to avoid:** Annotate every potentially fanout-updated key with an explicit reducer function.
**Warning signs:** Intermittent failures only when branch parallelism is enabled.

### Pitfall 2: Contract drift between backend and SDK
**What goes wrong:** Backend state shape and SDK-exported types diverge, forcing custom shims for consumers.
**Why it happens:** Duplicate schema definitions are maintained manually in multiple trees.
**How to avoid:** Canonicalize `RAGState` and node contracts in one SDK module and import everywhere else.
**Warning signs:** Same field exists with slightly different defaults/types in `src/backend` vs `sdk/core`.

### Pitfall 3: Non-deterministic merge outcomes despite reducers
**What goes wrong:** Equivalent runs produce different ordered collections.
**Why it happens:** Reducer operation or branch payloads depend on unstable ordering/side effects.
**How to avoid:** Keep reducers pure; sort or key-normalize where semantic order matters; test repeated runs for exact equality.
**Warning signs:** Flaky tests around list-like fields under fanout.

### Pitfall 4: Overusing Pydantic in hot path state channels
**What goes wrong:** Latency and memory overhead increase in graph-heavy execution.
**Why it happens:** Deep recursive validation for every transition.
**How to avoid:** Use `TypedDict` for internal graph state channels; reserve Pydantic for API boundaries and node payload validation.
**Warning signs:** Profiling shows validation overhead dominating node runtime.

## Code Examples

Verified patterns from official sources:

### Reducer-based state key for fanout safety
```python
# Source: https://docs.langchain.com/oss/python/langgraph/errors/INVALID_CONCURRENT_GRAPH_UPDATE
import operator
from typing import Annotated
from typing_extensions import TypedDict

class State(TypedDict):
    some_key: Annotated[list, operator.add]
```

### Explicit graph input/output schema boundaries
```python
# Source: https://docs.langchain.com/oss/python/langgraph/use-graph-api#define-input-and-output-schemas
class InputState(TypedDict):
    user_input: str

class OutputState(TypedDict):
    graph_output: str

class OverallState(TypedDict):
    user_input: str
    graph_output: str
    internal_key: str

builder = StateGraph(OverallState, input_schema=InputState, output_schema=OutputState)
```

### Message-safe reducer (append + update-by-id)
```python
# Source: https://reference.langchain.com/python/langgraph/graph/message/add_messages/
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `config_schema` for run config | `context_schema` on `StateGraph` | Deprecated in LangGraph v0.6.0 (removal planned in v2.0.0) | New graph contracts should use `context_schema` to avoid technical debt |
| Implicit overwrite-only behavior for all keys | Per-key reducer contracts with `Annotated` | Matured in current LangGraph 1.x docs | Deterministic, explicit merge rules are now baseline expectation |
| Manual message list handling | `add_messages` reducer / `MessagesState` | Current LangGraph 1.x docs | Lower bug surface for message normalization and update semantics |

**Deprecated/outdated:**
- `config_schema` on `StateGraph`: deprecated; use `context_schema`.
- Treating parallel fanout merges as overwrite-safe by default: conflicts now explicitly error without reducers.

## Open Questions

1. **Canonical state representation type for `RAGState`**
   - What we know: LangGraph supports `TypedDict`, dataclass, and Pydantic; docs position `TypedDict` as primary and note Pydantic performance cost.
   - What's unclear: Whether this repo wants strict runtime validation in the graph hot path or only at boundaries.
   - Recommendation: Plan around `TypedDict` canonical graph state plus Pydantic boundary models; if team prefers Pydantic-only, require a benchmark gate.

2. **Exact reducer definitions for each mutable channel in current RAG flow**
   - What we know: Existing flow has fanout lanes and order-sensitive collections (`sub_qa`, provenance, citations, snapshots).
   - What's unclear: Which channels should be append-only, overwrite, keyed-merge, or post-sort canonicalized.
   - Recommendation: Create a reducer matrix table in implementation docs and pair each channel with deterministic tests.

3. **Documentation surface for SGF-02 "reference docs"**
   - What we know: Node I/O schema models already exist in code.
   - What's unclear: Whether reference docs should be generated from code or hand-authored.
   - Recommendation: Plan auto-generated contract docs from schema introspection to prevent drift.

## Sources

### Primary (HIGH confidence)
- [LangGraph Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api) - state schema model, reducers, super-step semantics, parallel edge behavior
- [LangGraph "Use the graph API"](https://docs.langchain.com/oss/python/langgraph/use-graph-api) - state types, reducer patterns, distinct input/output schema guidance
- [LangGraph `INVALID_CONCURRENT_GRAPH_UPDATE`](https://docs.langchain.com/oss/python/langgraph/errors/INVALID_CONCURRENT_GRAPH_UPDATE) - official concurrent update failure mode and reducer requirement
- [LangGraph `StateGraph` reference](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/) - canonical node signature (`State -> Partial`) and constructor schema parameters
- [LangGraph `add_messages` reference](https://reference.langchain.com/python/langgraph/graph/message/add_messages/) - message reducer semantics
- [LangGraph `Overwrite` reference](https://reference.langchain.com/python/langgraph/types/Overwrite/) - reducer bypass semantics and constraints
- Repository sources:
  - `src/backend/schemas/agent.py`
  - `sdk/core/src/schemas/agent.py`
  - `src/backend/services/agent_service.py`
  - `src/backend/tests/services/test_agent_service.py`
  - `src/backend/uv.lock`

### Secondary (MEDIUM confidence)
- None needed; primary sources were sufficient.

### Tertiary (LOW confidence)
- None included.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - based on repository lockfile versions and official LangGraph docs/reference.
- Architecture: HIGH - based on official Graph API/state/reducer guidance and direct mapping to existing code.
- Pitfalls: HIGH - directly supported by official error docs plus repository fanout patterns/tests.

**Research date:** 2026-03-12
**Valid until:** 2026-04-11 (30 days; LangGraph API surface is active and should be revalidated before implementation starts if delayed)
