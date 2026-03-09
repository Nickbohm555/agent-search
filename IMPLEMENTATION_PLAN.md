
Tasks are in **recommended implementation order** (1...n). Each section = one context window. Complete one section at a time.

Current section to work on: section 15. (move +1 after each turn)

---

## Section 1: Define state graph contracts - graph state and node IO

**Single goal:** Introduce a typed state model and node contracts for the full workflow before migrating execution.

**Details:**
- Define graph-level state for: `main_question`, `decomposition_sub_questions`, per-subquestion artifacts (`expanded_queries`, `retrieved_docs`, `reranked_docs`, `sub_answer`), and `final_answer`.
- Define stable node input/output contracts for nodes: `decompose`, `expand`, `search`, `rerank`, `answer_subquestion`, `synthesize_final`.
- Keep compatibility fields used by current API response (`sub_qa`, `output`) so migration is non-breaking.
- Define citation carrier format in state (ranked source rows keyed by citation index).
- Include observability identifiers in run state/metadata (`run_id`, trace/correlation ids) so `langfuse` traces can be attached consistently across nodes.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies required.
- Tooling (uv, poetry, Docker): no container/runtime changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/schemas/agent.py` | Add graph-state-adjacent typed models for staged artifacts. |
| `src/backend/services/agent_service.py` | Host shared state-contract definitions and conversion helpers. |
| `src/backend/utils/langfuse_tracing.py` | Reuse existing tracing helpers for graph-state run metadata conventions. |
| `src/backend/tests/services/test_agent_service.py` | Validate state-shape and backward-compatible response mapping. |

**How to test:** Run backend schema/service tests to confirm graph state maps cleanly to existing `RuntimeAgentRunResponse`.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 2: Build decomposition node from existing logic - state-graph entry

**Single goal:** Reuse current decomposition logic as the first graph node that produces normalized sub-questions.

**Details:**
- Lift current decomposition-only logic into a dedicated graph node.
- Keep existing normalization guarantees (atomic questions ending with `?`, dedupe, max/min handling).
- Emit `decomposition_sub_questions` immediately into graph state for downstream fanout and UI.
- Preserve fallback behavior when LLM decomposition fails.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Extract decomposition into reusable graph node function. |
| `src/backend/schemas/decomposition.py` | Continue using structured decomposition output contract. |
| `src/backend/tests/services/test_agent_service.py` | Verify node behavior and fallback logic. |

**How to test:** Run decomposition-focused backend tests; confirm node emits normalized sub-questions in state.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 3: Build expansion node - query list generation per sub-question

**Single goal:** Add a graph node that expands each sub-question into a bounded query list.

**Details:**
- For each sub-question, generate `queries` containing original question plus expansions.
- Use `langchain` `MultiQueryRetriever` query-generation flow to produce alternate phrasings per sub-question.
- Apply normalization: trim, dedupe, drop empties, cap count and query length.
- Keep deterministic fallback to original question when expansion fails.
- Store expansions per sub-question in graph state.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): use `langchain` `MultiQueryRetriever` for expansion generation.
- Tooling (uv, poetry, Docker): optional env settings for expansion count/limits.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/pyproject.toml` | Add/lock query-expansion dependencies (`langchain` explicit version/range as needed). |
| `src/backend/services/query_expansion_service.py` | Library-backed query expansion wrapper (`MultiQueryRetriever`) with normalization/fallback. |
| `src/backend/services/agent_service.py` | Implement expansion node and state updates. |
| `src/backend/tests/services/test_agent_service.py` | Test expansion list generation and fallback behavior. |
| `src/backend/tests/services/test_query_expansion_service.py` | Verify library-backed expansion behavior and deterministic fallback path. |

**How to test:** Run backend tests verifying expansion node outputs include original query and bounded expansions.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 4: Build search node - multi-query retrieval with merge/dedupe

**Single goal:** Implement graph search node that retrieves across expanded queries and merges candidates.

**Details:**
- For each sub-question, run retrieval for each expanded query with over-fetch (`k_fetch`).
- Merge/dedupe by stable key (`document_id` preferred; fallback source+content key).
- Keep deterministic ordering before rerank fallback path.
- Store merged candidate set and retrieval provenance in graph state.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): configurable `k_fetch` via env.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Implement search node orchestration and merge logic. |
| `src/backend/services/vector_store_service.py` | Reuse retrieval primitives in graph node execution. |
| `src/backend/tests/services/test_agent_service.py` | Validate multi-query retrieval merge and dedupe behavior. |

