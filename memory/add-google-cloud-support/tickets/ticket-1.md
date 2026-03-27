Title: Introduce foundational GCP client and config primitives
Issue URL: https://github.com/cerredz/HarnessHub/issues/288
PR URL: https://github.com/cerredz/HarnessHub/pull/304

Intent:
Establish the shared execution and persistence base for every later GCP feature. This ticket creates the package-level primitives that make the rest of the provider layer testable, deterministic, and consistent with the repositoryâ€™s file-backed configuration style.

Scope:
Add the initial `harnessiq/providers/gcloud/` package with `__init__.py`, `base.py`, `client.py`, and `config.py`, plus focused unit tests for config persistence and command execution behavior. This ticket does not add CLI commands, provider implementations beyond the base class, or any command-builder modules.

Relevant Files:
- `harnessiq/providers/gcloud/__init__.py`: Export the new foundational GCP types and helpers.
- `harnessiq/providers/gcloud/base.py`: Add `BaseGcpProvider` with the shared `client` and `config` contract.
- `harnessiq/providers/gcloud/client.py`: Add `GcloudClient` and `GcloudError` for subprocess-backed `gcloud` execution.
- `harnessiq/providers/gcloud/config.py`: Add the persisted `GcpAgentConfig` model with load/save support.
- `tests/test_gcloud_client.py`: Verify command execution, project flag appending, JSON parsing, stdin handling, and error translation.
- `tests/test_gcloud_config.py`: Verify config normalization, round-trip persistence, and missing-config failure behavior.

Approach:
Use the existing repository pattern of explicit dataclasses and file-backed stores rather than introducing Google SDK dependencies or dynamic config loaders. `GcloudClient` should own subprocess invocation, universal `--project` handling, dry-run behavior, JSON decoding, and consistent error messages. `GcpAgentConfig` should persist under a deterministic path that matches the design intent while remaining easy to unit test.

Assumptions:
- The GCP provider layer will shell out to the installed `gcloud` CLI instead of using `google-cloud-*` libraries for control-plane operations.
- A dedicated GCP config file is acceptable even though the repository already has generic harness profile stores.
- No live GCP access is required for unit tests in this ticket.

Acceptance Criteria:
- [ ] `harnessiq/providers/gcloud/` exists as an importable package with clean exports.
- [ ] `BaseGcpProvider` exposes shared `client` and `config` properties without constructing clients internally.
- [ ] `GcloudClient` appends the configured project flag consistently and raises `GcloudError` on non-zero command failures.
- [ ] `GcloudClient` supports plain-text and JSON command execution helpers.
- [ ] `GcloudClient` supports dry-run previews without mutating remote state.
- [ ] `GcpAgentConfig` round-trips to disk and can be loaded by agent name.
- [ ] Unit tests cover success paths, failure paths, and config persistence behavior.

Verification Steps:
- Static analysis: No repository linter is configured; manually keep new code idiomatic and import-clean.
- Type checking: No repository type checker is configured; add precise annotations to all new code and validate imports by running the new tests.
- Unit tests: Run `pytest tests/test_gcloud_client.py tests/test_gcloud_config.py`.
- Integration and contract tests: Not applicable in this ticket; document the absence of live GCP integration coverage.
- Smoke and manual verification: Import the new package locally and instantiate a `GcpAgentConfig` plus `GcloudClient` in a short shell session.

Dependencies:
None.

Drift Guard:
Do not add CLI handlers, command-builder modules, or concrete provider classes in this ticket. The goal is only to create the stable base layer that later tickets can compose; any deployment logic, auth validation, or credential syncing belongs in later tickets.

