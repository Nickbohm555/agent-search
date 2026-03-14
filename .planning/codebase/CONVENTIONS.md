# Coding Conventions

**Analysis Date:** 2026-03-12

## Naming Patterns

**Files:**
- Python modules use `snake_case.py` across backend and SDK files, such as `src/backend/services/agent_service.py` and `sdk/core/src/services/agent_service.py`.
- React UI files use PascalCase for top-level components and co-located tests, such as `src/frontend/src/App.tsx` and `src/frontend/src/App.test.tsx`.
- Frontend utility files use lowercase names, such as `src/frontend/src/utils/api.ts` and `src/frontend/src/utils/constants.ts`.
- Backend tests use `test_*.py` naming and domain folders, such as `src/backend/tests/services/test_agent_service.py`.

**Functions:**
- Python functions use `snake_case` with explicit return annotations in most modules, such as `build_runtime_timeout_config_from_env` in `src/backend/services/agent_service.py`.
- React helpers and event handlers use `camelCase`, such as `formatLatency`, `handleRun`, and `handleLoadWiki` in `src/frontend/src/App.tsx`.

**Variables:**
- Python module constants are uppercase with underscores, often env-driven, such as `_RUNTIME_AGENT_MODEL` and `_SEARCH_NODE_MERGED_CAP` in `src/backend/services/agent_service.py`.
- React state variables use paired `value` and `setValue` naming, such as `runState` and `setRunState` in `src/frontend/src/App.tsx`.

**Types:**
- Backend domain models are Pydantic/dataclass types with PascalCase names, such as `RuntimeAgentRunResponse` in `src/backend/schemas/agent.py`.
- Frontend API contracts use `interface` and string unions with PascalCase names, such as `RuntimeAgentRunAsyncStatusResponse` in `src/frontend/src/utils/api.ts`.

## Code Style

**Formatting:**
- Not detected: no repository-level formatter config file for Prettier, Black, or Ruff was found.
- Style appears to rely on language defaults and contributor discipline in `src/backend` and `src/frontend`.

**Linting:**
- Not detected for app code: no repo-level `eslint`/`ruff`/`flake8` config was found for `src/backend` or `src/frontend`.
- Python SDK package includes static-analysis settings in `sdk/python/pyproject.toml` (`mypy` settings, `flake8` dev dependency), but this is scoped to generated SDK code.

## Import Organization

**Order:**
1. Standard library imports first (for example `json`, `logging`, `os` in `src/backend/services/agent_service.py`).
2. Third-party framework imports second (for example `langchain_*`, `sqlalchemy`, `react`).
3. Project-local imports last (for example `from services...` in backend modules and `from "./utils/api"` in frontend modules).

**Path Aliases:**
- Frontend path aliases are not used; relative imports are standard in files such as `src/frontend/src/App.tsx`.
- Backend uses top-level package-style local imports (for example `from services...`, `from schemas...`) in files under `src/backend`.

## Error Handling

**Patterns:**
- Broad exception capture (`except Exception`) is used in runtime-critical backend paths, including `src/backend/services/agent_service.py`, `src/backend/agent_search/runtime/jobs.py`, and `src/backend/services/internal_data_jobs.py`.
- Fallback-oriented behavior is common: failures degrade to default messages or reduced outputs (for example query expansion fallback in `src/backend/services/query_expansion_service.py`).
- Frontend API layer normalizes errors into structured union results via `ApiResult<T>` in `src/frontend/src/utils/api.ts`.

## Logging

**Framework:** Python `logging` in backend and `console` in frontend.

**Patterns:**
- Backend sets root logger to INFO and enables selected namespaces in `src/backend/main.py`.
- Runtime services emit structured context logs with IDs and stage metadata in `src/backend/services/agent_service.py` and `src/backend/agent_search/runtime/jobs.py`.
- Frontend emits operational `console.info` and `console.error` in flow handlers in `src/frontend/src/App.tsx`.

