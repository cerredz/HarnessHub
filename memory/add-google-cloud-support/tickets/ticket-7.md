Title: Implement health and IAM providers
Issue URL: https://github.com/cerredz/HarnessHub/issues/294
PR URL: https://github.com/cerredz/HarnessHub/pull/312

Intent:
Add the first operational support providers so the deployment flow can validate prerequisites and manage service-account permissions without embedding that logic in the CLI.

Scope:
Add `HealthProvider` and `IamProvider`, plus focused tests. This ticket does not add billing, logging, monitoring, Cloud Storage, `GcpContext`, or CLI handlers.

Relevant Files:
- `harnessiq/providers/gcloud/health.py`: Add auth, API, and service-account validation logic.
- `harnessiq/providers/gcloud/infra/__init__.py`: Export infrastructure providers.
- `harnessiq/providers/gcloud/infra/iam.py`: Add service-account and IAM-role management.
- `tests/test_gcloud_health_and_iam.py`: Verify provider behavior and failure handling.

Approach:
Keep both providers thin and command-builder-backed. `HealthProvider` should validate `gcloud` presence, active CLI auth, ADC presence, required API enablement, and service-account Secret Manager access as separate checks. `IamProvider` should encapsulate service-account creation, inspection, and required-role binding logic.

Assumptions:
- The health checks should remain read-mostly and return structured results rather than mutating project state implicitly.
- The default compute service account fallback is acceptable when no dedicated service account is configured.
- Tests should mock `GcloudClient` rather than `subprocess`.

Acceptance Criteria:
- [ ] `HealthProvider` and `IamProvider` are importable and exported cleanly.
- [ ] `HealthProvider` distinguishes `gcloud` CLI auth from ADC and reports both separately.
- [ ] `HealthProvider` can verify required API enablement and service-account secret access.
- [ ] `IamProvider` can create/describe service accounts, list granted roles, and compute missing required roles.
- [ ] Tests cover success paths, missing-auth paths, and missing-role behavior.

Verification Steps:
- Static analysis: No configured linter; manually review provider imports and result-shape consistency.
- Type checking: No configured type checker; keep all provider methods and result dataclasses fully annotated.
- Unit tests: Run `pytest tests/test_gcloud_health_and_iam.py`.
- Integration and contract tests: Mock `GcloudClient` interactions and assert provider return values.
- Smoke and manual verification: Instantiate each provider with a fake client in a shell and inspect representative method outputs.

Dependencies:
Ticket 3.

Drift Guard:
Do not add billing, logging, monitoring, Cloud Storage, `GcpContext`, CLI handlers, or credential-bridge behavior in this ticket. The scope is only health validation and IAM management.

