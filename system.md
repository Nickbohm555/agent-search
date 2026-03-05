# Agent-Search System Flow

How the implementation plan sections connect at runtime. Section numbers match `IMPLEMENTATION_PLAN.md`.

---

## High-level flow

```mermaid
flowchart TB
    Q([question])
    Q --> S1

    S1["1. Initial search"]
    S2["2. Decomposition"]
    S9["9. Parallel sub-question pipeline"]
    S10["10. Initial answer"]
    S11["11. Extraction"]
    S12["12. Refinement decision"]
    S13["13. Refinement decomposition"]
    S14["14. Refinement answer path"]

    S1 --> S2
    S1 --> S10
    S1 --> S11
    S2 --> S9
    S9 --> S10
    S11 --> S13
    S10 --> S12
    S12 --> need{"Refinement needed?"}
    need -->|No| FINAL([final answer])
    need -->|Yes| S13
    S13 --> S14
    S14 --> FINAL
```

- **Section 9** runs the per-subquestion pipeline (steps 3–8) for all sub-questions in parallel.
- **Section 13** uses: initial answer (10), SubQuestionAnswer list (9), and ExtractionResult (11). **Section 14** reuses the same pipeline (3–8) for refined sub-questions.

---

## Per-subquestion pipeline (Sections 3–8)

Same sequence runs for each **initial** sub-question (Section 9) and each **refined** sub-question (Section 14).

```mermaid
flowchart LR
    A["3. Expand"] --> B["4. Search"] --> C["5. Validate"] --> D["6. Rerank"] --> E["7. Subanswer"] --> F["8. Verify"]
    F --> out["SubQuestionAnswer"]
```

---

## Data flow summary

| Output | Produced by | Consumed by |
|--------|-------------|-------------|
| Initial search context | 1 | 2, 10, 11 |
| Sub-questions | 2 | 9 |
| SubQuestionAnswer list | 9 (3–8) | 10, 12, 13 |
| ExtractionResult | 11 | 13 |
| Initial answer | 10 | 12, 13 |
| refinement_needed | 12 | 13 (if true) |
| Refined sub-questions | 13 | 14 |
| Final answer | 10 (no refinement) or 14 (refinement) | response |

---

## Parallelism

- **Section 9:** All sub-questions run the pipeline (3→8) in parallel.
- **Section 11:** Extraction can run in parallel with the sub-question pipeline (2→9); both only need Section 1.
- **Section 14:** Refined sub-questions again run the same pipeline in parallel.
