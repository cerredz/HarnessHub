Title: Add GCP health and credential CLI commands
Issue URL: https://github.com/cerredz/HarnessHub/issues/299
PR URL: https://github.com/cerredz/HarnessHub/pull/324

Intent:
Expose init-time validation and credential synchronization through the new `harnessiq gcloud` family so operators can prepare a project and sync secrets without importing provider classes.

Scope:
Add CLI handlers for health, auth/credential status, and credential sync/mutation flows. This ticket does not add the deployment operations commands such as build, deploy, schedule, execute, logs, or cost inspection.

Relevant Files:
- `harnessiq/cli/gcloud/commands.py`: Add the health and credential command handlers.
- `tests/test_gcloud_cli.py`: Extend CLI tests for health and credential flows.

Approach:
Keep handlers thin: construct `GcpContext` or `GcpAgentConfig`, delegate to `HealthProvider` and `CredentialBridge`, and emit structured JSON. Adapt the design doc's human-readable examples into repository-native JSON output while preserving the underlying command names and behaviors.

Assumptions:
- JSON responses are the default output contract even for health/status operations.
- `init` can share logic with the health and credential flows as long as the handler boundaries stay clear.
- The CLI should report bridge and health results without printing raw secrets.

Acceptance Criteria:
- [ ] The GCP CLI exposes health/auth validation commands.
- [ ] The GCP CLI exposes credential status, sync, set, and remove flows backed by `CredentialBridge`.
- [ ] `init` can perform prerequisite validation and credential sync orchestration using structured JSON output.
- [ ] CLI tests cover representative success and failure cases for these commands.

Verification Steps:
- Static analysis: No configured linter; manually review handler boundaries and JSON output shapes.
- Type checking: No configured type checker; keep handler signatures annotated and validate imports via tests.
- Unit tests: Run `pytest tests/test_gcloud_cli.py`.
- Integration and contract tests: Mock `GcpContext`, `HealthProvider`, and `CredentialBridge` interactions from the CLI.
- Smoke and manual verification: Run representative `harnessiq gcloud health ...` and `harnessiq gcloud credentials ...` help paths locally.

Dependencies:
Ticket 10, Ticket 11.

Drift Guard:
Do not add build/deploy/schedule/execute/logs/cost command handlers in this ticket. Keep the scope to prerequisite validation and credential management only.
