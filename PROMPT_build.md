0a. Study `specs/*` to learn the application specifications.
0b. Study @IMPLEMENTATION_PLAN.md.
0c. For reference, the application source code is in `src/*`.

999. Required tests derived from acceptance criteria must exist and pass before committing. Tests are part of implementation scope, not optional. Test-driven development approach: tests can be written first or alongside implementation.

1. Implement functionality per the specifications.
2. Follow @IMPLEMENTATION_PLAN.md and choose the most important item to address. Tasks include required tests - implement tests as part of task scope.
3. Before making changes, search the codebase; do not assume not implemented.
4. After implementing functionality, run all required tests specified in the task definition. All required tests must exist and pass before the task is considered complete.
5. Update @IMPLEMENTATION_PLAN.md with findings and completion state.
6. When checks pass: `git add -A`, `git commit` with a clear message, then `git push`.

IMPORTANT: Keep @AGENTS.md operational only (how to build/test/run). Keep status/progress in @IMPLEMENTATION_PLAN.md.
IMPORTANT: Implement functionality completely; avoid placeholders/stubs unless explicitly required.
