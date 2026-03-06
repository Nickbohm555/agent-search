## Section 1: Coordinator flow tracking via write_todos and virtual file system

**Single goal:** The coordinator agent uses the deep-agents (LangGraph) `write_todos` planning tool and the **deep-agents virtual file system** to keep track of the pipeline flow so it does not lose context across steps.

### Implemented
- Updated `src/backend/agents/coordinator.py` to explicitly configure deep-agents backend as `StateBackend` (virtual filesystem backend) when creating the coordinator agent.
- Strengthened coordinator system prompt to require:
  - `write_todos` at run start and throughout stage transitions.
  - `read_file`/`write_file` usage on `/runtime/coordinator_flow.md` for persisted flow tracking across steps.
  - Stage-aligned planning for the full initial + refinement pipeline.
- Added coordinator creation logging to include backend and flow tracking file path for visibility.
- Added/updated tests in `src/backend/tests/agents/test_coordinator_agent.py`:
  - Verifies coordinator prompt contains mandatory `write_todos` + virtual filesystem instructions.
  - Verifies backend passed to deep-agents is `StateBackend`.
  - Verifies backend override wiring works.

### Validation and logs
- Fresh restart (full rebuild):
  - `docker compose down -v --rmi all`
  - `docker compose build`
  - `docker compose up -d`
- Backend unit tests:
  - `docker compose exec backend sh -lc 'uv run pytest tests/agents/test_coordinator_agent.py tests/services/test_agent_service.py'`
  - Result: `5 passed`
- API smoke selection command:
  - `docker compose exec backend sh -lc 'uv run pytest tests/api -m smoke'`
  - Result: `2 deselected` (no smoke-selected tests)
- Integration run:
  - `POST /api/agents/run` with `{"query":"What is the Strait of Hormuz?"}`
  - Result: `HTTP 200`
  - Response included `main_question`, `sub_qa`, and `output`.
- Backend logs confirmed required runtime behavior:
  - `Tool called: name=write_todos ...`
  - `Tool called: name=write_file input={'file_path': '/runtime/coordinator_flow.md', ...}`
  - `Tool response ... Command(update={'files': {'/runtime/coordinator_flow.md': ...}})`
  - Additional flow updates and staged todo status transitions were present.
- Container log sweep performed (`backend`, `frontend`, `db`) and `docker compose ps` checked all services up/healthy.

### Noted runtime detail
- `GET /api/health` currently returns `404 Not Found` in this codebase state.
