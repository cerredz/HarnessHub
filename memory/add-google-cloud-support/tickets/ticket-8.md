Title: Implement billing, logging, monitoring, and Cloud Storage providers
Issue URL: https://github.com/cerredz/HarnessHub/issues/295
PR URL: https://github.com/cerredz/HarnessHub/pull/313

Intent:
Complete the remaining operational provider surface needed for cost inspection, log access, failure alerting, and raw cloud storage operations.

Scope:
Add `BillingProvider`, `LoggingProvider`, `MonitoringProvider`, and `CloudStorageProvider`, plus focused tests. This ticket does not add `GcpContext`, the credential bridge, or any runtime memory-sync integration.

Relevant Files:
- `harnessiq/providers/gcloud/infra/billing.py`: Add cost-estimation helpers.
- `harnessiq/providers/gcloud/storage/__init__.py`: Export storage providers.
- `harnessiq/providers/gcloud/storage/cloud_storage.py`: Add Cloud Storage bucket/object helpers.
- `harnessiq/providers/gcloud/observability/__init__.py`: Export observability providers.
- `harnessiq/providers/gcloud/observability/logging.py`: Add Cloud Logging query helpers.
- `harnessiq/providers/gcloud/observability/monitoring.py`: Add notification-channel and alert-policy helpers.
- `tests/test_gcloud_observability_and_storage.py`: Verify provider behavior with mocked client calls.

Approach:
Implement each provider as a thin wrapper over the command-builder layer and shared client. `BillingProvider` should stay deterministic and config-driven. `CloudStorageProvider` in this ticket should expose bucket/object primitives only; later tickets can build higher-level harness-memory synchronization on top.

Assumptions:
- A pricing heuristic embedded in `BillingProvider` is acceptable as long as assumptions are explicit and tested.
- `LoggingProvider` can focus on Cloud Run Job log queries rather than a broader logging abstraction.
- `CloudStorageProvider` should stop at raw storage helpers for now.

Acceptance Criteria:
- [ ] Billing, logging, monitoring, and Cloud Storage providers are importable and exported cleanly.
- [ ] `BillingProvider` returns deterministic monthly cost estimates from config.
- [ ] `LoggingProvider` exposes basic log query helpers for Cloud Run Jobs.
- [ ] `MonitoringProvider` can create notification channels and failure alerts using the command-builder layer.
- [ ] `CloudStorageProvider` supports bucket creation plus object read/write/list/delete helpers.
- [ ] Tests cover representative provider flows and failure handling.

Verification Steps:
- Static analysis: No configured linter; manually review provider imports, rounding logic, and helper extraction.
- Type checking: No configured type checker; keep all provider methods and dataclasses fully annotated.
- Unit tests: Run `pytest tests/test_gcloud_observability_and_storage.py`.
- Integration and contract tests: Mock `GcloudClient` interactions and assert provider return values.
- Smoke and manual verification: Instantiate each provider with a fake client in a shell and inspect representative outputs.

Dependencies:
Ticket 3.

Drift Guard:
Do not add `GcpContext`, CLI handlers, or harness-memory synchronization in this ticket. The objective is only the raw operational provider surface.

