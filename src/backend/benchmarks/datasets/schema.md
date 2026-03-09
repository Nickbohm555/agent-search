# Internal Benchmark Dataset Schema (DeepResearchBench-aligned)

Dataset format: JSON Lines (`.jsonl`), one question object per line.

## Required fields

Each JSON object must include exactly these fields:

- `question_id` (`string`, non-empty): globally unique question identifier.
- `question` (`string`, non-empty): benchmark prompt shown to the system under test.
- `domain` (`string`, non-empty): taxonomy label (for example `finance`, `public_health`).
- `difficulty` (`string`, non-empty): calibrated difficulty bucket (`easy`, `medium`, `hard`).
- `expected_answer_points` (`string[]`, at least 1 item): key facts that a correct answer should cover.
- `required_sources` (`string[]`, at least 1 item): required citation/source classes for answer grounding.
- `disallowed_behaviors` (`string[]`, at least 1 item): behaviors that should be marked incorrect.

## Strictness rules

- Extra fields are not allowed.
- Empty strings are not allowed.
- Empty arrays are not allowed for list fields.
- Invalid JSON rows are rejected.

## v1 target

- Dataset id: `internal_v1`
- Row count target: `120` public questions
