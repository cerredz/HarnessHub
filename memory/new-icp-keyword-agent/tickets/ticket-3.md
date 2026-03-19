Title: Add SDK/CLI/public-surface wiring, documentation, and tests

Issue URL:
Blocked in local environment. `gh` cannot reach GitHub from this sandbox.

Intent:
Make the new Instagram discovery agent usable through the shipped package and command line, and document the contract so users can configure the agent, run it, and retrieve persisted emails through supported surfaces.

Scope:
- Register new CLI commands under the root parser.
- Expose the new agent and memory store through package exports.
- Add CLI retrieval commands such as `get-emails`.
- Update README and architectural artifact references.
- Extend package/CLI tests.

Relevant Files:
- `harnessiq/cli/instagram/__init__.py`: new CLI package export.
- `harnessiq/cli/instagram/commands.py`: new CLI commands.
- `harnessiq/cli/main.py`: root command registration.
- `harnessiq/agents/__init__.py`: public SDK export.
- `harnessiq/__init__.py`: top-level package export if required by existing policy.
- `README.md`: public usage documentation.
- `artifacts/file_index.md`: architecture reference update.
- `tests/test_instagram_cli.py`: CLI coverage.
- `tests/test_sdk_package.py`: packaging smoke coverage for the new public surface if needed.

Approach:
Mirror the existing `linkedin` and `outreach` CLI patterns: `prepare`, `configure`, `show`, `run`, plus a new retrieval command for persisted emails. Keep stdout JSON-first for automation. Wire the new agent into exports and documentation additively, then extend tests to lock down the public surface.

Assumptions:
- The CLI namespace should be `instagram`.
- `get-emails` should read persisted memory and not require a live agent process.
- The local environment may block GitHub issue/PR creation, but local code/documentation/test work remains in scope.

Acceptance Criteria:
- [ ] The root CLI registers the new Instagram command group.
- [ ] Users can prepare/configure/show/run the agent and retrieve persisted emails through CLI commands.
- [ ] The SDK public exports include the new agent and memory-store surface.
- [ ] README and architecture docs mention the new agent accurately.
- [ ] Tests cover CLI parser registration, run wiring, and persisted email retrieval.

Verification Steps:
- Run targeted Instagram CLI tests.
- Run package smoke tests if changes touch package exports.
- Manually inspect CLI help output and JSON payload shapes in tests where relevant.

Dependencies:
- Ticket 1.
- Ticket 2.

Drift Guard:
This ticket must not redesign existing CLI conventions or rework unrelated package exports. It should wire the new domain into the existing patterns with the minimum necessary surface area.