**How to test:** Run backend tests and verify merged retrieval candidates are deduplicated and deterministic.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 5: Build rerank node - reorder retrieved candidates before answering

**Single goal:** Add reranking node that reorders merged retrieval candidates and trims to final top_n context.

**Details:**
- Score merged candidate documents with a library reranker (`flashrank`) against sub-question semantics.
- Select top `top_n` reranked documents for answer generation.
- Keep deterministic fallback to non-reranked order if reranker fails/unavailable.
- Persist rerank scores/order in graph state for observability.
- Explicitly remove and prohibit custom lexical-overlap reranking implementations for production path.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): use `flashrank` for reranking models/inference.
- Tooling (uv, poetry, Docker): env config for rerank enable/top_n.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/pyproject.toml` | Add `flashrank` dependency for production reranking. |
| `src/backend/services/agent_service.py` | Implement rerank node and fallback behavior. |
| `src/backend/services/reranker_service.py` | Provide `flashrank`-backed reranking adapter/config. |
| `src/backend/tests/services/test_reranker_service.py` | Validate ranking quality and fallback behavior. |
| `src/backend/tests/services/test_agent_service.py` | Verify rerank node state transitions and outputs. |

**How to test:** Run reranker and agent-service tests; confirm top_n docs differ from raw retrieval when reranking is enabled.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 6: Build subanswer node - answer per sub-question with citations

**Single goal:** Generate one grounded subanswer per sub-question using reranked docs and mandatory citation markers.

**Details:**
- Build prompt contract: answer only from reranked docs; include citation markers like `[1]`, `[2]`.
- Return exact fallback `nothing relevant found` when docs do not support an answer.
- Store `sub_answer`, citation usage, and supporting source rows in graph state.
- Keep output aligned with existing `SubQuestionAnswer` fields.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Implement subanswer node and state updates. |
| `src/backend/services/subanswer_service.py` | Reuse/extend subanswer generation contract. |
| `src/backend/services/subanswer_verification_service.py` | Validate citation presence/supportability. |
| `src/backend/tests/services/test_agent_service.py` | Verify subanswers include citations or correct fallback. |

**How to test:** Run backend subanswer/verification tests and confirm citation markers map to ranked doc rows.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 7: Build final synthesis node - compose final answer from subanswers

**Single goal:** Synthesize final answer from per-subquestion answers while preserving grounded citations.

**Details:**
- Use `main_question` + collected subanswers as synthesis inputs.
- Preserve citation grounding in final output (carry through or remap citations deterministically).
- Ensure final output remains concise and evidence-bound.
- Keep API response shape unchanged (`output` + `sub_qa`).

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/initial_answer_service.py` | Adapt synthesis for state-graph inputs/outputs. |
| `src/backend/services/agent_service.py` | Invoke synthesis node and map graph state to response. |
| `src/backend/tests/services/test_initial_answer_service.py` | Verify grounded final synthesis behavior. |

**How to test:** Run synthesis tests and verify final answer uses subanswer evidence with stable citations.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 8: Assemble graph runner - sequential lane only

**Single goal:** Implement a sequential graph runner that executes nodes in strict order for one sub-question at a time.

**Details:**
- Graph order: `decompose -> (for each sub-question: expand -> search -> rerank -> answer) -> synthesize_final`.
- Run sub-question lane sequentially in this section to simplify correctness/debugging.
- Keep legacy deep-agent code untouched in this section; only add sequential graph runner and tests.
- Defer parallel fanout and state snapshot emission to Section 9.
- Keep `langfuse` tracing active in this new graph path (start handler, attach callbacks, flush at run end/finally).

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies required.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Implement graph runner and node orchestration. |
| `src/backend/utils/langfuse_tracing.py` | Provide callback lifecycle utilities reused by graph runner execution. |
| `src/backend/tests/services/test_agent_service.py` | Validate sequential graph order and deterministic outputs. |

**How to test:** Run agent-service tests verifying strict sequential node execution and stable outputs.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 9: Add parallel sub-question fanout and state snapshots

**Single goal:** Add controlled parallelism for per-subquestion lanes and emit snapshot state for progress reporting.

**Details:**
- Parallelize `expand -> search -> rerank -> answer` per sub-question with bounded workers.
- Preserve deterministic output order by reindexing results to original sub-question order.
- Emit stage snapshots required by async status and progressive UI.
- Keep business logic unchanged from sequential runner; this section is orchestration-only.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): optional env for max workers.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Add bounded parallel fanout and snapshot emission. |
| `src/backend/tests/services/test_agent_service.py` | Verify deterministic ordering and snapshot payload correctness under parallel execution. |

