---
status: in_progress
phase: "05-prompt-customization-and-guidance"
source:
  - 05-01-SUMMARY.md
  - 05-02-SUMMARY.md
  - 05-03-SUMMARY.md
  - 05-04-SUMMARY.md
  - 05-05-SUMMARY.md
started: "2026-03-13"
updated: "2026-03-14"
---

## Current Test

Test 4 pending. Tests 1-3 passed on 2026-03-14 and confirm alias compatibility, safe prompt key handling, default-behavior preservation when overrides are omitted, and deterministic prompt-influenced output changes.

## Information Needed from the Summary

- what_changed:
  - Request contracts now accept both `custom_prompts` and `custom-prompts`, normalize to one internal shape, and pass supported `subanswer`/`synthesis` overrides through runtime config.
  - Generation services and runtime nodes now accept optional prompt templates; default prompts still apply when overrides are absent.
  - Public API merge precedence is deterministic: defaults, then config-level custom prompts, then per-run overrides; sync and async behavior should match.
  - Documentation was aligned across canonical docs and SDK/root READMEs with explicit safety boundaries.
- files_changed:
  - `src/backend/schemas/agent.py`
  - `src/backend/routers/agent.py`
  - `src/backend/agent_search/config.py`
  - `sdk/core/src/agent_search/config.py`
  - `src/backend/services/subanswer_service.py`
  - `src/backend/services/initial_answer_service.py`
  - `src/backend/agent_search/runtime/nodes/answer.py`
  - `src/backend/agent_search/runtime/nodes/synthesize.py`
  - `src/backend/services/agent_service.py`
  - `src/backend/agent_search/public_api.py`
  - `sdk/core/src/agent_search/public_api.py`
  - `docs/prompt-customization.md`
  - `sdk/core/README.md`
  - `sdk/python/README.md`
  - `README.md`
- code_areas:
  - API request validation and alias normalization.
  - Runtime config parsing and prompt key whitelisting.
  - Subanswer/synthesis generation service prompt selection.
  - Runtime node prompt propagation and citation fallback enforcement.
  - SDK/backend public API precedence and mutable-map isolation.
  - User-facing prompt customization guidance.
- testing_notes:
  - Unknown prompt keys should be ignored safely, not crash requests.
  - Prompt overrides should influence generation behavior, but must not bypass citation/fallback guardrails.
  - Documentation tests should validate discoverability and consistency of supported keys and safety limits.

## Tests

1. **Alias Compatibility and Safe Prompt Key Handling**
   - Given a run request that includes `custom-prompts` with `subanswer`, `synthesis`, and an unsupported key.
   - When the request is submitted through the standard run endpoint.
   - Then the run is accepted, supported overrides are applied, unsupported keys are ignored, and no schema/validation error is returned.
   - result: Pass on 2026-03-14. `docker compose exec backend uv run pytest tests/api/test_agent_run.py::test_runtime_agent_run_request_accepts_custom_prompts_alias_and_ignores_unknown_keys tests/api/test_agent_run.py::test_post_run_forwards_custom_prompts_alias_and_ignores_unknown_keys tests/sdk/test_runtime_config.py::test_runtime_config_parses_custom_prompts_with_alias_and_ignores_unknown_keys` passed; the request model accepted `custom-prompts`, filtered the unsupported key, the standard run endpoint forwarded only `subanswer` and `synthesis`, and runtime config alias parsing matched the same behavior.

2. **Default Behavior Preserved When Overrides Are Omitted**
   - Given two equivalent runs with no prompt override values set.
   - When both runs execute through the same backend flow.
   - Then output behavior matches baseline/default prompt behavior and no custom prompt side effects appear.
   - result: Pass on 2026-03-15. `docker compose exec backend uv run pytest tests/sdk/test_runtime_config.py::test_runtime_config_preserves_legacy_defaults_when_custom_prompts_omitted tests/services/test_subanswer_service.py::test_generate_subanswer_unset_prompt_matches_explicit_default_template tests/services/test_initial_answer_service.py::test_generate_initial_answer_unset_prompt_matches_explicit_default_template` passed; omitted prompt overrides left `RuntimeConfig.custom_prompts` unset and both generation services produced the same outputs and prompt bodies as the explicit built-in default templates.

3. **Prompt Override Influences Subanswer/Synthesis Output**
   - Given a run with explicit `subanswer` and `synthesis` override text designed to alter deterministic wording.
   - When the run completes.
   - Then resulting intermediate/final generated text reflects override influence compared with a default-prompt control run.
   - result: Pass on 2026-03-14. `docker compose exec backend uv run pytest tests/services/test_agent_service.py::test_run_sequential_graph_runner_prompt_overrides_influence_orchestrated_outputs tests/services/test_subanswer_service.py::test_generate_subanswer_uses_custom_prompt_template tests/services/test_initial_answer_service.py::test_generate_initial_answer_uses_custom_prompt_template` passed; the orchestrated graph runner changed the intermediate subanswer from `Default subanswer [1].` to `Concise subanswer [1].` and the final output from `Default synthesis: Default subanswer [1].` to `Executive synthesis: Concise subanswer [1].`, while the service-level tests confirmed custom prompt templates directly alter the rendered subanswer and synthesis prompt bodies.

4. **Guardrails Still Enforced Under Custom Prompts**
   - Given a custom prompt that omits citation-oriented instructions.
   - When generation completes in a case that requires citation checks.
   - Then runtime citation/fallback behavior still triggers guarded output rather than allowing uncited unsupported content.

5. **Deterministic Precedence in Public API (Sync + Async)**
   - Given reusable config-level `custom_prompts` defaults and per-run runtime overrides for the same keys.
   - When runs are executed via both sync and async public API entrypoints.
   - Then per-run values win over reusable defaults in both paths, with identical effective prompt resolution.

6. **Documentation UAT for Prompt Customization Discoverability**
   - Given a consumer following only published docs.
   - When they read `README.md`, SDK README(s), and `docs/prompt-customization.md`.
   - Then they can identify supported keys (`subanswer`, `synthesis`), accepted naming forms (`custom-prompts` JSON and `custom_prompts` Python/internal), precedence order, and the explicit statement that guardrails are not bypassed.

## Summary

Tests 1-3 passed on 2026-03-14. Remaining coverage is still pending for guardrails, precedence, and documentation.

## Gaps

- Tests 4-6 not yet executed.
