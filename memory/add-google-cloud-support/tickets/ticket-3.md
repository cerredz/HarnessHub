Title: Add auth, IAM, storage, logging, and monitoring command builders
Issue URL: https://github.com/cerredz/HarnessHub/issues/290
PR URL: https://github.com/cerredz/HarnessHub/pull/307

Intent:
Expand the pure command-builder layer with the non-deployment control-plane commands that later support providers and health checks will rely on.

Scope:
Add pure command builders for auth, IAM, Cloud Storage, Cloud Logging, and Cloud Monitoring, plus focused unit tests. This ticket does not add deployment command builders, provider classes, or CLI entrypoints.

Relevant Files:
- `harnessiq/providers/gcloud/commands/auth.py`: Add auth and API-management builders.
- `harnessiq/providers/gcloud/commands/iam.py`: Add IAM builders.
- `harnessiq/providers/gcloud/commands/storage.py`: Add Cloud Storage builders.
- `harnessiq/providers/gcloud/commands/logging_.py`: Add Cloud Logging builders.
- `harnessiq/providers/gcloud/commands/monitoring.py`: Add Cloud Monitoring builders.
- `tests/test_gcloud_commands_support.py`: Verify the support-surface command builders.

Approach:
Keep the builders completely pure and align them with the design rule that destructive operations should be quiet, read operations should request deterministic formats, and the project flag should stay absent. Keep shared sequences factored into private helpers when the same flags appear multiple times.

Assumptions:
- Support-surface builders should exist before the corresponding providers so provider tickets can stay thin.
- The design docâ€™s builder split maps cleanly to this repositoryâ€™s testing style.
- Unit tests should assert exact command lists and omission behavior only.

Acceptance Criteria:
- [ ] Auth, IAM, storage, logging, and monitoring builder modules exist and are exported cleanly.
- [ ] Read operations in this surface emit deterministic `--format` flags.
- [ ] Destructive operations in this surface emit `--quiet` where appropriate.
- [ ] No builder in this ticket emits a project flag.
- [ ] Unit tests verify representative command shapes and defaults.

Verification Steps:
- Static analysis: No configured linter; manually review imports, naming, and exact command construction.
- Type checking: No configured type checker; keep signatures annotated and validate via test imports.
- Unit tests: Run `pytest tests/test_gcloud_commands_support.py`.
- Integration and contract tests: Not applicable; builders are pure.
- Smoke and manual verification: Import the new builder modules in a shell and print representative command lists.

Dependencies:
Ticket 2.

Drift Guard:
Do not add deployment builders, provider classes, CLI commands, or subprocess execution in this ticket. The deliverable is only the pure support-surface builder set.

