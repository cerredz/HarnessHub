## Post-Critique Review

### Findings

- `command_helpers.py` still carried several imports that belonged to the pre-extraction implementation, which made the compatibility layer look busier than it really is after the runner migration.
- The new runner tests covered resume behavior through the high-level `resolve_run_request()` path but did not directly exercise `resolve_resume_request_from_snapshot()`, one of the specific functions this ticket was meant to extract.

### Improvements Applied

- Removed the now-unused run/execution imports from `command_helpers.py` so the compatibility layer reflects the new delegation boundary more clearly.
- Added a direct runner test for `resolve_resume_request_from_snapshot()` to cover persisted-snapshot reuse independently of the broader platform command flow.

### Re-Verification

- Re-ran `python -m compileall harnessiq/cli/runners harnessiq/cli/commands/command_helpers.py tests/test_cli_runners.py`.
- Re-ran `pytest tests/test_cli_runners.py tests/test_platform_cli.py`.
- Result: all checks still passed.
