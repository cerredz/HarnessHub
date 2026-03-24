Title: Seed repo-local CLI environment before adapter and factory initialization
Issue URL: https://github.com/cerredz/HarnessHub/issues/245

Intent: Ensure CLI run commands can construct model and browser/provider adapters from repo-local env files without requiring the user to export provider keys into the shell first. This directly addresses the reported prospecting Grok failure and keeps the platform-first adapter path consistent.

Scope: Add one shared CLI env bootstrap helper that loads `.env` plus `local.env` overlays, preserves existing shell env precedence, preserves LangSmith alias backfilling, and invoke it before runtime factory construction in the relevant CLI run paths. Do not change agent logic, provider transport logic, or credential-binding resolution.

Relevant Files:

- `harnessiq/cli/_langsmith.py`: expand the helper into a shared repo-local env bootstrap for CLI runs while preserving the LangSmith API.
- `harnessiq/cli/platform_commands.py`: seed the shared CLI env before generic model factory creation.
- `harnessiq/cli/prospecting/commands.py`: seed the shared CLI env before the reported prospecting model/browser factory construction.
- `harnessiq/cli/instagram/commands.py`: seed the shared CLI env before model/backend factory construction.
- `harnessiq/cli/linkedin/commands.py`: seed the shared CLI env before model/browser factory construction.
- `harnessiq/cli/leads/commands.py`: seed the shared CLI env before model/provider/storage factory construction.
- `harnessiq/cli/exa_outreach/commands.py`: seed the shared CLI env before model/provider/template factory construction.
- `tests/test_platform_cli.py`: verify the platform-first adapter path sees repo-local env vars before the model factory executes.
- `tests/test_prospecting_cli.py`: verify the legacy prospecting run path sees repo-local env vars before the model factory executes, including `local.env` support.

Approach: Centralize env discovery and merge logic in the existing CLI env helper module. Discover the nearest directory that contains repo-local env files, merge `.env` first and `local.env` second so `local.env` acts as an overlay, then write values into `os.environ` only when the key is not already set. Reuse the merged map to preserve the current LangSmith alias behavior. Call this helper at the start of each CLI `run` flow so every adapter/factory path receives the same env semantics.

Assumptions:

- Factory initialization is the earliest point that requires provider env vars in the affected commands.
- `local.env` should override `.env` when both exist in the same repo root.
- Existing tests around LangSmith env aliasing should continue to pass with the shared bootstrap.

Acceptance Criteria:

- [ ] CLI run paths load repo-local provider env vars before model/browser/provider factories are constructed.
- [ ] The legacy `prospecting run` path supports provider env bootstrap from `.env` and `local.env`.
- [ ] The platform-first adapter run path supports provider env bootstrap from `.env` and `local.env`.
- [ ] Existing process env vars are not overwritten by repo-local env file values.
- [ ] LangSmith alias backfilling continues to work.
- [ ] Focused automated tests cover the new bootstrap behavior and pass.

Verification Steps:

- Run `python -m pytest tests/test_platform_cli.py tests/test_prospecting_cli.py`.
- Run any narrower direct tests for the shared CLI env helper if added.
- Review the changed run flows to confirm env seeding occurs before factory imports/construction.

Dependencies: None.

Drift Guard: This ticket must not redesign credential binding, introduce third-party dotenv dependencies, or alter agent/provider runtime logic outside CLI env preparation. Keep the change in the CLI bootstrap layer and its tests.


## Quality Pipeline Results
## Stage 1: Static Analysis

No dedicated linter or static-analysis command is configured in `pyproject.toml`.

Manual static checks performed:

- Reviewed the changed CLI run paths to confirm `seed_cli_environment(...)` executes before any model, browser, provider, or storage factory construction.
- Ran `python -m compileall harnessiq\cli tests\test_cli_environment.py tests\test_platform_cli.py tests\test_prospecting_cli.py`.

Result: Passed.

## Stage 2: Type Checking

No dedicated type-checker configuration is present in the repository.

Manual type-safety checks performed:

- Preserved explicit function signatures and return annotations in the shared helper.
- Kept env bootstrap helpers dictionary-based and side-effect boundaries explicit.

Result: No type-checker configured; manual review completed.

## Stage 3: Unit Tests

Command run:

`python -m pytest tests/test_cli_environment.py tests/test_platform_cli.py tests/test_prospecting_cli.py tests/test_instagram_cli.py tests/test_linkedin_cli.py tests/test_leads_cli.py tests/test_exa_outreach_cli.py`

Result:

- `64 passed`

Notes:

- The LangSmith pytest plugin emitted a post-run `403 Forbidden` multipart ingest warning against the hosted LangSmith API. This did not fail the test session and did not affect the local assertions.

## Stage 4: Integration & Contract Tests

The repository does not define a separate contract-test suite. The executed CLI tests include integration-style coverage for the affected entrypoints:

- `tests/test_platform_cli.py` verifies the platform-first `run prospecting` path seeds `XAI_API_KEY` from `local.env` before the model factory executes.
- `tests/test_prospecting_cli.py` verifies the legacy `prospecting run` path seeds `XAI_API_KEY` from `local.env` before the model factory executes.
- Existing run-path tests for Instagram, LinkedIn, Leads, and Exa Outreach remained green after switching them to the shared env bootstrap helper.

Result: Passed.

## Stage 5: Smoke & Manual Verification

Manual verification performed:

- Confirmed `harnessiq/cli/platform_commands.py::_handle_run` now calls `seed_cli_environment(context.repo_root)` before `load_factory(args.model_factory)()`.
- Confirmed `harnessiq/cli/prospecting/commands.py::_handle_run` now calls `seed_cli_environment(Path(args.memory_root).expanduser())` before both model and browser-tools factory creation.
- Confirmed the other legacy run commands (`instagram`, `linkedin`, `leads`, `outreach`) now call the same helper before their respective runtime factories.
- Confirmed the shared helper merges `.env` then `local.env`, preserves process-env precedence, and still backfills LangSmith aliases.

Result: Passed.


## Post-Critique Changes
Post-implementation review findings:

- The initial implementation had strong `local.env` coverage but lacked a direct unit test proving that the existing `.env`-only flow still works after the helper refactor.

Post-critique improvement applied:

- Added `test_seed_cli_environment_reads_dot_env_when_local_env_is_absent` to `tests/test_cli_environment.py` so the refactor is explicitly guarded on both the legacy `.env` path and the new `local.env` overlay path.

Re-review after the improvement:

- The helper remains small and CLI-scoped.
- Precedence is explicit: shell env first, then `.env`, then `local.env` overlay.
- The run-path changes stay narrowly bounded to env bootstrapping and do not alter agent runtime logic.
- No further simplification or risk reduction was identified without expanding scope.

