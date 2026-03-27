## Self-Critique Findings

1. `credentials check` originally built a full `GcpContext` just to access `HealthProvider`.
   That created unnecessary coupling between a local auth diagnostic command and the entire GCP provider tree.

2. The initial smoke run showed that the local auth check path could crash when `gcloud` execution was unavailable.
   That is the exact failure mode the command is supposed to report, so the provider needed to degrade into structured failures instead of raising `FileNotFoundError`.

3. The CLI handlers repeated config-path rendering across multiple credential commands, which would make later output-shape changes drift-prone.

## Improvements Applied

- Reworked the local auth helper to construct `HealthProvider` directly from `GcpAgentConfig` and `GcloudClient` instead of going through `GcpContext`.
- Updated `HealthProvider` to treat missing `gcloud` executables the same way as other command failures for auth, API enablement, and Secret Manager access checks.
- Added regression coverage for the missing-`gcloud` path.
- Extracted `_config_path_for_agent()` so the credential commands share one config-path rendering helper.
- Re-ran the focused and broader GCP/CLI regression suites plus the smoke commands after the refinement.
