Title: Implement Artifact Registry and Cloud Run providers
Issue URL: https://github.com/cerredz/HarnessHub/issues/292
PR URL: https://github.com/cerredz/HarnessHub/pull/310

Intent:
Deliver the first executable deployment slice on top of the builder layer so HarnessIQ can build container images and create or update Cloud Run Jobs through a thin provider API.

Scope:
Add the Artifact Registry and Cloud Run providers, plus focused provider tests. This ticket does not add the Scheduler provider, Secret Manager provider, `GcpContext`, CLI code, or the credential bridge.

Relevant Files:
- `harnessiq/providers/gcloud/deploy/__init__.py`: Export deploy providers.
- `harnessiq/providers/gcloud/deploy/artifact_registry.py`: Add the Artifact Registry provider.
- `harnessiq/providers/gcloud/deploy/cloud_run.py`: Add the Cloud Run Jobs provider.
- `tests/test_gcloud_deploy_providers.py`: Verify provider behavior against mocked client calls.

Approach:
Keep the providers thin and command-builder-backed. Translate `GcpAgentConfig` into command-builder inputs, call `GcloudClient`, and normalize simple return values. Preserve idempotency around Cloud Run create-versus-update behavior and repository existence checks.

Assumptions:
- Artifact Registry build submission can rely on `gcloud builds submit` rather than local Docker.
- Cloud Run provider methods can use command builders for all command-list construction.
- Tests should mock `GcloudClient` instead of subprocess directly.

Acceptance Criteria:
- [ ] Artifact Registry and Cloud Run providers are importable and exported cleanly.
- [ ] Artifact Registry provider supports repository existence checks and build/push flows.
- [ ] Cloud Run provider supports create, update, deploy, execute, describe, and execution-listing flows.
- [ ] Provider tests verify command-builder usage and create-versus-update branching behavior.

Verification Steps:
- Static analysis: No configured linter; manually review provider imports, branch logic, and config translation.
- Type checking: No configured type checker; keep provider method contracts annotated and validate them via tests.
- Unit tests: Run `pytest tests/test_gcloud_deploy_providers.py`.
- Integration and contract tests: Mock `GcloudClient` interactions rather than live GCP.
- Smoke and manual verification: Instantiate providers with a fake client in a shell and exercise representative `deploy_job()` paths.

Dependencies:
Ticket 4.

Drift Guard:
Do not add the Scheduler provider, Secret Manager provider, `GcpContext`, CLI handlers, or credential syncing in this ticket. The goal is only the Artifact Registry and Cloud Run provider slice.

