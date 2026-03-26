Title: Apply PR 278 review feedback across Instagram and agent helper modules

Issue URL: https://github.com/cerredz/HarnessHub/issues/279

PR URL: https://github.com/cerredz/HarnessHub/pull/280

Intent:
Implement all owner comments left on PR `#278` by bringing the Instagram ICP-rotation work onto a fresh branch from `main`, revising the Instagram prompt and loop structure per review, and performing the requested cross-agent helper-file refactor under `harnessiq/agents/`.

Scope:
- Reapply the relevant Instagram ICP-rotation behavior from `origin/issue-273` onto current `main`.
- Update the Instagram master prompt to restore explicit identity/goal structure plus an action-oriented checklist.
- Refactor the Instagram run loop so one ICP iteration is isolated in a helper and the loop body has concise readability comments.
- Add `helpers.py` to each agent package under `harnessiq/agents/` that contains `agent.py`.
- Move clearly helper-oriented logic out of agent modules into local helper modules and centralize shared helper utilities in `harnessiq/agents/helpers.py` where the same logic is reused across agents.
- Update affected tests and generated docs/artifacts as needed.
- Do not change provider contracts, CLI flags, or unrelated runtime architecture.

Relevant Files:
- `harnessiq/agents/helpers.py`: shared reusable agent helper utilities extracted from repeated per-agent logic.
- `harnessiq/agents/*/helpers.py`: package-local helper modules for agent-specific utilities.
- `harnessiq/agents/instagram/agent.py`: apply ICP-rotation work plus review-driven prompt/loop refactor integration.
- `harnessiq/agents/instagram/prompts/master_prompt.md`: restore structured prompt sections and checklist.
- `harnessiq/shared/instagram.py`: reapply ICP state/run-state persistence from the original PR.
- `harnessiq/tools/instagram.py`: bind the search tool to active-ICP-aware persistence.
- `harnessiq/tools/instagram/operations.py`: scope duplicate detection and persistence by active ICP.
- `harnessiq/cli/instagram/commands.py`: expose per-ICP summary information from the new persistence model.
- `harnessiq/cli/adapters/instagram.py`: expose per-ICP summary information in the platform CLI.
- `tests/test_instagram_agent.py`: cover ICP rotation, scoped recent searches, loop behavior, and prompt/compatibility expectations.
- `tests/test_instagram_cli.py`: cover updated per-ICP show summary behavior.
- `artifacts/file_index.md`: regenerated if the agent package layout or documented standards change.

Approach:
Start from fresh `main`, copy in the functional Instagram changes from `origin/issue-273`, then refine them to match the review comments. Extract repeated helper functions from agent modules into sibling `helpers.py` files, using `harnessiq/agents/helpers.py` for utilities that are genuinely shared across multiple agents such as repo-root resolution, optional text reads, memory-path resolution, and UTC/timestamp helpers. Keep orchestration logic and public agent classes in `agent.py`, and avoid changing public imports or provider behavior beyond what is required to satisfy the review comments.

Assumptions:
- "All agents" means every package in `harnessiq/agents/` with `agent.py`.
- Empty or near-empty helper modules are acceptable for packages that currently do not warrant substantial extraction yet.
- The existing `origin/issue-273` implementation is the authoritative functional baseline for the Instagram feature.
- One PR should contain the full implementation.

Acceptance Criteria:
- [ ] The Instagram ICP-rotation behavior from PR `#278` is present on a fresh branch from current `main`.
- [ ] The Instagram master prompt contains an identity section, a goal section, and a structured action-oriented checklist.
- [ ] The Instagram run loop delegates one iteration to a helper and includes short comments clarifying the high-level steps.
- [ ] Each agent package under `harnessiq/agents/` with `agent.py` has a sibling `helpers.py` file.
- [ ] Repeated helper logic extracted across agents is centralized in `harnessiq/agents/helpers.py` where appropriate.
- [ ] Agent behavior outside the requested Instagram feature/refactor remains unchanged.
- [ ] Targeted Instagram tests and any affected broader agent/import/docs checks pass.

Verification Steps:
- Run syntax/static verification on changed Python modules.
- Run `python -m unittest tests.test_instagram_agent tests.test_instagram_cli`.
- Run any additional affected tests for agent imports or shared manifest/docs sync if touched.
- Regenerate repo docs/artifacts if required and verify sync-related checks pass.
- Review the diff to confirm the refactor remains within `harnessiq/agents/`, Instagram-related runtime files, targeted tests, and generated artifacts.

Dependencies:
- None.

Drift Guard:
This ticket must implement the specific review feedback from PR `#278` without turning into a general repo-wide cleanup. It must not redesign `BaseAgent`, alter provider APIs, or refactor modules outside the agent/helper surfaces needed to satisfy the comments and keep the Instagram feature working on `main`.
