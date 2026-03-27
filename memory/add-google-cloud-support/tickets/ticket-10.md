Title: Implement a binding-aware credential bridge
Issue URL: https://github.com/cerredz/HarnessHub/issues/297
PR URL: https://github.com/cerredz/HarnessHub/pull/315

Intent:
Connect the existing repo-local HarnessIQ credential system to GCP Secret Manager so deployed jobs can inherit the same logical credential bindings that local harness runs already use.

Scope:
Add `CredentialBridge` and any supporting config-field extensions needed to register synced secrets on `GcpAgentConfig`, plus focused tests. This ticket should integrate with the existing `CredentialsConfigStore`, harness binding names, and manifest metadata rather than inventing a parallel local secret-discovery path.

Relevant Files:
- `harnessiq/providers/gcloud/credentials/bridge.py`: Add the binding-aware credential bridge and sync/status operations.
- `harnessiq/providers/gcloud/config.py`: Extend config fields as needed for registered secrets and harness deployment metadata.
- `tests/test_gcloud_credential_bridge.py`: Verify secret discovery, sync rules, and config registration behavior.

Approach:
Resolve local secrets through the existing binding system first. The bridge should use the logical harness profile and manifest metadata to determine what credentials exist locally, then map those resolved values into Secret Manager entries and Cloud Run secret references. Keep sync one-directional from local binding resolution to GCP and keep non-interactive mode deterministic.

Assumptions:
- The existing repo-local `.env` plus `CredentialsConfigStore` remains the source of truth for local harness credentials.
- Universal model credentials such as `ANTHROPIC_API_KEY` may not always be represented in the provider-family binding system and may require an explicit bridge rule or fallback.
- The bridge may need an internal registry keyed by harness manifest/provider families rather than the design docâ€™s `HARNESSIQ_AGENT_MODULE` approach.

Acceptance Criteria:
- [ ] `CredentialBridge` can report status for required and optional secrets without mutating remote state.
- [ ] `CredentialBridge` can sync missing local credentials into Secret Manager and register secret references on `GcpAgentConfig`.
- [ ] `CredentialBridge` respects interactive and non-interactive behavior for missing or already-present secrets.
- [ ] The bridge reuses existing HarnessIQ credential bindings instead of reading raw local process environment variables as its primary source.
- [ ] Tests cover universal credentials, harness/provider-family credentials, missing-binding failures, and config updates.

Verification Steps:
- Static analysis: No configured linter; manually review secret-handling code to avoid logging or persisting raw secret values.
- Type checking: No configured type checker; keep bridge types explicit and verify imports via tests.
- Unit tests: Run `pytest tests/test_gcloud_credential_bridge.py`.
- Integration and contract tests: Mock Secret Manager provider calls and credential-store resolution.
- Smoke and manual verification: Build a fake repo-local credential store and confirm `CredentialBridge.status()` and `sync(dry_run=True)` produce the expected JSON-safe status output.

Dependencies:
Ticket 9.

Drift Guard:
Do not add CLI parsing or Cloud Run runtime logic in this ticket. The bridge should stop at local binding resolution, Secret Manager synchronization, and GCP config registration.

