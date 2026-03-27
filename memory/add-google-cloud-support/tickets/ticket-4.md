Title: Add Cloud Run, Scheduler, Artifact Registry, and Secret Manager command builders
Issue URL: https://github.com/cerredz/HarnessHub/issues/291

Intent:
Finish the pure command-builder layer for the deployment-time and secret-management surfaces so the executable provider tickets can stay focused on orchestration instead of list construction.

Scope:
Add pure command builders for Cloud Run jobs, Cloud Scheduler, Artifact Registry, and Secret Manager, plus focused unit tests. This ticket does not add provider classes, `GcpContext`, or CLI handlers.

Relevant Files:
- `harnessiq/providers/gcloud/commands/run_jobs.py`: Add Cloud Run Job builders.
- `harnessiq/providers/gcloud/commands/scheduler.py`: Add Cloud Scheduler builders.
- `harnessiq/providers/gcloud/commands/artifact_registry.py`: Add Artifact Registry builders.
- `harnessiq/providers/gcloud/commands/secret_manager.py`: Add Secret Manager builders.
- `tests/test_gcloud_commands_deploy.py`: Verify deployment-surface command builders.

Approach:
Keep the builders completely pure and align them with the design invariants: shared private helpers for repeated flag sequences, no project flag emission, omission of default flags where possible, and deterministic output formatting on read operations.

Assumptions:
- The deployment builder surface is large but cohesive enough for one pure-builder ticket.
- Secret value transport concerns stop at command-list construction here; provider tickets will handle stdin/value passing.
- The deploy-surface builders should mirror the design doc closely because later provider tests will depend on their exact behavior.

Acceptance Criteria:
- [ ] Cloud Run, Scheduler, Artifact Registry, and Secret Manager builder modules exist and are exported cleanly.
- [ ] Shared deployment flag sequences are factored so create/update behavior does not drift.
- [ ] Secret-manager builders support stdin-driven version creation without placing secret values in the command list.
- [ ] No builder in this ticket emits a project flag.
- [ ] Unit tests verify representative deployment command shapes and omission behavior.

Verification Steps:
- Static analysis: No configured linter; manually review imports, helper extraction, and command formatting.
- Type checking: No configured type checker; keep signatures annotated and validate via test imports.
- Unit tests: Run `pytest tests/test_gcloud_commands_deploy.py`.
- Integration and contract tests: Not applicable; builders are pure.
- Smoke and manual verification: Import the deployment builder modules in a shell and inspect representative command lists.

Dependencies:
Ticket 2.

Drift Guard:
Do not add provider classes, CLI handlers, or subprocess execution in this ticket. The deliverable is only the pure deployment and secret-management builder set.