**How to test:** Run agent-service tests with multiple sub-questions to verify ordering is stable and snapshots emit expected stage data.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 10: Migrate API endpoint to graph backend - deep-agent decoupling

**Single goal:** Switch `/api/agents/run` to execute the new graph runner instead of deep-agents.

**Details:**
- Route runtime requests through graph runner in `run_runtime_agent`.
- Keep request/response API contract unchanged for frontend compatibility.
- Add feature flag for rollback during migration window (temporary).
- Isolate deep-agent-specific callbacks from the primary runtime path, but do not delete legacy files yet.
- Preserve `langfuse` integration on the primary runtime path; ensure graph runs emit traces with stage/node context.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): optional env feature flag.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/routers/agent.py` | Keep endpoint stable while swapping backend orchestration. |
| `src/backend/services/agent_service.py` | Use graph runner as primary execution path. |
| `src/backend/utils/langfuse_tracing.py` | Keep tracing callback wiring stable across migration and flag states. |
| `src/backend/tests/api/test_agent_run.py` | Confirm endpoint behavior is preserved post-migration. |

**How to test:** Run API + service tests and confirm `/api/agents/run` returns compatible payloads using graph execution with feature flag on/off.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 11: Async run-status for progressive subquestion visibility

**Single goal:** Expose staged graph progress so UI can show subquestions as soon as decomposition completes.

**Details:**
- Add async run job endpoints: start, status, optional cancel.
- Emit run stages including `subquestions_ready` immediately after decomposition node.
- Return partial graph state (`decomposition_sub_questions`, stage metadata) in status payload.
- Keep sync endpoint intact for compatibility.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies; reuse current in-memory job pattern.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_jobs.py` | Manage graph run jobs and staged updates. |
| `src/backend/routers/agent.py` | Add async run/status/cancel endpoints. |
| `src/backend/schemas/agent.py` | Define staged async response payloads. |
| `src/backend/tests/api/test_agent_run.py` | Verify staged status behavior and partial outputs. |

**How to test:** Run API/job tests and manually confirm status returns subquestions before final answer completion.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 12: Frontend run timeline shell - progressive container and stage rail

**Single goal:** Add a reusable progressive run shell that displays ordered stages for the full flow.

**Details:**
- Add a stage rail/timeline with canonical order: `decompose -> expand -> search -> rerank -> answer -> final`.
- Render per-stage status (`pending`, `in_progress`, `completed`, `error`) from async run-status payloads.
- Keep this section focused on container and status wiring only (no stage-specific payload rendering yet).

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new frontend dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Add stage-status types required by timeline shell. |
| `src/frontend/src/App.tsx` | Add progressive run shell and stage rail UI. |
| `src/frontend/src/App.test.tsx` | Verify ordered stage rail and status transitions. |

**How to test:** Run frontend tests and verify stage rail status updates correctly during polling.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 13: Decompose stage view - immediate sub-question display

**Single goal:** Render decomposed sub-questions as soon as decomposition completes.

