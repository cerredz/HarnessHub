Stage 1 - Static Analysis
- No dedicated linter is configured for this CLI package. I manually reviewed the Instagram command module after extraction to confirm the handlers now only parse arguments and delegate to the Instagram builder/runner services.

Stage 2 - Type Checking
- No project type checker is configured for this repository. The new Instagram builder/runner modules and updated command wiring passed Python bytecode compilation.
- Command: `python -m compileall harnessiq/cli/instagram/commands.py harnessiq/cli/builders harnessiq/cli/runners tests/test_cli_builders.py tests/test_cli_runners.py tests/test_instagram_cli.py`

Stage 3 - Unit Tests
- Command: `pytest tests/test_cli_builders.py tests/test_cli_runners.py tests/test_instagram_cli.py`
- Result: `23 passed`

Stage 4 - Integration & Contract Tests
- The Instagram CLI suite exercises the public `prepare`, `configure`, `show`, `run`, and `get-emails` flows end to end, while the direct builder/runner tests cover the extracted Instagram services and session-directory behavior.
- Command: `pytest tests/test_cli_builders.py tests/test_cli_runners.py tests/test_instagram_cli.py`
- Result: `23 passed`

Stage 5 - Smoke & Manual Verification
- Executed an in-process smoke run against the live Instagram CLI entrypoint:
  - `instagram configure --agent smoke-creator --memory-root <temp> --icp "fitness creators"`
  - `instagram run --agent smoke-creator --memory-root <temp> --model-factory mod:model --icp "fitness creators" --max-cycles 1`
- Observed `result.status == "completed"` and `email_count == 1`.
