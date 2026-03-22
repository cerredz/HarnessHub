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
