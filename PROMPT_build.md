0b. Study @IMPLEMENTATION_PLAN.md.
0c. For reference, the application source code is in `src/*`.


997. Iteration scope: complete exactly ONE item per run—always the first item listed in @IMPLEMENTATION_PLAN.md—then stop for the next loop.

1. Take the first item from @IMPLEMENTATION_PLAN.md (do not choose; always use the first). Include relevant tests in the task scope. 

2. Before making changes, search the codebase so existing functionality is reused when possible.

3. After implementing functionality, run the required tests from the task definition. Prefer all required tests passing unless blocked by rule 998.

4. When the task is completed or blocked: always remove that item from @IMPLEMENTATION_PLAN.md and append it to @completed.md. If completed, append the item as-is. 

5. For blocked external dependency (rule 998): remove the item from @IMPLEMENTATION_PLAN.md and add it to @completed.md with a BLOCKED message and explanation (see step 5);

6. After completion or blocked, either way we write `.loop-commit-msg` then end this run. For `loop-commit-msg`, add every a short summary of what was built and tested.


NOTE: Keep @AGENTS.md operational only (how to build/test/run). Keep remaining work in @IMPLEMENTATION_PLAN.md; record completed items in @completed.md.
NOTE: Prefer complete functionality over placeholders/stubs unless explicitly needed.
