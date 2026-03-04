0a. Study `specs/*` to learn the application specifications.
0b. Study @IMPLEMENTATION_PLAN.md.
0c. For reference, the application source code is in `src/*`.
0d. Start fresh for every build; @AGENTS.md has the command (remove services, volumes, and images; then build and start).

997. Iteration scope: aim to complete ONE highest-priority implementation-plan item per run, then stop for the next loop.
998. Special case - Blocked external dependency (missing env/API key/service access): if required tests cannot run or pass only because external configuration is missing, do not claim full success. Complete what is possible, then record a blocker.
999. Tests derived from acceptance criteria should be treated as part of implementation scope. TDD is encouraged (tests first or alongside implementation).

1. Implement functionality per the specifications.
2. Follow @IMPLEMENTATION_PLAN.md and choose the single most important item to address. Include relevant tests in the task scope. Look at blocked items and check if any are unblocked now.
3. Before making changes, search the codebase so existing functionality is reused when possible.
4. After implementing functionality, run the required tests from the task definition. Prefer all required tests passing unless blocked by rule 998.
5. Update @IMPLEMENTATION_PLAN.md with findings and completion state.
6. For blocked external dependency (rule 998): update @IMPLEMENTATION_PLAN.md with a `BLOCKED` item including:
- what is missing (env var / API key / account / access)
- exact failed command/test + error excerpt
- **Nicholas, the human needs to**: explicit instructions (e.g. "provide OPENAI_API_KEY", "create Langfuse account + set LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY", "grant access to <service>")
Then write `.loop-commit-msg` and end this run.
7. If you made a build tradeoff: record it in @IMPLEMENTATION_PLAN.md with:
- what you chose + why (1-2 lines)
- alternatives considered
- references for the human: PR link/number (if applicable) and exact code location(s) (file paths, key symbols)
- a clearly marked section `HUMAN-ONLY NOTES` (assume only Nicholas reads it) that references the PR (or commit/message) + code locations
8. At the end of every run: write one line to `.loop-commit-msg` in the repo root so the loop can use it for the commit (e.g. `Worked on: <brief>. Blocked: <if any>.`).
9. Mermaid doc (ONLY if it adds value beyond @IMPLEMENTATION_PLAN.md): add at most one `.mermaid` file under `docs/` in a topic subfolder that matches the work, e.g.:
- `docs/backend/mcp/<descriptive-name>.mermaid` for MCP-related work
- `docs/frontend/ui/<descriptive-name>.mermaid` for UI flows
- `docs/loop/<descriptive-name>.mermaid` only for loop-process diagrams
Name it with a short, specific slug (avoid generic `diagram.mermaid`). Only add it when it clarifies a flow/interaction/tradeoff better than text; otherwise skip.

NOTE: Keep @AGENTS.md operational only (how to build/test/run). Keep status/progress in @IMPLEMENTATION_PLAN.md.
NOTE: Prefer complete functionality over placeholders/stubs unless explicitly needed.
