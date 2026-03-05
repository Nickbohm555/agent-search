0b. Study @IMPLEMENTATION_PLAN.md.
0c. For reference, the application source code is in `src/*`.

Before starting, completely restart the application so we have fresh builds, logs, ect;

997. Iteration scope: complete exactly ONE item per run—always the first item listed in @IMPLEMENTATION_PLAN.md—then stop for the next loop.

1. Take the first item from @IMPLEMENTATION_PLAN.md (do not choose; always use the first). Include relevant tests in the task scope. 

2. Before making changes, search the codebase so existing functionality is reused when possible.

3. After implementing functionality, ALWAYS add logs for visibility and check what containers were changed and either restart or completely reboot depending on the task. when in doubt, restart the application entirely and check all the container logs. If you see an error, fix it now and re-run to make sure it works. run the required tests from the task definition. You must provide and view logs for every item built. 

4. When the task is completed: always remove that item from @IMPLEMENTATION_PLAN.md and append it to @completed.md. If completed, append the item as-is. 

5. After completion or blocked, either way we write `.loop-commit-msg` then end this run. For `loop-commit-msg`, add every a short summary of what was built and tested. 


NOTE: Keep @AGENTS.md operational only (how to build/test/run). Keep remaining work in @IMPLEMENTATION_PLAN.md; record completed items in @completed.md.
NOTE: Prefer complete functionality over placeholders/stubs unless explicitly needed.