**Details:**
- At `subquestions_ready`, render `decomposition_sub_questions` in a dedicated Decompose panel.
- Show question count and normalization status indicators.
- Keep panel independent from later stage artifacts.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/App.tsx` | Add Decompose panel and subquestion list rendering. |
| `src/frontend/src/App.test.tsx` | Verify Decompose panel appears before later stages complete. |

**How to test:** Run frontend tests and manual run to confirm sub-questions appear before expansion/search/rerank results.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 14: Expand stage view - per-subquestion expanded query list

**Single goal:** Render expansion outputs for each sub-question in a dedicated Expand panel.

**Details:**
- Show original sub-question and generated expanded queries list.
- Show fallback badge when expansion collapses to original query only.
- Keep data grouped by sub-question index for stable traceability.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Add expansion artifact fields to staged payload types. |
| `src/frontend/src/App.tsx` | Add Expand panel UI grouped by sub-question. |
| `src/frontend/src/App.test.tsx` | Verify expanded query lists and fallback badges render correctly. |

**How to test:** Run frontend tests and confirm expanded queries show per sub-question after expansion stage.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 15: Search stage view - retrieval candidates and merge provenance

**Single goal:** Render search-stage outputs showing merged retrieval candidates before reranking.

**Details:**
- Show per-subquestion candidate count after multi-query merge/dedupe.
- Render top candidate preview rows with source/title snippets.
- Show merge stats (`raw_hits`, `deduped_hits`) for transparency.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Add search merge stats/candidate preview types. |
| `src/frontend/src/App.tsx` | Add Search panel for merged candidate previews. |
| `src/frontend/src/App.test.tsx` | Verify search candidate counts and merge stats rendering. |

**How to test:** Run frontend tests and verify Search panel displays merged candidate stats before rerank completes.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 16: Rerank stage view - reordered top_n evidence

**Single goal:** Render reranked evidence and score/order changes per sub-question.

**Details:**
- Show reranked top_n list for each sub-question with final order and optional score.
- Display rerank fallback notice when reranking was bypassed.
- Keep links/snippets aligned with citation index that answer stage will use.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Add rerank artifact/fallback fields to payload types. |
| `src/frontend/src/App.tsx` | Add Rerank panel for top_n evidence rendering. |
| `src/frontend/src/App.test.tsx` | Verify rerank order and fallback indicator behavior. |

**How to test:** Run frontend tests and ensure reranked ordering displays before subanswers/final answer.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 17: Subanswer stage view - per-subquestion answer with citations

**Single goal:** Render per-subquestion answers as they become available, including citation markers.

**Details:**
- Show each sub-question with its generated subanswer and citation markers (`[1]`, `[2]`, ...).
- Highlight explicit fallback `nothing relevant found` when returned.
- Link visible citation markers to reranked evidence rows in the Rerank panel.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/utils/api.ts` | Add subanswer citation/fallback fields to stage payload types. |
| `src/frontend/src/App.tsx` | Add Subanswer panel and citation-to-evidence linkage. |
| `src/frontend/src/App.test.tsx` | Verify subanswer rendering, citation markers, and fallback display. |

**How to test:** Run frontend tests and confirm subanswers/citations render per sub-question during answering stage.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 18: Final synthesis view - final answer with supporting subanswer summary

**Single goal:** Render the final answer stage as a distinct panel that summarizes supporting subanswers and citations.

**Details:**
- Show final answer only when synthesis stage completes.
- Display compact summary of contributing subanswers and citation coverage.
- Preserve previous successful final answer while a new run is in progress.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/frontend/src/App.tsx` | Add Final panel with synthesis completion behavior. |
| `src/frontend/src/App.test.tsx` | Verify final panel only updates on synthesis completion. |

**How to test:** Run frontend tests and manual run to confirm final panel updates only at terminal synthesis stage.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 19: Parity evals - deep-agent path vs graph path

**Single goal:** Prove graph workflow preserves baseline behavior compared to deep-agent path during migration.

**Details:**
- Build fixed-question parity suite across both paths.
- Compare main output shape, sub_qa completeness, and fallback behavior.
- Keep this section focused on parity only; quality/cost deltas are handled in Sections 20-21.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies required initially.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tests/services/test_agent_service.py` | Add graph vs deep-agent parity regression tests. |
| `README.md` | Document parity test scope and acceptance thresholds. |

**How to test:** Run parity suite and verify graph path meets agreed parity thresholds before cleanup sections begin.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 20: Retrieval quality evals - search-only vs search+rerank

**Single goal:** Quantify retrieval-quality gains from reranking without mixing in cost metrics.

**Details:**
- Compare `search-only` vs `search+rerank` on benchmark queries.
- Track hit-quality metrics and citation-grounding consistency.
- Include hard queries where relevant evidence is outside naive top-k.
- Keep this section focused on quality metrics only.
- Include eval slices for the actual library stack (`MultiQueryRetriever` + `flashrank`) versus non-expanded/non-reranked baselines.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies required initially.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tests/services/test_agent_service.py` | Add retrieval quality regression tests for rerank impact. |
| `src/backend/tests/services/test_reranker_service.py` | Add rerank quality/fallback tests used by eval cases. |
| `README.md` | Document retrieval-quality eval methodology. |

**How to test:** Run quality eval suite and verify rerank path improves retrieval/citation metrics on selected hard queries.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 21: Efficiency evals - context size and token budget impact

**Single goal:** Quantify efficiency impact of reranked top_n context vs naive large-context baselines.

**Details:**
- Compare token usage for reranked top_n vs larger unfiltered context windows.
- Track answer quality floor while reducing token cost.
- Record target operating ranges for `k_fetch` and `top_n`.
- Keep this section focused on cost/efficiency metrics only.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies required initially.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/tests/services/test_agent_service.py` | Add efficiency-oriented regression checks and fixtures. |
| `README.md` | Document token/cost eval method and recommended defaults. |

