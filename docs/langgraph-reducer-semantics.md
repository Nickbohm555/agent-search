# LangGraph Reducer Semantics

This document defines the deterministic merge rules used by the runtime graph state reducer layer in `src/backend/agent_search/runtime/reducers.py`.

## Channel Rules

| Channel | Reducer | Semantics | Determinism guarantee |
| --- | --- | --- | --- |
| `decomposition_sub_questions` | `merge_decomposition_sub_questions` | Append in first-seen order after trimming blanks and deduplicating case-insensitively. | Equivalent input sequences always emit the same normalized question list. |
| `sub_question_artifacts` | `merge_sub_question_artifacts` | Preserve first insertion order by `sub_question`; later updates replace the full artifact for that key. | Fan-in merges keep a stable lane order while still applying last-write-wins replacement. |
| `citation_rows_by_index` | `merge_citation_rows_by_index` | Merge dictionaries by integer citation index; later values replace earlier values for the same index; final map is key-sorted. | Equivalent updates always serialize in ascending citation index order. |
| `sub_qa` | `merge_sub_qa` | Preserve first insertion order by `sub_question`; later updates replace the full answer object for that key. | Parallel and sequential lane completions converge to the same ordered answer list. |
| `stage_snapshots` | `merge_stage_snapshots` | Append-only list of emitted snapshots with deep copies on both current and update inputs. | Snapshot history reflects explicit emission order without aliasing prior state. |

## Implementation Notes

- Reducers are pure merge helpers. They do not mutate caller-owned lists, dictionaries, or Pydantic model instances.
- Replacement channels use keyed overwrite semantics only after the key's first position has been established.
- Collection ordering is owned by reducer logic, not by thread completion timing or incidental Python dict merge behavior.
- Citation row merges normalize keys to integers before sorting, so serialization stays stable even if callers pass mixed numeric-like keys.
- Snapshot merges are intentionally append-only because snapshots model observed execution history, not a keyed registry.

## Service-Level Expectations

- `apply_decompose_node_output_to_graph_state` seeds ordered `decomposition_sub_questions`, `sub_question_artifacts`, and `sub_qa`.
- `apply_expand_node_output_to_graph_state`, `apply_search_node_output_to_graph_state`, `apply_rerank_node_output_to_graph_state`, and `apply_answer_subquestion_node_output_to_graph_state` must delegate merge-sensitive channels to shared reducers.
- `run_parallel_graph_runner` may finish lane work out of order, but the merged state must still match the deterministic reducer contract.
- `run_sequential_graph_runner` must produce the same final state shape and ordering as equivalent repeated runs.

## Examples

### `decomposition_sub_questions`

Input:

```text
current = ["What changed?", "what changed?", "Why now?"]
update = ["Why now?", "What next?"]
```

Output:

```text
["What changed?", "Why now?", "What next?"]
```

### `sub_question_artifacts` and `sub_qa`

Input order establishes lane order. A later update for `"Sub-question B?"` replaces the object payload for that key but does not move it ahead of `"Sub-question A?"`.

### `citation_rows_by_index`

If one branch emits `{2: row_old, 1: row_a}` and another emits `{2: row_new, 3: row_c}`, the merged result serializes as `{1: row_a, 2: row_new, 3: row_c}`.

### `stage_snapshots`

Snapshots are appended exactly as emitted:

```text
["decompose", "expand", "search", "rerank", "answer", "synthesize_final"]
```

The reducer never deduplicates or reorders snapshots because their sequence is itself execution evidence.

## Test Parity

- Unit reducer determinism coverage lives in `src/backend/tests/sdk/test_runtime_reducers.py`.
- Repeat-run graph runner determinism coverage lives in `src/backend/tests/services/test_agent_service.py`.
- Documentation and tests should stay aligned: append, replace, dedupe, and stable-order semantics in this file must match those test assertions.
