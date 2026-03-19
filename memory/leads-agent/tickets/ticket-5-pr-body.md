Title: Add leads agent CLI, documentation, and repository exports

Issue URL: https://github.com/cerredz/HarnessHub/issues/153

Intent:
Make the new leads agent usable from the repo's public surfaces by adding CLI entrypoints, docs/examples, export wiring, and architecture index updates.

Scope:
This ticket adds CLI commands, docs, README coverage, package/toolset exports, and artifact index updates needed to expose the completed leads agent end to end.
This ticket does not add new runtime behavior or new provider functionality beyond wiring what earlier tickets produced.

Relevant Files:
- `harnessiq/cli/leads/__init__.py`
- `harnessiq/cli/leads/commands.py`
- `harnessiq/cli/main.py`
- `README.md`
- `docs/agent-runtime.md`
- `docs/tools.md`
- `docs/leads-agent.md`
- `artifacts/file_index.md`
- `tests/test_leads_cli.py`

## Quality Pipeline Results

Stage 1 - Static Analysis
- No project linter is configured in this repository.
- Passed `python -m py_compile` for:
  - `harnessiq/cli/leads/commands.py`
  - `harnessiq/cli/leads/__init__.py`
  - `tests/test_leads_cli.py`

Stage 2 - Type Checking
- No standalone type checker is configured in this repository.
- Verified import safety through `py_compile` plus the test suite.

Stage 3 - Unit Tests
- Passed:
  - `python -m pytest .worktrees/issue-153/tests/test_leads_cli.py -q`
  - `python -m pytest .worktrees/issue-153/tests/test_leads_agent.py .worktrees/issue-153/tests/test_leads_shared.py .worktrees/issue-153/tests/test_exa_outreach_cli.py -q`
  - `python -m pytest .worktrees/issue-153/tests/test_apollo_provider.py -q`

Stage 4 - Integration and Contract Tests
- Passed:
  - `python -m pytest .worktrees/issue-153/tests/test_leads_cli.py .worktrees/issue-153/tests/test_leads_agent.py .worktrees/issue-153/tests/test_leads_shared.py .worktrees/issue-153/tests/test_exa_outreach_cli.py -q`
- Observed unrelated existing failure:
  - `python -m pytest .worktrees/issue-153/tests/test_linkedin_cli.py -q`
  - `LinkedInCLITests.test_run_uses_persisted_state_and_factory_model` expects pure JSON from `linkedin run`, but that command prints a human-readable summary before the JSON payload.

Stage 5 - Smoke and Manual Verification
- Smoke-verified `leads prepare`, `leads configure`, `leads show`, and `leads run` through `tests/test_leads_cli.py`.
- Confirmed CLI wiring for:
  - root parser registration
  - persisted run config and runtime parameter storage
  - per-ICP state initialization during configure
  - runtime overrides for run-config-backed settings
  - pluggable storage backend injection

## Post-Critique Changes

- Fixed a CLI correctness bug where run-time overrides for `search_summary_every`, `search_tail_size`, and `max_leads_per_icp` were accepted but not applied.
- Added `--storage-backend-factory` so the CLI exposes the same pluggable backend surface as the SDK.
- Initialized per-ICP state files during `leads configure` so `leads show` renders real ICP state before the first run.
- Added README, docs, and architecture-index coverage for the leads agent and Apollo provider.
- Tightened the README `leads run` example so it includes `--memory-root` consistently with the other CLI examples.
