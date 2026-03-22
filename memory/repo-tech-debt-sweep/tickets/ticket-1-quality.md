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
