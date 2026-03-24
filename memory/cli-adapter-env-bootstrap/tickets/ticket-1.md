Title: Seed repo-local CLI environment before adapter and factory initialization
Issue URL: https://github.com/cerredz/HarnessHub/issues/245
PR URL: https://github.com/cerredz/HarnessHub/pull/246

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
