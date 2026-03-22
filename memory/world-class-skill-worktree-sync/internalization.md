### 1a: Structural Survey
The requested change targets a standalone skill definition stored at `C:\Users\Michael Cerreto\.codex\skills\world-class-software-engineer\SKILL.md`. The artifact is an instruction document rather than application runtime code. Its structure is a linear operating procedure: high-level engineering standards, mandatory planning phases, GitHub issue workflow, implementation loop, quality gates, critique, PR creation, and worktree cleanup. The relevant convention is that execution guidance is embedded directly in prose and example shell snippets, so durable behavior changes should update both the narrative instruction and any command examples that operationalize it.

### 1b: Task Cross-Reference
The user wants the skill to instruct agents to refresh the main local repository before creating a new branch and worktree because `main` may advance in the background as PRs are merged. The concrete insertion point is `Phase 4`, `Step 2 — Create a Worktree`, currently around the existing `git worktree add .worktrees/issue-<issue-number> -b issue-<issue-number>` example. That section already governs branch/worktree creation, so adding the context there keeps the rule attached to the action it constrains. The change should also update the example command to branch explicitly from refreshed `main`, otherwise the new paragraph would remain advisory while the command could still branch from a stale or incorrect `HEAD`.

### 1c: Assumption & Risk Inventory
Assumption: the intended meaning of "main local repo is up to date" is specifically that the primary checkout's `main` branch should be synchronized with `origin/main` immediately before `git worktree add`.
Assumption: the skill should prefer a safe fast-forward update pattern over a generic pull so it does not silently create merge commits in the primary checkout.
Risk: adding prose without changing the sample command would leave a footgun in place because `git worktree add ... -b ...` without an explicit start-point can still branch from the current `HEAD`.
Risk: the skill file lives outside the normal writable repo root, so applying the patch may require elevated filesystem access depending on sandbox enforcement.

Phase 1 complete
