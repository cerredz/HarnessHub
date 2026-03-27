Critique findings:
- `platform_commands.py` still carried an unused `Any` import after the handler refactor.
- `command_helpers.py` still carried an unused `replace` import after snapshot persistence moved into the runner.
- Credential validation rebuilt `set(manifest.provider_families)` on every assignment loop iteration.

Improvements applied:
- Removed the dead imports from `platform_commands.py` and `command_helpers.py`.
- Hoisted the provider-family set construction out of the credential-validation loop in `HarnessCliLifecycleBuilder`.

Regression check:
- Re-ran `python -m compileall harnessiq/cli/commands/platform_commands.py harnessiq/cli/commands/command_helpers.py harnessiq/cli/builders harnessiq/cli/runners tests/test_cli_builders.py tests/test_cli_runners.py tests/test_platform_cli.py`
- Re-ran `pytest tests/test_cli_builders.py tests/test_cli_runners.py tests/test_platform_cli.py`
- Re-ran the manual `prepare knowt` + `run knowt` smoke flow and observed `platform-run-smoke-ok`
