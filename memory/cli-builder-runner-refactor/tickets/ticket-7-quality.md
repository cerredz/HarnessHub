Stage 1 - Static Analysis
- No dedicated linter is configured for this CLI package. I manually reviewed the Prospecting command module after extraction to confirm the handlers now only parse arguments and delegate to the Prospecting builder/runner services.

Stage 2 - Type Checking
- No project type checker is configured for this repository. The new Prospecting builder/runner modules and updated command wiring passed Python bytecode compilation.
- Command: `python -m compileall harnessiq/cli/prospecting/commands.py harnessiq/cli/builders harnessiq/cli/runners tests/test_cli_builders.py tests/test_cli_runners.py tests/test_prospecting_cli.py`

Stage 3 - Unit Tests
- Command: `pytest tests/test_cli_builders.py tests/test_cli_runners.py tests/test_prospecting_cli.py`
- Result: `28 passed`

Stage 4 - Integration & Contract Tests
- The Prospecting CLI suite exercises the public `prepare`, `configure`, `show`, `run`, and `init-browser` flows end to end, while the direct builder/runner tests cover the extracted Prospecting services and their browser/runtime orchestration boundaries.
- Command: `pytest tests/test_cli_builders.py tests/test_cli_runners.py tests/test_prospecting_cli.py`
- Result: `28 passed`

Stage 5 - Smoke & Manual Verification
- Executed in-process smoke checks against the live Prospecting CLI handlers:
  - `prospecting configure --agent nj-dentists --memory-root <temp> --company-description-text "Owner-operated dental practices in New Jersey." --runtime-param max_tokens=4096 --custom-param max_searches_per_run=12`
  - `prospecting run --agent nj-dentists --memory-root <temp> --model-factory tests.test_prospecting_cli:_recording_model_factory --runtime-param max_tokens=2048`
  - `prospecting init-browser --agent nj-dentists --memory-root <temp>`
- Observed `result.status == "completed"` for the run path, confirmed the mocked `GoogleMapsProspectingAgent.from_memory(...)` received `runtime_overrides["max_tokens"] == 2048`, and verified the browser bootstrap path emitted `status == "session_saved"` with the expected persistent browser-data directory.
