Title: Add leads agent CLI, documentation, and repository exports

Issue URL: https://github.com/cerredz/HarnessHub/issues/153

Intent:
Make the new leads agent usable from the repo's public surfaces by adding CLI entrypoints, docs/examples, export wiring, and architecture index updates.

Scope:
This ticket adds CLI commands, docs, README coverage, package/toolset exports, and artifact index updates needed to expose the completed leads agent end to end.
This ticket does not add new runtime behavior or new provider functionality beyond wiring what earlier tickets produced.

Relevant Files:
- `harnessiq/cli/leads/__init__.py`: export leads CLI command helpers.
- `harnessiq/cli/leads/commands.py`: implement leads-agent CLI entrypoints and argument handling.
- `harnessiq/cli/main.py`: register the leads command group in the root CLI.
- `README.md`: document the new leads agent, Apollo provider, and usage examples.
- `docs/agent-runtime.md`: update runtime docs if the deterministic pruning contract changes public usage guidance.
- `docs/tools.md`: document the Apollo tool family if tool docs enumerate provider surfaces.
- `artifacts/file_index.md`: add the new agent/shared/CLI/provider locations to the architectural index.
- `harnessiq/agents/__init__.py`: ensure public exports are complete if not finalized earlier.

Approach:
Mirror the existing CLI organization used for `linkedin` and `exa_outreach`. Keep the CLI surface thin: parse config, construct the agent, run it, and display status/results without embedding agent logic in the CLI layer.
Update docs with one clear SDK example and one CLI example, and make sure the architecture index reflects the new meaningful directories and modules added by this feature.

Assumptions:
- The final agent/config shape is stable by the time this ticket begins.
- The repo's root CLI should expose a top-level `leads` command family rather than burying it under another namespace.
- README and docs should describe the deterministic pruning behavior at a high level but not duplicate implementation detail from the code.

Acceptance Criteria:
- [ ] The root CLI exposes a leads-agent command path that can construct and run the new harness.
- [ ] README/docs include Apollo-backed leads-agent usage examples.
- [ ] The architecture/file index reflects the new leads agent, shared module, CLI, and Apollo provider family.
- [ ] Public exports are consistent so SDK and CLI imports resolve cleanly.

Verification Steps:
- Static analysis: run the linter against the new CLI modules and touched docs-adjacent Python files.
- Type checking: run the type checker or validate annotations/import safety for the CLI code.
- Unit tests: run the leads CLI tests if added, plus any package export/import tests affected by the new modules.
- Integration and contract tests: run the CLI and package-level tests that verify root command registration and SDK exports.
- Smoke verification: invoke the leads CLI with test/fake inputs and confirm it constructs the agent and reports run status.

Dependencies:
- Ticket 1.
- Ticket 2.
- Ticket 3.
- Ticket 4.

Drift Guard:
This ticket must not reopen agent-core design or provider semantics. It is strictly the user-facing wiring, docs, and repository-surface completion pass after the core implementation exists.
