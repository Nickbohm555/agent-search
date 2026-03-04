0a. Study `specs/*` to learn the application specifications.
0b. Study @IMPLEMENTATION_PLAN.md.
0c. For reference, the application source code is in `src/*`.

997. Iteration scope: aim to complete ONE highest-priority implementation-plan item per run, then stop for the next loop.
998. Special case - Blocked external dependency (missing env/API key/service access): if required tests cannot run or pass only because external configuration is missing, do not claim full success. Complete what is possible, then record a blocker.
999. Tests derived from acceptance criteria should be treated as part of implementation scope. TDD is encouraged (tests first or alongside implementation).

1. Implement functionality per the specifications.
2. Follow @IMPLEMENTATION_PLAN.md and choose the single most important item to address. Include relevant tests in the task scope. Look at blocked items and check if any are unblocked now.
3. Before making changes, search the codebase so existing functionality is reused when possible.
4. After implementing functionality, run the required tests from the task definition. Prefer all required tests passing unless blocked by rule 998.
5. Update @IMPLEMENTATION_PLAN.md with findings and completion state.
6. For blocked external dependency (rule 998): update @IMPLEMENTATION_PLAN.md with a `BLOCKED` item including missing variable/access, failed command/test, and next action; then write `.loop-commit-msg`, write the mermaid file, then end this run.
7. When checks pass (or blocked state is documented under rule 998): write `.loop-commit-msg`, write the mermaid file (step 8), then end this run.
8. At the end of every run: (a) Write one line to `.loop-commit-msg` in the repo root so the loop can use it for the commit (e.g. `Worked on: <brief>. Blocked: <if any>.`). (b) Add one Mermaid diagram file under `docs/loop/`. Create the directory if needed. One file per run; use a filename that identifies the work (e.g. `per-subquery-tools.mermaid` or `auth-flow.mermaid`). The diagram should summarize what was implemented, what was blocked (if any), and key decisions or flow for this run (e.g. flowchart or sequence diagram in Mermaid syntax).

NOTE: Keep @AGENTS.md operational only (how to build/test/run). Keep status/progress in @IMPLEMENTATION_PLAN.md.
NOTE: Prefer complete functionality over placeholders/stubs unless explicitly needed.
