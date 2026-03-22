Title: Expose LinkedIn Google Drive settings and credential workflows through SDK and CLI
Issue URL: https://github.com/cerredz/HarnessHub/issues/146

Intent: Make the new Google Drive-backed LinkedIn behavior usable from public SDK and CLI entrypoints so users can save credentials, enable or disable Drive persistence, and run the agent without manual internal wiring.

Scope:
- Expose ergonomic SDK helpers for saving/loading Google Drive credentials for the LinkedIn agent.
- Extend the LinkedIn CLI surface so users can persist `save_to_google_drive` and configure or inspect the relevant credential linkage.
- Update docs and repository artifacts to reflect the new provider and LinkedIn runtime behavior.
- Preserve backward compatibility for existing LinkedIn CLI users who do not enable Google Drive sync.

Relevant Files:
- `harnessiq/cli/main.py`: register any new CLI command group if credential configuration becomes user-facing there.
- `harnessiq/cli/linkedin/commands.py`: expose the new runtime parameter and any LinkedIn-specific credential configuration/show behavior.
- `harnessiq/agents/__init__.py`: export any new public LinkedIn/credential helper APIs if needed.
- `harnessiq/config/__init__.py`: export any new SDK-facing credential persistence helpers used by public callers.
- `README.md`: document the new credential-saving workflow and LinkedIn Drive-sync runtime parameter.
- `docs/linkedin-agent.md`: document Drive sync, duplicate guard behavior, and the credential-loading path.
- `artifacts/file_index.md`: update the meaningful repository layout if new provider or CLI folders are added.
- `tests/test_linkedin_cli.py`: add coverage for CLI persistence and runtime behavior around `save_to_google_drive` and credential setup.
- `tests/test_sdk_package.py`: verify any new public exports remain package-accessible.

Approach:
- Prefer extending the existing LinkedIn CLI/configure flow for the boolean runtime parameter, because runtime parameters are already the persistence contract for agent settings.
- If a user-facing credential CLI is needed, keep it explicit and repo-local, built on top of the same config persistence APIs from Ticket 1.
- Keep the SDK API narrow and unsurprising: callers should be able to save credentials once, load them later, and pass or omit `save_to_google_drive` as a first-class LinkedIn setting.
- Update docs only after the concrete public surface is stable.

Assumptions:
- Users should be able to configure Google Drive support without directly editing internal JSON files.
- The existing LinkedIn CLI configure/show/run pattern is the right public home for this feature unless a separate config command is needed.
- The package exports should stay minimal; helper APIs should be added only where they materially improve usability.

Acceptance Criteria:
- [ ] A public SDK path exists to save and load Google Drive credentials for LinkedIn usage.
- [ ] Users can set `save_to_google_drive` from both SDK and CLI, with a default of `false`.
- [ ] The LinkedIn CLI surfaces the persisted setting clearly and remains backward compatible when the setting is absent.
- [ ] Documentation reflects the new Drive-sync workflow and duplicate-protection behavior.
- [ ] Automated tests cover the new CLI/SDK configuration flows and package exports.

Verification Steps:
- Static analysis: manually review CLI/help text and public helper naming for consistency with existing command and config patterns.
- Type checking: no configured checker; validate public imports and helper signatures through tests and import execution.
- Unit tests: run `python -m pytest tests/test_linkedin_cli.py tests/test_sdk_package.py`.
- Integration and contract tests: run the broader CLI/agent/config suite that exercises LinkedIn configuration and package entrypoints.
- Smoke/manual verification: configure a temporary LinkedIn agent via CLI with `save_to_google_drive=true`, inspect the stored state with `linkedin show`, and confirm the persisted runtime parameter is rendered correctly.

Dependencies:
- Ticket 1.
- Ticket 2.

Drift Guard: This ticket must not expand the feature into unrelated provider management UX or broad CLI redesign. Its job is to expose the already-built capability cleanly through existing public surfaces and documentation.
