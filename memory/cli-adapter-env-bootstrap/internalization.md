### 1a: Structural Survey

`HarnessIQ` is a Python CLI/agent SDK with all live runtime code under `harnessiq/`. The repo uses a split between harness-specific legacy CLI commands such as `harnessiq/cli/prospecting/commands.py` and the newer platform-first manifest-driven CLI under `harnessiq/cli/platform_commands.py` plus `harnessiq/cli/adapters/`.

Relevant architectural conventions:

- CLI entrypoints parse arguments, normalize persisted memory/config, then build runtime dependencies from `module:callable` factories immediately before agent execution.
- Repo-local environment loading is implemented in small helpers rather than through a global dependency like `python-dotenv`.
- Provider/model adapters such as `harnessiq/integrations/grok_model.py` read required API keys directly from `os.environ`.
- Legacy harness-specific run commands usually seed LangSmith aliases from `.env` before model creation, but they do not currently seed arbitrary provider env vars.
- The platform-first CLI also seeds only LangSmith aliases before calling `load_factory(args.model_factory)()`.
- Tests rely mostly on `unittest`/`pytest` style modules under `tests/`, with CLI behavior verified through `harnessiq.cli.main.main(...)` and patched factories.

Relevant files:

- `harnessiq/cli/_langsmith.py`: current repo-local env discovery and LangSmith alias seeding.
- `harnessiq/cli/platform_commands.py`: generic `run` flow for manifest-driven adapters.
- `harnessiq/cli/prospecting/commands.py`: legacy prospecting CLI `run` flow used in the reported command.
- `harnessiq/cli/instagram/commands.py`, `harnessiq/cli/linkedin/commands.py`, `harnessiq/cli/leads/commands.py`, `harnessiq/cli/exa_outreach/commands.py`: other legacy `run` flows with the same env bootstrap pattern.
- `harnessiq/cli/adapters/*.py` and `harnessiq/cli/adapters/utils/factories.py`: adapter runtime surfaces that depend on the platform-first `run` path having already prepared env state.
- `harnessiq/integrations/grok_model.py`: concrete failure point when `XAI_API_KEY` is absent from `os.environ`.
- `tests/test_platform_cli.py` and `tests/test_prospecting_cli.py`: best coverage points for the reported regression and the adapter path.

### 1b: Task Cross-Reference

User request: ensure CLI adapters load required adapter env vars from repo-local env files before initialization, then open a PR against `main`.

Concrete mapping:

- The reported command uses the legacy path `python -m harnessiq.cli prospecting run ...`, so `harnessiq/cli/prospecting/commands.py::_handle_run` must seed repo-local env before it constructs the model factory and browser-tools factory.
- The user suspects the regression is related to the added adapter layer. The platform-first generic path in `harnessiq/cli/platform_commands.py::_handle_run` also needs the same fix so adapter-backed runs behave consistently.
- The existing helper in `harnessiq/cli/_langsmith.py` only backfills LangSmith aliases from `.env`; it should be expanded or complemented so general provider env vars are available too.
- Because the user explicitly referred to `local.env`, the env discovery logic should support both `.env` and `local.env`, with deterministic precedence, without overwriting already-exported shell env vars.
- Tests should verify both the old prospecting command path and the platform-first adapter path seed env vars before the model factory runs.

Behavior that must be preserved:

- Existing `.env` support must continue to work.
- Existing shell env vars must remain authoritative.
- LangSmith alias backfilling must continue to work.
- No CLI command semantics outside run-time env bootstrapping should change.

Blast radius:

- Small-to-moderate within CLI runtime setup only; no agent logic or provider transport logic should change.

### 1c: Assumption & Risk Inventory

Assumptions:

- The missing runtime env is the actual root cause of the reported failure. Code inspection strongly supports this because `create_grok_model` requires `XAI_API_KEY` from `os.environ`, while the reported prospecting run path never loads repo-local provider env vars.
- `local.env` is an intended repo-local overlay file even though the current code only recognizes `.env`.
- Preloading all repo-local env vars before factory construction is acceptable for CLI run paths and does not create unintended side effects because existing process env remains authoritative.

Risks:

- Expanding env loading too broadly could change behavior for commands that previously depended on an unset env var. Mitigation: scope the change to run paths and avoid overriding existing process env values.
- Supporting multiple env files can create ambiguity about precedence. Mitigation: use deterministic merge order and test it.
- Refactoring the shared helper could accidentally break existing LangSmith alias behavior. Mitigation: preserve the alias seeding API and cover the changed behavior with tests.

Phase 1 complete.