## Comments

**When to Comment:**
- Comments are used mostly for intent and compatibility notes, such as warning suppression and tracing compatibility in `src/backend/main.py` and `src/backend/utils/langfuse_tracing.py`.
- Generated SDK contains TODO comments marking technical debt migration points in `sdk/python/openapi_client/models/*.py`.

**JSDoc/TSDoc:**
- Minimal usage in app code; lightweight inline comments are preferred (for example timeout rationale in `src/frontend/src/utils/api.ts`).

## Function Design

**Size:** Large orchestration functions and helper sets are concentrated in a few modules, especially `src/backend/services/agent_service.py` and `src/frontend/src/App.tsx`.

**Parameters:** Backend public APIs frequently accept generic integration objects (`Any`) for model/vector-store abstractions in `src/backend/agent_search/public_api.py` and `src/backend/services/agent_service.py`.

**Return Values:** Strongly typed response models are common at boundaries (Pydantic models in backend schemas and TypeScript interfaces in frontend API utilities).

## Module Design

**Exports:** Backend modules expose many functions directly without barrel indirection; frontend utility exports are centralized in `src/frontend/src/utils/api.ts`.

**Barrel Files:** Minimal use; `__init__.py` files aggregate some backend and SDK exports, such as `src/backend/services/__init__.py`.

## Complexity Hotspots

- `src/backend/services/agent_service.py`: primary orchestration hub with high branch density, timeout logic, stage mapping, and parallel execution paths.
- `src/backend/tests/services/test_agent_service.py`: very large test module, difficult to navigate and expensive to maintain as behavior evolves.
- `src/frontend/src/App.tsx`: UI, orchestration, polling, summarization, and rendering all in one component.
- `src/frontend/src/App.test.tsx`: extensive end-to-end-ish component scenario coverage in one file.
- `src/frontend/src/utils/api.ts`: many request/validation branches and contract guards in a single module.

## Duplication Patterns

- Major mirrored codebase duplication exists between backend runtime code and SDK core code:
  - `src/backend/services/agent_service.py` and `sdk/core/src/services/agent_service.py`
  - `src/backend/agent_search/public_api.py` and `sdk/core/src/agent_search/public_api.py`
  - `src/backend/utils/langfuse_tracing.py` and `sdk/core/src/utils/langfuse_tracing.py`
  - many additional mirrored modules under `src/backend` and `sdk/core/src`
- This duplicate-source pattern increases drift risk and doubles maintenance overhead unless synchronization is strictly enforced.
- API schema model duplication is also present in generated client artifacts under `sdk/python/openapi_client/models/`.

## Risky Areas

- In-memory async job registries (`_JOBS`, `_EXECUTOR`) in `src/backend/agent_search/runtime/jobs.py` and `src/backend/services/internal_data_jobs.py` are process-local and fragile under multi-process deployments.
- Broad exception swallowing with fallback behavior in `src/backend/services/query_expansion_service.py`, `src/backend/services/subanswer_service.py`, and `src/backend/services/initial_answer_service.py` can mask root causes.
- Polling loops in `src/frontend/src/App.tsx` use recursive `setTimeout` chains without a centralized cancellation abstraction.
- Open CORS policy in `src/backend/main.py` (`allow_origins=["*"]`) increases operational risk if deployed without tighter environment controls.

## Maintainability Observations

- Prefer extraction of orchestration seams from `src/backend/services/agent_service.py` into smaller stage modules to reduce cognitive load.
- Prefer extraction of focused React hooks/components from `src/frontend/src/App.tsx` to isolate polling and state transitions.
- Introduce a single source-of-truth generation/sync mechanism for mirrored backend and SDK-core modules rooted in `src/backend` and `sdk/core/src`.
- Add repository-level lint/format standards for app code (backend and frontend) to reduce style drift and review noise.

---

*Convention analysis: 2026-03-12*
