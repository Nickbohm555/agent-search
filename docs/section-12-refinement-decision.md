# Section 12 Architecture: Refinement Decision

## Purpose
Decide whether the initial synthesized answer is good enough to return, or whether the pipeline should enter refinement. Section 12 consumes the initial answer from Section 11 and verified per-subquestion outcomes from Section 10, then emits a binary gate (`refinement_needed`) plus a machine-readable reason.

## Components
- Decision policy service:
`src/backend/services/refinement_decision_service.py`
- Runtime orchestration and branch point:
`src/backend/services/agent_service.py`
- Decision input/output schema dependency (`SubQuestionAnswer`):
`src/backend/schemas/agent.py`
- Section 12 tests:
`src/backend/tests/services/test_refinement_decision_service.py`,
`src/backend/tests/services/test_agent_service.py`

## Flow Diagram
```text
+---------------------------------------------------------------------------------------------------+
| Section 12 Inputs (inside run_runtime_agent)                                                      |
|                                                                                                   |
|  A) question: payload.query                                                                       |
|  B) initial_answer: output from generate_initial_answer (Section 11)                             |
|  C) sub_qa: list[SubQuestionAnswer] from Section 10                                               |
|     +-----------------------------------------------------------------------------------------+   |
|     | sub_question, sub_answer, answerable, verification_reason, expanded_query, ...         |   |
|     +-----------------------------------------------------------------------------------------+   |
+---------------------------------------------------------+-----------------------------------------+
                                                          |
                                                          v
+---------------------------------------------------------------------------------------------------+
| should_refine(question, initial_answer, sub_qa)                                                   |
|  +---------------------------------------------------------------------------------------------+  |
|  | Rule checks (ordered):                                                                       |  |
|  | 1) initial_answer empty? -> refinement_needed=True, reason=initial_answer_empty             |  |
|  | 2) initial_answer contains insufficient-evidence pattern? -> True                            |  |
|  | 3) sub_qa empty? -> True, reason=no_subquestion_answers                                      |  |
|  | 4) answerable_count == 0? -> True, reason=no_answerable_subanswers                          |  |
|  | 5) answerable_ratio < REFINEMENT_MIN_ANSWERABLE_RATIO? -> True                              |  |
|  | 6) else -> False, reason=sufficient_answerable_ratio:<ratio>                                 |  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------+-----------------------------------------+
                                                          |
                                                          v
+---------------------------------------------------------------------------------------------------+
| Section 12 Output: RefinementDecision                                                             |
|  +---------------------------------------------------------------+                                |
|  | refinement_needed: bool                                       |                                |
|  | reason: str                                                   |                                |
|  +---------------------------------------------------------------+                                |
+---------------------------------------------------------+-----------------------------------------+
                                                          |
                                         +----------------+----------------+
                                         |                                 |
                                         v                                 v
                  +------------------------------------------------+   +---------------------------------------------+
                  | refinement_needed = False                      |   | refinement_needed = True                    |
                  | return current initial answer as final output  |   | handoff to Section 13 refinement           |
                  +------------------------------------------------+   +---------------------------------------------+
```

## Data Flow
Inputs:
- `question` (`RuntimeAgentRunRequest.query`) is passed to `should_refine(...)` for future policy extensions.
- `initial_answer` is the synthesized string from Section 11.
- `sub_qa` is the processed/verified list from Section 10, especially `answerable` flags used for ratio computation.

Transformations:
1. `run_runtime_agent(...)` generates `output` via `generate_initial_answer(...)` (Section 11).
2. Immediately after generation, `run_runtime_agent(...)` calls:
`should_refine(question=payload.query, initial_answer=output, sub_qa=sub_qa)`.
3. `should_refine(...)` normalizes and evaluates `initial_answer` and `sub_qa` using ordered deterministic rules.
4. The function computes:
- `answerable_count = sum(item.answerable for item in sub_qa)`
- `answerable_ratio = answerable_count / len(sub_qa)`
- threshold comparison against `REFINEMENT_MIN_ANSWERABLE_RATIO` (default `0.5`).
5. It returns `RefinementDecision(refinement_needed: bool, reason: str)`.
6. `run_runtime_agent(...)` logs the decision and branches:
- `False`: keep current `output`.
- `True`: trigger Section 13 decomposition and downstream refinement path.

