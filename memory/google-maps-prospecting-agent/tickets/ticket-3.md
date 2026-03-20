Title: Add SDK, CLI, documentation, and tests for prospecting

Issue URL: https://github.com/cerredz/HarnessHub/issues/194

Intent:
Expose the new prospecting harness as a first-class SDK and CLI feature, document the structural repo changes, and complete the test coverage needed for safe integration into the package.

Scope:
- Export the new agent and shared prospecting surfaces from public package modules.
- Add `harnessiq prospecting` CLI commands with `prepare`, `configure`, `show`, and `run`.
- Default the CLI run path to the Playwright-backed browser integration while allowing the model factory to be injected.
- Update `artifacts/file_index.md` for the new package structure and any meaningful reusable tool directories.
- Update package smoke tests and add CLI tests for the new command family.
- Do not redesign runtime semantics beyond what Tickets 1 and 2 require.

Relevant Files:
- `harnessiq/agents/__init__.py`: export the new agent and memory store types.
- `harnessiq/cli/main.py`: register prospecting commands.
- `harnessiq/cli/prospecting/commands.py`: new CLI flow.
- `harnessiq/cli/prospecting/__init__.py`: CLI package export.
- `artifacts/file_index.md`: update meaningful architecture sections.
- `README.md`: update agent/CLI docs if needed.
- `tests/test_sdk_package.py`: package/export coverage.
- `tests/test_prospecting_cli.py`: new CLI coverage.

Approach:
Follow the existing LinkedIn/Instagram/Outreach CLI pattern exactly: persist configuration into an agent memory folder, rehydrate with `from_memory()` for runs, and accept per-run sink injection via `AgentRuntimeConfig`. Keep stdout JSON structured. Update the architectural artifact only where the high-level package shape changes.

Assumptions:
- Tickets 1 and 2 are complete.
- The prospecting agent exposes a `from_memory()` constructor or equivalent CLI rehydration path.
- The prospecting agent’s ledger outputs already contain `qualified_leads`.

Acceptance Criteria:
- [ ] `harnessiq.agents` publicly exports the new prospecting agent surface.
- [ ] `harnessiq prospecting` CLI commands exist and follow existing conventions.
- [ ] The CLI supports persisted configuration and run-time model/browser injection required by the harness design.
- [ ] `artifacts/file_index.md` reflects the new meaningful package structure.
- [ ] SDK/package/CLI tests cover the new agent and pass.

Verification Steps:
- Run targeted CLI tests and package smoke tests.
- Manually inspect `harnessiq --help` and `harnessiq prospecting --help`.
- Verify a configured CLI run resolves the new agent and returns structured JSON.

Dependencies:
- Ticket 1.
- Ticket 2.

Drift Guard:
This ticket must not backdoor architectural changes that belong in the harness or tool tickets. Keep the work on public exposure, command wiring, documentation, and verification coverage.
