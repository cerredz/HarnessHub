Title: Add GCP deployment and operations CLI commands
Issue URL: https://github.com/cerredz/HarnessHub/issues/300
PR URL: https://github.com/cerredz/HarnessHub/pull/334

Intent:
Expose the provider layer's deployment, scheduling, execution, logging, and cost operations through the new CLI family so the provider/CLI service is fully usable before deeper runtime integration lands.

Scope:
Add CLI handlers for build, deploy, schedule, execute, logs, and cost inspection. This ticket does not add manifest-driven deploy-spec derivation or the cloud runtime wrapper yet.

Relevant Files:
- `harnessiq/cli/gcloud/commands.py`: Add the deployment and operations command handlers.
- `tests/test_gcloud_cli.py`: Extend CLI tests for build/deploy/schedule/execute/logs/cost flows.

Approach:
Keep handlers thin and context-driven: load or construct `GcpContext`, delegate to the appropriate provider, and emit structured JSON. Preserve the repository's JSON-first CLI conventions while keeping command names close to the design doc.

Assumptions:
- The provider/CLI service is considered delivered once operators can initialize config, sync credentials, build, deploy, schedule, execute, inspect logs, and inspect cost through the CLI.
- Deeper manifest/runtime integration can remain a later ticket without blocking these operations from existing config data.

Acceptance Criteria:
- [ ] The GCP CLI exposes build, deploy, schedule, execute, logs, and cost commands.
- [ ] Each command delegates to the correct provider through `GcpContext`.
- [ ] JSON output includes the information needed to script these operations.
- [ ] CLI tests cover representative success and failure cases for these commands.

Verification Steps:
- Static analysis: No configured linter; manually review handler boundaries and import cleanliness.
- Type checking: No configured type checker; keep handler signatures annotated and validate imports via tests.
- Unit tests: Run `pytest tests/test_gcloud_cli.py`.
- Integration and contract tests: Mock provider calls from the CLI and assert emitted JSON payloads.
- Smoke and manual verification: Run representative `harnessiq gcloud ... --help` paths for the deployment commands locally.

Dependencies:
Ticket 11.

Drift Guard:
Do not add manifest-driven deployment spec derivation or the cloud runtime wrapper in this ticket. The goal is only the provider-backed CLI operations surface.