Outputs:
- Direct output of Section 12 is a `RefinementDecision` object.
- Indirect runtime effect is control-flow selection of normal return vs refinement stages.

Data movement and boundaries:
- Section 12 uses only in-memory data already in the backend process.
- No database writes happen in this stage.
- No external network calls happen in the decision logic (pure rule evaluation).
- Observability boundary is logs: decision reason and counts are emitted for debugging and audits.

## Key Interfaces / APIs
- Decision API:
`should_refine(*, question: str, initial_answer: str, sub_qa: list[SubQuestionAnswer]) -> RefinementDecision`
- Decision model:
`RefinementDecision(refinement_needed: bool, reason: str)` (`dataclass`)
- Runtime orchestration call site:
`run_runtime_agent(payload: RuntimeAgentRunRequest, db: Session) -> RuntimeAgentRunResponse`
- Config input:
`REFINEMENT_MIN_ANSWERABLE_RATIO` (environment variable, parsed once at module load)

## How It Fits Adjacent Sections
- Upstream:
- Section 10 provides verified `sub_qa` items (`answerable` + `verification_reason`) that Section 12 uses as quality signals.
- Section 11 provides `initial_answer`, the main artifact being judged.

- Downstream:
- If refinement is needed, Section 13 (`refine_subquestions(...)`) receives `question`, `initial_answer`, and `sub_qa` to create refined subquestions.
- If refinement is not needed, the existing initial answer exits as final response without running refinement stages.

## Tradeoffs
1. Deterministic rule-based gate vs LLM-based refinement classifier
- Chosen: rule-based decision in `should_refine(...)`.
- Pros: predictable behavior, easy to test, zero extra model cost/latency, simple failure modes.
- Cons: lower nuance; may miss subtle low-quality answers that do not match patterns.
- Alternative considered: ask an LLM to score answer sufficiency.
- Why rejected: non-determinism and extra runtime cost for a control gate.

2. Ordered hard checks vs weighted multi-factor score
- Chosen: ordered checks with early exits (empty answer, insufficiency markers, no sub_qa, ratio threshold).
- Pros: transparent reasons, stable semantics, straightforward debugging.
- Cons: coarse granularity; cannot express medium-confidence “maybe refine” states.
- Alternative considered: weighted confidence score across many signals.
- Why rejected: higher complexity and harder threshold tuning at this stage.

3. Answerable-ratio threshold as env config vs hardcoded constant
- Chosen: env-configurable `REFINEMENT_MIN_ANSWERABLE_RATIO` (default `0.5`).
- Pros: fast tuning per environment/workload without code changes.
- Cons: config drift risk across environments; module-load parsing means runtime env changes require restart.
- Alternative considered: fixed threshold in code.
- Why rejected: less operational flexibility.

4. String-pattern insufficiency detection vs structured evidence scoring
- Chosen: substring matching on common insufficiency phrases in `initial_answer`.
- Pros: cheap and effective for explicit low-evidence outputs.
- Cons: brittle to wording variation and model phrasing.
- Alternative considered: structured evidence coverage tracking from synthesis stage.
- Why rejected: requires additional schema/contracts between Sections 11 and 12.

5. Stateless decision (no persistence) vs persisted decision audit records
- Chosen: evaluate and branch in-memory, rely on logs for traceability.
- Pros: minimal implementation overhead and low latency.
- Cons: limited queryability for post-run analytics unless logs are centralized.
- Alternative considered: persist decision records in DB.
- Why rejected: additional schema/migration complexity not required for current runtime contract.
