## Critique Findings

- The initial test set proved config-driven model overrides and missing-model failure, but it did not prove that `derive_deploy_spec()` can recover model selection from persisted harness run state when the saved GCP config omits it.
- That fallback is part of the manifest/profile contract for generic cloud deployment, so leaving it untested would make the deploy-spec layer easier to regress during later runtime-wrapper work.

## Improvements Applied

- Added `test_derive_deploy_spec_uses_snapshot_model_selection_when_config_omits_one` to [tests/test_gcloud_manifest_support.py](C:/Users/422mi/HarnessHub/.worktrees/issue-301/tests/test_gcloud_manifest_support.py).
- The new test persists a real harness profile plus last-run snapshot, derives a deploy spec from a config that omits model fields, and asserts that the snapshot model selection and custom parameters flow through correctly.

## Post-Critique Verification

- Re-ran `git diff --check`.
- Re-ran `pytest tests/test_gcloud_manifest_support.py tests/test_gcloud_config.py`.
- Result: `13 passed in 0.28s`.
- Re-ran the manual smoke script for `research_sweep` and `instagram`; both still emitted the expected serialized memory path in the derived remote command payload.
