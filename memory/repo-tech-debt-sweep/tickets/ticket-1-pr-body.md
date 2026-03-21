Title: Centralize shared CLI agent-command helpers and JSON rendering

Intent:
Reduce repeated helper logic across the agent-oriented CLI modules so command behavior is easier to reason about, update, and test. This directly improves readability and lowers the risk of command drift when new agent CLIs are added.

Issue URL: https://github.com/cerredz/HarnessHub/issues/205

Scope:

- Add a shared CLI helper module for the repeated command patterns currently duplicated across agent command modules.
- Move shared logic for JSON emission, slugified memory-path resolution, text-or-file argument handling, and generic runtime assignment parsing into that shared helper layer.
- Update the existing command modules to use the shared helpers without changing their public command names or output shapes.
- Keep command-specific normalization logic inside each command module where it belongs.
- Do not redesign CLI UX or rename flags.

Relevant Files:

- `harnessiq/cli/common.py`: new shared helper module for JSON output, memory-path helpers, text/file resolution, and generic assignment parsing.
- `harnessiq/cli/linkedin/commands.py`: replace duplicated helper implementations with imports from the shared helper layer.
- `harnessiq/cli/instagram/commands.py`: replace duplicated helper implementations with imports from the shared helper layer.
- `harnessiq/cli/prospecting/commands.py`: replace duplicated helper implementations with imports from the shared helper layer.
- `harnessiq/cli/exa_outreach/commands.py`: replace duplicated helper implementations with imports from the shared helper layer.
- `harnessiq/cli/leads/commands.py`: replace duplicated helper implementations with imports from the shared helper layer discovered on `origin/main`.
- `harnessiq/cli/ledger/commands.py`: reuse the shared JSON emission helper.
- `tests/test_cli_common.py`: direct unit coverage for the new helper module.
- `tests/test_linkedin_cli.py`: confirm behavior is unchanged after helper extraction.
- `tests/test_instagram_cli.py`: confirm behavior is unchanged after helper extraction.
- `tests/test_prospecting_cli.py`: confirm behavior is unchanged after helper extraction.
- `tests/test_exa_outreach_cli.py`: confirm behavior is unchanged after helper extraction.
- `tests/test_leads_cli.py`: confirm behavior is unchanged after helper extraction where the current `origin/main` baseline allows it.
- `tests/test_ledger_cli.py`: confirm ledger CLI JSON emission still works through the shared helper.

Approach:

- Create a small, dependency-light helper module under `harnessiq/cli/`.
- Keep the abstractions narrow and concrete: pure helpers rather than new OO command wrappers.
- Provide a JSON rendering helper that uses deterministic formatting and tolerates common Path-like values safely.
- Apply the same extraction to every agent-style CLI module that exists on `origin/main`, including `leads`, so the duplication is reduced consistently rather than only partially.
- Provide a generic assignment parser that returns scalar JSON-decoded values; each CLI module will continue to run its own command-specific normalization after parsing.
- Refactor incrementally and keep command output payloads byte-for-byte compatible where reasonable.

Assumptions:

- Existing tests already capture the intended command behavior closely enough to guard the refactor.
- No external user depends on the private helper function names currently defined inside the command modules.
- Shared helpers should remain internal to the CLI package and not become top-level public SDK exports.

Acceptance Criteria:

- [ ] A new shared helper module exists under `harnessiq/cli/` for the repeated agent-command helper logic.
- [ ] The duplicated helper implementations are removed from the touched CLI modules and replaced with shared imports.
- [ ] Public command names, flags, and returned JSON payload shapes remain unchanged.
- [ ] Existing CLI tests covering the touched commands pass without requiring fixture rewrites for changed behavior.
- [ ] The new shared helper module has direct unit or usage coverage through the updated CLI tests.

Verification Steps:

- Static analysis: run `python -m compileall harnessiq tests`.
- Type checking: no configured type checker; verify the refactor keeps existing annotations coherent and does not introduce new untyped public helper signatures where obvious annotations are practical.
- Unit tests: run `.venv\Scripts\pytest.exe -q tests/test_linkedin_cli.py tests/test_instagram_cli.py tests/test_prospecting_cli.py tests/test_exa_outreach_cli.py tests/test_ledger_cli.py`.
- Integration and contract tests: run `.venv\Scripts\pytest.exe -q tests/test_sdk_package.py` if unaffected by unrelated repo-root discovery problems; otherwise note the current baseline blocker and run the touched CLI suites as the integration signal.
- Smoke/manual verification: run `.venv\Scripts\python.exe -m harnessiq.cli --help` and one representative JSON-emitting command path that does not require external credentials.

