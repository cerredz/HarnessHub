Title: Add the `harnessiq gcloud` CLI scaffold
Issue URL: https://github.com/cerredz/HarnessHub/issues/298
PR URL: https://github.com/cerredz/HarnessHub/pull/316

Intent:
Create the top-level CLI entry point and shared command-family structure so later tickets can add focused GCP command handlers without repeatedly touching the root parser.

Scope:
Add the `harnessiq gcloud` package, register it in `harnessiq/cli/main.py`, and create the shared parser structure for subcommands. This ticket does not yet add the full command handler set for health, credentials, or deployment operations.

Relevant Files:
- `harnessiq/cli/gcloud/__init__.py`: Export the GCP CLI registration hook.
- `harnessiq/cli/gcloud/commands.py`: Add the argparse command-family scaffold and shared helpers.
- `harnessiq/cli/main.py`: Register the new top-level `gcloud` family.
- `tests/test_gcloud_cli.py`: Verify top-level parser registration and help-path behavior.

Approach:
Follow the repositoryâ€™s existing argparse architecture exactly: top-level registration in `harnessiq/cli/main.py`, a dedicated `commands.py` module for the command family, and JSON-first conventions for later handlers. Keep this ticket focused on structure so later CLI tickets can fill in behavior incrementally.

Assumptions:
- The GCP command family should live beside other top-level command families rather than under the platform-first generic `prepare/show/run` tree.
- It is acceptable for some subcommands to remain parser-only placeholders until later CLI tickets land.

Acceptance Criteria:
- [ ] `harnessiq gcloud ...` is registered at the top level.
- [ ] The GCP CLI package exists and exposes a registration hook.
- [ ] Shared subparser structure exists for later health, credential, and deployment commands.
- [ ] Parser-level tests verify help output and registration behavior.

Verification Steps:
- Static analysis: No configured linter; manually review argparse wiring and package exports.
- Type checking: No configured type checker; keep CLI registration helpers annotated and validate imports via tests.
- Unit tests: Run `pytest tests/test_gcloud_cli.py`.
- Integration and contract tests: Not applicable beyond parser construction in this ticket.
- Smoke and manual verification: Run `python -m harnessiq.cli gcloud --help` locally.

Dependencies:
Ticket 9.

Drift Guard:
Do not add full command logic in this ticket. The deliverable is the top-level CLI scaffold and parser structure only.

