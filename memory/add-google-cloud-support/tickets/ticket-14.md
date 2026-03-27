Title: Add manifest-driven deployment specs for all harnesses
Issue URL: https://github.com/cerredz/HarnessHub/issues/301
PR URL: https://github.com/cerredz/HarnessHub/pull/342
Status: implemented, awaiting merge into `main`

Intent:
Make the GCP deployment system generic across every manifest-backed harness instead of binding the cloud path to one or two bespoke agents. This is the bridge between the provider/CLI service and full repository-wide cloud support.

Scope:
Extend the GCP configuration and provider layer so a deployment can be derived from harness manifests, harness profiles, model selection, and adapter arguments for any supported harness. This ticket should produce deterministic deploy specs and remote command metadata that the CLI and runtime wrapper can use.

Relevant Files:
- `harnessiq/providers/gcloud/config.py`: Extend the persisted deploy config with manifest/profile/model/runtime fields needed for generic deployment.
- `harnessiq/providers/gcloud/context.py`: Load and expose the richer config surface where needed.
- `harnessiq/providers/gcloud/manifest_support.py`: Add manifest/profile-to-deploy-spec resolution helpers.
- `tests/test_gcloud_manifest_support.py`: Verify deploy-spec derivation for multiple harness manifests.

Approach:
Use the existing harness-manifest and profile system as the source of truth instead of the design doc's `HARNESSIQ_AGENT_MODULE`-driven approach. A deployable GCP spec should be derived from manifest id, logical agent name, saved runtime/custom parameters, model selection, sink settings, and any harness-specific adapter arguments already captured in profile/run snapshot state. Keep the derivation deterministic and JSON-safe so it can be surfaced by the CLI.

Assumptions:
- All harnesses should flow through the generic manifest-backed CLI path for cloud execution, even if some still retain older specialized local commands.
- Persisted harness profile and run snapshot state contain enough information to reconstruct a deployable remote run request, though small config extensions may be needed.
- It is acceptable to adapt the design doc's agent-module registry idea into a manifest-driven registry because that matches the live codebase better.

Acceptance Criteria:
- [x] `GcpAgentConfig` can represent the manifest id, logical agent name, model selection, and remote run metadata needed for all harnesses.
- [x] A helper can derive a deployable spec for every built-in harness manifest without hard-coded per-harness branching as the primary path.
- [x] The deploy spec captures the remote command, env vars, and secret references needed by the future runtime wrapper.
- [x] Tests cover multiple manifests and assert deterministic deploy-spec output.

Verification Steps:
- Static analysis: No configured linter; manually review the manifest/profile resolution code for branching complexity.
- Type checking: No configured type checker; keep deploy-spec dataclasses and helper signatures fully annotated.
- Unit tests: Run `pytest tests/test_gcloud_manifest_support.py`.
- Integration and contract tests: Add tests that use real built-in manifests and fake profile data to exercise the derivation layer.
- Smoke and manual verification: Inspect a derived deploy spec for at least two built-in harnesses in a shell session.

Dependencies:
Ticket 12, Ticket 13.

Drift Guard:
Do not yet add the actual Cloud Run runtime wrapper or GCS synchronization in this ticket. The output here is the manifest-driven deployment specification, not the remote execution implementation itself.
