# Advanced Evaluation Upgrade Plan

## Purpose
This document defines the deferred path from the current low-cost v1 evaluator set to deeper DeepResearchBench-style parity without changing existing benchmark run APIs.

## Current v1 scope (implemented)
- Single-judge quality score with deterministic prompt and JSON output.
- Deterministic citation presence/support checks.
- DRB-inspired raw export shape (`id`, `prompt`, `article`) for compatibility workflows.

## Deferred advanced scope (not implemented yet)
- RACE-equivalent evaluator for richer answer quality dimensions.
- FACT-equivalent evaluator for claim-level verification and attribution robustness.
- Pairwise evaluation mode for comparative ranking against baseline outputs.
- Multi-judge aggregation (panel scoring) with configurable disagreement policy.
- Calibrated evaluator confidence and variance metrics.

## Compatibility contract to preserve
- Keep benchmark run API routes and response schemas stable.
- Keep `BenchmarkResult` storage as the canonical source of evaluated answer payloads.
- Keep DRB raw export shape stable for external parity tooling inputs.

## Scaffolding entrypoint
- `src/backend/benchmarks/drb/parity_runner.py`
  - Provides export-shape smoke parity helper.
  - Defines advanced evaluator interface stubs and registry hooks.
  - Keeps placeholders isolated so future evaluator rollout does not require run API changes.

## Deferred implementation checklist
- [ ] Implement `RACE`-style evaluator adapter behind `DRBAdvancedEvaluator`.
- [ ] Implement `FACT`-style evaluator adapter behind `DRBAdvancedEvaluator`.
- [ ] Add pairwise judge runner using existing run/result storage.
- [ ] Add multi-judge runner + aggregation policy (`mean`, `median`, or configurable).
- [ ] Persist advanced evaluator outputs in additive tables/modeled extension fields.
- [ ] Extend compare/reporting API payloads with advanced metrics behind feature flags.
- [ ] Add deterministic fixture-based parity tests against frozen DRB-like samples.

## Rollout notes
- Add new evaluators as additive services; do not change required fields in existing APIs.
- Gate advanced execution behind explicit runtime settings.
- Keep v1 smoke parity (`test_drb_export_parity_smoke.py`) as the minimum compatibility guardrail.
