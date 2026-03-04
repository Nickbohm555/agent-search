0a. Study `specs/*` to learn the application specifications.
0b. Study @IMPLEMENTATION_PLAN.md (if present) to understand the plan so far.
0c. Study `src/lib/*` to understand shared utilities and components.
0d. For reference, the application source code is in `src/*`.

1. You are creating a SCOPED implementation plan for work: "${WORK_SCOPE}". Study @IMPLEMENTATION_PLAN.md (if present; it may be incorrect) and study existing source code in `src/*` and compare it against `specs/*`. For each task in the plan, derive required tests from acceptance criteria in specs - what specific outcomes need verification (behavior, performance, edge cases). Tests verify WHAT works, not HOW it's implemented. Include as part of task definition.
2. Analyze findings, prioritize tasks, and create/update @IMPLEMENTATION_PLAN.md as a bullet list sorted by highest priority items yet to be implemented.
3. For each task, derive verification requirements from acceptance criteria in specs (what outcomes must be validated, not implementation details).
4. Keep @IMPLEMENTATION_PLAN.md up to date with items considered complete/incomplete.

IMPORTANT: This is SCOPED PLANNING for "${WORK_SCOPE}" only. Create a plan containing ONLY tasks directly related to this work scope.
IMPORTANT: Be conservative. If uncertain whether a task belongs to this scope, exclude it.
IMPORTANT: Plan only. Do NOT implement anything. Do NOT commit anything.
IMPORTANT: Do NOT assume functionality is missing; confirm with code search first.
IMPORTANT: Treat `src/lib/*` as the project's standard library for shared utilities and components. Prefer consolidated, idiomatic implementations there over ad-hoc copies.

ULTIMATE GOAL: Achieve the scoped work "${WORK_SCOPE}".
If a needed element is missing, search first to confirm it does not exist, then if needed author/update the related spec at `specs/FILENAME.md`.
If you create a new scoped element, document the implementation tasks in @IMPLEMENTATION_PLAN.md.
