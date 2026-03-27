Critique findings:
- `harnessiq/cli/linkedin/commands.py` still carried an unused `Sequence` import after the handler extraction.
- `harnessiq/cli/runners/linkedin.py` still carried an unused `Iterable` import.
- `LinkedInCliBuilder` exposed a public `load_store()` method that was not used outside the module and widened the surface area unnecessarily.

Improvements applied:
- Removed the dead imports from the LinkedIn command and runner modules.
- Dropped the unused public `load_store()` method from `LinkedInCliBuilder` and kept the store-loading helper private.

Regression check:
- Re-ran `python -m compileall harnessiq/cli/linkedin/commands.py harnessiq/cli/builders harnessiq/cli/runners tests/test_cli_builders.py tests/test_cli_runners.py tests/test_linkedin_cli.py`
- Re-ran `pytest tests/test_cli_builders.py tests/test_cli_runners.py tests/test_linkedin_cli.py`
- Re-ran the manual LinkedIn `configure` + `run` smoke flow and observed `linkedin-run-smoke-ok`
