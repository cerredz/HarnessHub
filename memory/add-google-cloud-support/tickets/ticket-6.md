Title: Implement Scheduler and Secret Manager providers
Issue URL: https://github.com/cerredz/HarnessHub/issues/293
PR URL: https://github.com/cerredz/HarnessHub/pull/311

Intent:
Complete the remaining deployment-time provider surface so scheduling and runtime secret mutation can be composed into the shared context and CLI without embedding command logic there.

Scope:
Add the Scheduler and Secret Manager providers, plus focused provider tests. This ticket does not add `GcpContext`, CLI registration, or the credential bridge.

Relevant Files:
- `harnessiq/providers/gcloud/credentials/__init__.py`: Export credential-related providers.
- `harnessiq/providers/gcloud/credentials/secret_manager.py`: Add the Secret Manager provider.
- `harnessiq/providers/gcloud/deploy/scheduler.py`: Add the Cloud Scheduler provider.
- `tests/test_gcloud_schedule_and_secrets.py`: Verify provider behavior against mocked client calls.

Approach:
Keep both providers thin and command-builder-backed. `SecretManagerProvider` should own secret creation, metadata lookup, version addition, and rotation flows without ever embedding raw secret values in command strings. `SchedulerProvider` should own create/update/describe/pause/resume/run/delete flows.

Assumptions:
- Secret value transport will rely on `GcloudClient` stdin support.
- Scheduler provider behavior can stay generic and independent of manifest/runtime concerns.
- Tests should mock `GcloudClient` interactions only.

Acceptance Criteria:
- [ ] Scheduler and Secret Manager providers are importable and exported cleanly.
- [ ] `SchedulerProvider` supports create, update, describe, pause/resume, run-now, and delete flows.
- [ ] `SecretManagerProvider` supports create, rotate, describe, list, access metadata, and delete flows without leaking raw secret values in command strings.
- [ ] Provider tests verify command-builder usage and provider-side branching behavior.

Verification Steps:
- Static analysis: No configured linter; manually review provider imports and secret-handling paths.
- Type checking: No configured type checker; keep method signatures explicit and validate imports through tests.
- Unit tests: Run `pytest tests/test_gcloud_schedule_and_secrets.py`.
- Integration and contract tests: Mock `GcloudClient` interactions rather than live GCP.
- Smoke and manual verification: Instantiate both providers with a fake client in a shell and exercise representative methods.

Dependencies:
Ticket 4.

Drift Guard:
Do not add `GcpContext`, CLI handlers, or credential-bridge logic in this ticket. The goal is only the Scheduler and Secret Manager provider slice.

