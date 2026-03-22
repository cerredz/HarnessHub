Title: Add CLI credential management commands and document the workflow

Issue URL: https://github.com/cerredz/HarnessHub/issues/30

Intent:
Give users a first-class way to register and inspect agent credential bindings from the command line, matching the new SDK config APIs and making the credential workflow discoverable in the package surface and docs.

Scope:
Add CLI commands for writing and showing credential bindings, integrate them into the main parser, and update README/docs/examples/tests to show direct-code and CLI-based usage. This ticket assumes the config layer and agent wiring already exist.

Relevant Files:
- `harnessiq/cli/main.py`: register the new config command group
- `harnessiq/cli/config/__init__.py`: CLI export surface for config commands
- `harnessiq/cli/config/commands.py`: CLI handlers for saving/showing credential bindings
- `tests/test_config_cli.py`: unit coverage for the new CLI commands
- `tests/test_sdk_package.py`: CLI/package smoke coverage updates if needed
- `README.md`: top-level quick-start documentation for credentials
- `docs/agent-runtime.md`: SDK usage example with the config loader
- `artifacts/file_index.md`: document the new CLI/config structure if needed

Approach:
Follow the existing LinkedIn CLI pattern: subcommand family, JSON output, explicit validation, and deterministic file locations. Add a top-level `config` CLI namespace so credential management is SDK-wide rather than agent-specific. Support at least a write/register command and a show/read command. Reuse the config-layer store instead of duplicating persistence logic. Keep output structured so the commands remain scriptable.

Assumptions:
- A single repo-local credential config file is sufficient for the initial CLI workflow.
- Users can identify an agent binding by logical agent name and credential field mapping.
- JSON output is the expected CLI contract, consistent with the current LinkedIn commands.

Acceptance Criteria:
- [ ] `harnessiq config ...` commands are available from the main CLI help output.
- [ ] Users can create/update an agent credential binding from the CLI.
- [ ] Users can inspect persisted credential bindings from the CLI.
- [ ] CLI commands surface clear errors when `.env` or required variables are missing during resolution paths.
- [ ] README/docs describe both direct SDK usage and CLI-based usage for credentials.
- [ ] CLI tests cover the new command behavior.

Verification Steps:
- Run CLI unit tests for both LinkedIn and config command families.
- Run `python -m harnessiq.cli --help` and confirm the new command family appears.
- Manually create a temporary binding via CLI, inspect it, and load it via the SDK API.

Dependencies:
- Ticket 1
- Ticket 2

Drift Guard:
This ticket must not redesign the existing LinkedIn memory CLI or introduce remote secret storage. It only exposes the new credential config/store through the existing local CLI architecture and updates docs.