Dependencies:

- None.

Drift Guard:

This ticket must stay focused on deduplicating helper logic and stabilizing CLI implementation structure. It must not redesign command semantics, rename subcommands, change memory-store formats, or expand runtime capabilities unrelated to the helper extraction.


## Quality Pipeline Results
Stage 1 - Static Analysis

- `python -m compileall harnessiq tests`
- Result: passed.

Stage 2 - Type Checking

- No project type checker is configured in `pyproject.toml`.
- Validation approach: kept all new shared helper functions explicitly annotated and confirmed the refactor compiled cleanly.

Stage 3 - Unit Tests

- `..\..\.venv\Scripts\pytest.exe -q tests/test_cli_common.py tests/test_linkedin_cli.py tests/test_instagram_cli.py tests/test_prospecting_cli.py tests/test_exa_outreach_cli.py tests/test_ledger_cli.py tests/test_leads_cli.py`
- Result: 70 passed, 2 failed.
- Baseline failures observed on `origin/main` and left out of this ticket scope:
  - `tests/test_linkedin_cli.py::LinkedInCLITests::test_run_seeds_langsmith_environment_from_repo_env`
    - fails because `ConnectionsConfigStore()` reaches `Path.home()` after `patch.dict(os.environ, {}, clear=True)` and the environment no longer exposes a resolvable home directory.
  - `tests/test_leads_cli.py::TestRunCommand::test_run_uses_provider_tools_and_storage_backend_factories`
    - fails because `harnessiq/agents/leads/agent.py` references undefined `_merge_tools` / `external_tools` names from a pre-existing merge artifact.
- Focused refactor verification excluding those known unrelated failures:
  - `..\..\.venv\Scripts\pytest.exe -q tests/test_cli_common.py tests/test_linkedin_cli.py tests/test_instagram_cli.py tests/test_prospecting_cli.py tests/test_exa_outreach_cli.py tests/test_ledger_cli.py tests/test_leads_cli.py -k "not test_run_seeds_langsmith_environment_from_repo_env and not test_run_uses_provider_tools_and_storage_backend_factories"`
  - Result: 69 passed, 3 deselected.

Stage 4 - Integration & Contract Tests

- `..\..\.venv\Scripts\pytest.exe -q tests/test_sdk_package.py`
- Result: 4 passed, 1 failed.
- Baseline failure left out of scope:
  - `HarnessiqPackageTests.test_agents_and_providers_keep_shared_definitions_out_of_local_modules`
  - failure reports pre-existing shared-definition violations in agent modules on `origin/main`.

Stage 5 - Smoke & Manual Verification

- `..\..\.venv\Scripts\python.exe -m harnessiq.cli --help`
- Result: passed. The CLI renders all expected top-level command groups, including `linkedin`, `leads`, `outreach`, `instagram`, and `prospecting`.
- Manual JSON smoke:
  - ran an inline Python snippet that executed `instagram configure` and `instagram show` through `harnessiq.cli.main`.
  - Result: the command emitted deterministic JSON with the expected memory path, ICP list, and empty lead/email counts.


## Post-Critique Changes
Post-critique findings:

- The original ticket artifact did not account for `harnessiq/cli/leads/commands.py`, which exists on `origin/main` and follows the same duplicated helper pattern. Leaving it out would make the PR look like it had drifted beyond its own spec.
- The shared JSON helper needed explicit coverage for fallback stringification of non-JSON leaf values so mocked CLI tests would not silently re-break later.

Improvements applied:

- Updated `memory/repo-tech-debt-sweep/tickets/ticket-1.md` inside the worktree to include the `leads` CLI module and its corresponding CLI test coverage in the scoped work.
- Added direct unit coverage in `tests/test_cli_common.py` for fallback JSON stringification.

Post-critique verification:

- `python -m compileall harnessiq tests`
- `..\..\.venv\Scripts\pytest.exe -q tests/test_cli_common.py tests/test_linkedin_cli.py tests/test_instagram_cli.py tests/test_prospecting_cli.py tests/test_exa_outreach_cli.py tests/test_ledger_cli.py tests/test_leads_cli.py -k "not test_run_seeds_langsmith_environment_from_repo_env and not test_run_uses_provider_tools_and_storage_backend_factories"`
- Result: passed (`69 passed, 3 deselected`).

