Title: Implement LinkedIn CLI commands for managed inputs and agent execution
Issue URL: Not created; `gh` is installed but unauthenticated in this environment.

Intent: Deliver the scriptable LinkedIn CLI workflow the user asked for: manage per-agent memory folders, ingest job-search inputs and user files, persist custom parameters, and run the LinkedIn SDK agent from the command line.

Scope:
- Add LinkedIn-specific CLI modules and subcommands under `harnessiq/cli/linkedin/`.
- Support commands for selecting an agent memory target, writing job preferences and profile content, ingesting files into managed memory, persisting typed runtime params, storing arbitrary key/value metadata, storing free-form prompt data, and running the LinkedIn agent.
- Reuse the LinkedIn memory-store contract from Ticket 1 and the CLI dispatch from Ticket 2.
- Update documentation and the repository file index for the new CLI structure.

Relevant Files:
- `harnessiq/cli/linkedin/__init__.py`: export LinkedIn CLI handlers.
- `harnessiq/cli/linkedin/commands.py`: implement LinkedIn subcommand parsing, persistence operations, and agent-run invocation.
- `harnessiq/agents/linkedin.py`: add any narrowly scoped constructor or loader helpers required to instantiate the agent from CLI-managed state.
- `tests/test_linkedin_agent.py`: extend tests for CLI-driven LinkedIn memory behavior if those helpers live here.
- `tests/test_sdk_package.py`: add CLI smoke assertions for LinkedIn command availability.
- `tests/test_linkedin_cli.py`: cover the LinkedIn CLI commands end to end.
- `README.md`: document the CLI installation and basic usage.
- `docs/linkedin-agent.md`: document the LinkedIn CLI workflow and managed memory behavior.
- `artifacts/file_index.md`: record the new `harnessiq/cli/` and `harnessiq/cli/linkedin/` structure.

Approach:
- Implement LinkedIn commands as explicit, scriptable subcommands with flags and repeatable options rather than an interactive flow.
- Keep data writes idempotent where practical: rewriting text inputs should replace the target content, while file ingestion should copy files into managed storage and update metadata deterministically.
- Build the run command so it reads the persisted typed params and constructs `LinkedInJobApplierAgent` accordingly, while still allowing the caller to supply or inject the model/runtime collaborator required by the SDK.
- Document any runtime limitations clearly if the CLI can prepare managed state more broadly than it can execute a live browser-backed workflow in tests.

Assumptions:
- The CLI can expose a practical run path even if live model/browser collaborators must be injected or mocked in tests.
- A dedicated `tests/test_linkedin_cli.py` file is acceptable for command-level behavior coverage.
- Updating both `README.md` and `docs/linkedin-agent.md` is sufficient documentation for this feature.

Acceptance Criteria:
- [ ] The root CLI exposes a `linkedin` command group.
- [ ] The LinkedIn CLI can create or prepare an agent-scoped memory folder and manage its durable inputs.
- [ ] The LinkedIn CLI can ingest one or more user files by copying them into managed storage while preserving source-path metadata.
- [ ] The LinkedIn CLI can persist agent-aligned typed params, arbitrary key/value metadata, and free-form prompt data.
- [ ] The LinkedIn CLI can construct and run the LinkedIn SDK agent from persisted state using the supported runtime contract.
- [ ] Automated tests cover command parsing and the primary LinkedIn CLI workflows.
- [ ] Documentation reflects the new CLI usage and repository structure.

Verification Steps:
- Static analysis: manually review command handlers for file safety, argument validation, and consistent exit behavior.
- Type checking: no configured checker; validate CLI command signatures and runtime wiring through tests and import-time execution.
- Unit tests: run `python -m unittest tests.test_linkedin_cli tests.test_linkedin_agent tests.test_sdk_package`.
- Integration and contract tests: run the full test suite to ensure the additive CLI layer does not regress existing SDK behavior.
- Smoke/manual verification: run the LinkedIn CLI help plus at least one prepare/ingest command locally and confirm the managed memory folder contents and command output match expectations.

Dependencies:
- Ticket 1: Add managed LinkedIn agent memory artifacts for CLI-driven configuration.
- Ticket 2: Add the Harnessiq CLI package and installable command entrypoint.

Drift Guard: This ticket must not redesign the core agent runtime or introduce unrelated agent domains into the CLI. The work is limited to a LinkedIn-focused command surface layered on the existing SDK.
