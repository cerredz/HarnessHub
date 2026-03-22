## Summary

- decompose `harnessiq.utils.ledger` into focused models, connections, exports, reports, and sinks modules
- keep `harnessiq.utils.ledger` as a compatibility facade so existing imports continue to work
- preserve the existing `harnessiq.utils` re-export surface and ledger CLI behavior

## Testing

- `python -m compileall harnessiq tests`
- `..\..\.venv\Scripts\pytest.exe -q tests\test_output_sinks.py tests\test_ledger_cli.py`
- `..\..\.venv\Scripts\pytest.exe -q tests\test_agents_base.py tests\test_linkedin_cli.py` *(contains 2 pre-existing baseline failures unrelated to this refactor; documented below)*
- `..\..\.venv\Scripts\python.exe -m harnessiq.cli connections list`
- `..\..\.venv\Scripts\python.exe -m harnessiq.cli report --help`

## Known baseline failures

- `tests/test_agents_base.py::BaseAgentTests::test_run_resets_context_when_prune_progress_interval_is_reached`
- `tests/test_linkedin_cli.py::LinkedInCLITests::test_run_seeds_langsmith_environment_from_repo_env`