**How to test:** Run efficiency suite and verify reranked context achieves lower token usage without unacceptable quality loss.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 22: Remove deep-agent runtime code - post-cutover cleanup

**Single goal:** Delete unused deep-agent runtime orchestration code after graph path is validated.

**Details:**
- Remove coordinator/deep-agent invocation from active runtime execution.
- Delete deep-agent-only helpers, callbacks, and prompt contracts that are no longer referenced.
- Keep only code required for historical docs/tests if explicitly needed; otherwise remove.
- Ensure imports and schemas no longer reference deep-agent-specific artifacts.
- Do not remove `langfuse` tracing integration; retain/cleanly re-home it as graph runtime observability.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/agents/coordinator.py` | Remove or archive deep-agent runtime path if fully unused. |
| `src/backend/services/agent_service.py` | Remove deep-agent branches and callback plumbing. |
| `src/backend/utils/agent_callbacks.py` | Remove deep-agent callback capture code if no longer used. |
| `src/backend/tests/agents/test_coordinator_agent.py` | Remove/replace tests tied only to removed runtime code. |

**How to test:** Run full backend tests and static import checks to confirm no dead deep-agent references remain.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 23: Remove migration scaffolding - flags, dual paths, and temporary parity code

**Single goal:** Remove temporary migration switches and dual-path code once graph runner is the only production path.

**Details:**
- Remove feature flags used only for migration rollback.
- Remove dual-path branching and temporary adapters used for parity comparisons.
- Remove migration-only fixtures and temporary eval wiring that is no longer needed.
- Keep permanent quality tests, but drop one-off migration parity harnesses.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): remove migration-only env vars from docs/config.

**Files and purpose**

| File | Purpose |
|------|--------|
| `src/backend/services/agent_service.py` | Delete dual-path/flagged branches. |
| `src/backend/tests/services/test_agent_service.py` | Remove migration-only parity fixtures while keeping permanent regressions. |
| `README.md` | Remove migration-only flags and rollout instructions. |

**How to test:** Run backend tests with migration flags removed and verify runtime behavior is unchanged.
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.

## Section 24: Final architecture docs reconciliation - canonical state-graph docs only

**Single goal:** Ensure repository docs and flow diagrams reflect only the final state-graph architecture.

**Details:**
- Update the architecture content in `README.md` to remove deep-agent runtime references.
- Update `run-flow.html` to show the canonical lane: `decompose -> expand -> search -> rerank -> answer -> synthesize`.
- Ensure README examples and terminology match actual code paths and endpoint behavior.
- Confirm no contradictory legacy flow descriptions remain across docs.
- Document concrete library usage in architecture docs: `langchain` `MultiQueryRetriever` for expansion and `flashrank` for reranking.
- Add a "How the flow works" explainer covering each stage:
  - `decompose`: split main question into atomic sub-questions.
  - `expand`: generate related queries per sub-question.
  - `search`: retrieve candidate chunks with vector similarity.
  - `rerank`: reorder retrieved chunks by query-specific relevance.
  - `answer`: produce subanswer with citations from reranked evidence.
  - `synthesize`: build final answer from subanswers.
- Add a retrieval fundamentals explainer:
  - embedding vectors and nearest-neighbor retrieval basics.
  - cosine similarity intuition (`-1..1`, direction similarity, higher is closer).
  - why over-fetch (`k_fetch`) then rerank (`top_n`) improves precision.
  - merge/dedupe behavior across expanded queries and citation index stability.
- Add a reranking explainer:
  - difference between initial vector retrieval score and reranker score.
  - why reranking can surface relevant chunks that were not in naive top-k.
  - fallback behavior when reranker is unavailable.

**Tech stack and dependencies**
- Libraries/packages (pip, npm, uv, etc.): no new dependencies.
- Tooling (uv, poetry, Docker): no tooling changes.

**Files and purpose**

| File | Purpose |
|------|--------|
| `README.md` | Canonical architecture and usage docs for state-graph runtime. |
| `src/frontend/public/run-flow.html` | Final flow visualization aligned with implementation. |

**How to test:** Manually validate docs against real runtime traces; confirm every stage in UI/run-status has a matching explanation, and verify retrieval/rerank examples are technically consistent with implementation (`k_fetch`, `top_n`, cosine similarity, dedupe/citation behavior).
**Documentation update:** After completing this section, update `README.md` and `src/frontend/public/run-flow.html`.
