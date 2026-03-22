Verification for issue `#207`

Commands run:

- `python -m compileall harnessiq tests`
- `..\..\.venv\Scripts\pytest.exe -q tests\test_output_sinks.py tests\test_ledger_cli.py`
- `..\..\.venv\Scripts\pytest.exe -q tests\test_agents_base.py tests\test_linkedin_cli.py`
- `..\..\.venv\Scripts\python.exe -m harnessiq.cli connections list`
- `..\..\.venv\Scripts\python.exe -m harnessiq.cli report --help`

Results:

- `python -m compileall harnessiq tests`: passed.
- `tests/test_output_sinks.py tests/test_ledger_cli.py`: passed with `10 passed in 0.44s`.
- `python -m harnessiq.cli connections list`: passed and returned an empty `connections` list.
- `python -m harnessiq.cli report --help`: passed and printed the expected command help.
- `tests/test_agents_base.py tests/test_linkedin_cli.py`: 2 failures, both pre-existing on `origin/main` and unrelated to the ledger refactor:
  - `tests/test_agents_base.py::BaseAgentTests::test_run_resets_context_when_prune_progress_interval_is_reached`
    - baseline test bug: `pruning_progress_value` is indented under `_FailingSink` instead of `_InspectableAgent` in `tests/test_agents_base.py` on `origin/main`, so the override never applies.
  - `tests/test_linkedin_cli.py::LinkedInCLITests::test_run_seeds_langsmith_environment_from_repo_env`
    - baseline environment issue: `ConnectionsConfigStore()` reaches `Path.home()` after `patch.dict(os.environ, {}, clear=True)` removes the home-directory variables, which raises `RuntimeError("Could not determine home directory.")`.
