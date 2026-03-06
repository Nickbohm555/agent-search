# Section 12 Architecture: Refinement decision

## Purpose
Decide whether the initial synthesized answer is strong enough to return, or whether the system should enter the refinement path. This section acts as a quality gate between initial answer generation (Section 11) and refinement decomposition (Section 13).

## Components
- Decision service: `should_refine(...)` in `src/backend/services/refinement_decision_service.py`
- Decision model: `RefinementDecision` dataclass (`refinement_needed: bool`, `reason: str`)
- Orchestrator call site: `run_runtime_agent(...)` in `src/backend/services/agent_service.py`
- Input schema dependency: `SubQuestionAnswer` in `src/backend/schemas/agent.py`

## Data Flow
### Inputs
1. `question: str`
- Original user query (`RuntimeAgentRunRequest.query`).
- Currently reserved for future semantic coverage checks and not used directly in rule evaluation.

2. `initial_answer: str`
- Output of Section 11 (`generate_initial_answer(...)`).
- Treated as a single synthesized candidate answer to evaluate.

3. `sub_qa: list[SubQuestionAnswer]`
- Output of Section 10 pipeline.
- Key fields used by decision rules:
- `answerable: bool`
- `verification_reason: str` (indirectly through upstream flagging)
- `sub_answer: str` (already verified/synthesized upstream)

### Transformations
1. `run_runtime_agent(...)` generates initial output via Section 11 and calls:
`should_refine(question=payload.query, initial_answer=output, sub_qa=sub_qa)`.

2. `should_refine(...)` normalizes and evaluates data in a fixed sequence:
- Empty `initial_answer` -> refine (`reason=initial_answer_empty`)
- Insufficient-evidence phrase match in `initial_answer` (for example, "no relevant docs", "insufficient evidence") -> refine (`reason=initial_answer_reports_insufficient_evidence`)
- Empty `sub_qa` -> refine (`reason=no_subquestion_answers`)
- Zero `answerable=True` items -> refine (`reason=no_answerable_subanswers`)
- Low answerable ratio (`answerable_count / len(sub_qa) < REFINEMENT_MIN_ANSWERABLE_RATIO`) -> refine (`reason=low_answerable_ratio:<ratio>`)
- Otherwise -> no refinement (`reason=sufficient_answerable_ratio:<ratio>`)

3. `run_runtime_agent(...)` logs the decision and branches:
- `refinement_needed=False`: keep current `output` and continue to final response.
- `refinement_needed=True`: hand off to Section 13 (`refine_subquestions(...)`) and then Section 14 path.

### Outputs
- `RefinementDecision`
- `refinement_needed: bool` branch control signal
- `reason: str` traceable explanation for logs and debugging

### Data Movement Summary
1. Section 11 emits one synthesized answer string.
2. Section 10 emits per-subquestion verification outcomes.
3. Section 12 combines both evidence layers into a binary gate (`refinement_needed`) plus an audit-friendly reason.
4. The gate result controls whether data proceeds directly to final response or into Sections 13-14 refinement loop.

## Key Interfaces and APIs
- `should_refine(*, question: str, initial_answer: str, sub_qa: list[SubQuestionAnswer]) -> RefinementDecision`
- `RefinementDecision(refinement_needed: bool, reason: str)`

Environment control:
- `REFINEMENT_MIN_ANSWERABLE_RATIO` (default `0.5`)

## Fit With Adjacent Sections
- Upstream:
- Section 10 produces verified `sub_qa` quality signals.
- Section 11 produces initial synthesized answer text.

- Current section role:
- Section 12 is the policy gate that decides if current evidence quality is acceptable.

- Downstream:
- If refinement is required, Section 13 decomposes follow-up subquestions.
- If not required, runtime returns Section 11 answer as final output.

## Tradeoffs
### Chosen design
Use deterministic, rule-based refinement gating instead of an LLM classifier.

### Benefits
- Predictable behavior across local/dev/CI environments.
- Low latency and no additional model/API cost.
- Transparent reasons (`reason` codes) for observability and tuning.
- Easy to regression test with stable assertions.

### Costs
- Phrase matching can miss nuanced low-quality answers that avoid known patterns.
- `answerable` ratio is a coarse proxy; it does not measure completeness against the original question.
- One global ratio threshold may not fit all query complexity levels.

### Alternatives considered or rejected
1. LLM-based refinement judge.
- Pros: richer semantic quality assessment and better nuance.
- Cons: extra cost/latency, nondeterminism, more brittle tests.

2. Confidence score aggregation from retrieval/reranking metrics.
- Pros: potentially more quantitative signal than phrase checks.
- Cons: requires broader scoring contracts across multiple services.

3. Always refine when any subquestion is unanswerable.
- Pros: conservative; may improve recall for hard questions.
- Cons: over-triggers refinement, increasing latency and compute for otherwise sufficient answers.

## Verification Coverage
- `src/backend/tests/services/test_refinement_decision_service.py`
- Verifies refine=true when initial answer signals insufficient evidence.
- Verifies refine=false when answerable coverage is sufficient.

- `src/backend/tests/services/test_agent_service.py`
- `test_run_runtime_agent_flags_refinement_path_when_decision_true` verifies runtime branching and refinement handoff logging.
