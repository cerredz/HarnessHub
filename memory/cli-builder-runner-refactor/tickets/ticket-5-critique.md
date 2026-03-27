Critique findings:
- The Instagram builder exposed a run-specific ICP resolver name even though the same parsing logic is shared by both `configure` and `run`.
- That naming made the builder boundary look more coupled to one command than it really is.

Improvements applied:
- Renamed the builder API to `resolve_icp_profiles(...)` and updated the Instagram command adapter to use the clearer shared name.

Regression check:
- Re-ran `python -m compileall harnessiq/cli/instagram/commands.py harnessiq/cli/builders harnessiq/cli/runners tests/test_cli_builders.py tests/test_cli_runners.py tests/test_instagram_cli.py`
- Re-ran `pytest tests/test_cli_builders.py tests/test_cli_runners.py tests/test_instagram_cli.py`
- Re-ran the manual Instagram `configure` + `run` smoke flow and observed `instagram-run-smoke-ok`
