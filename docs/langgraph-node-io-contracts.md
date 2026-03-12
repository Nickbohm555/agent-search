# LangGraph Node I/O Contracts

This document is the human-readable reference for the runtime node I/O registry in `src/backend/agent_search/runtime/node_contracts.py`.

It is intentionally contract-focused:

- Node name
- Input schema
- Output schema
- Runtime implementation entrypoint

Tests in `src/backend/tests/sdk/test_node_contract_registry.py` compare this table against the runtime registry so docs drift fails CI.

## Canonical Registry

| Node | Input schema | Output schema | Implementation |
| --- | --- | --- | --- |
| `decompose` | `DecomposeNodeInput` | `DecomposeNodeOutput` | `agent_search.runtime.nodes.decompose.run_decomposition_node` |
| `expand` | `ExpandNodeInput` | `ExpandNodeOutput` | `agent_search.runtime.nodes.expand.run_expansion_node` |
| `search` | `SearchNodeInput` | `SearchNodeOutput` | `agent_search.runtime.nodes.search.run_search_node` |
| `rerank` | `RerankNodeInput` | `RerankNodeOutput` | `agent_search.runtime.nodes.rerank.run_rerank_node` |
| `answer_subquestion` | `AnswerSubquestionNodeInput` | `AnswerSubquestionNodeOutput` | `agent_search.runtime.nodes.answer.run_answer_node` |
| `synthesize_final` | `SynthesizeFinalNodeInput` | `SynthesizeFinalNodeOutput` | `agent_search.runtime.nodes.synthesize.run_synthesize_node` |

## Notes

The registry is code-first. If a node contract changes, update `src/backend/agent_search/runtime/node_contracts.py` first and then update this document.

Schema classes live in `src/backend/schemas/agent.py`.

The runtime node implementations currently live in:

- `src/backend/agent_search/runtime/nodes/decompose.py`
- `src/backend/agent_search/runtime/nodes/expand.py`
- `src/backend/agent_search/runtime/nodes/search.py`
- `src/backend/agent_search/runtime/nodes/rerank.py`
- `src/backend/agent_search/runtime/nodes/answer.py`
- `src/backend/agent_search/runtime/nodes/synthesize.py`

This reference does not describe reducer behavior, orchestration order, or service internals.

Those concerns belong in separate runtime documentation and tests.

## Update Workflow

1. Change the runtime node implementation or schema contract.
2. Update `src/backend/agent_search/runtime/node_contracts.py`.
3. Update the table in this file.
4. Run `docker compose exec backend uv run pytest src/backend/tests/sdk/test_node_contract_registry.py`.

The pytest suite will fail if:

- A runtime node export is missing from the registry.
- A documented row is missing or extra.
- A documented schema name or implementation entrypoint no longer matches the registry.
