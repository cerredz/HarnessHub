## Critique Findings

- The initial wrapper only guaranteed sync-back after the adapter run path had started.
- That left a gap where failures during deploy-spec derivation, context construction, or model resolution could skip the upload pass even though the wrapper had already downloaded and potentially mutated local state.
- It also risked masking the primary execution failure if upload failed afterwards.

## Improvements Applied

- Expanded the guarded execution window in [runtime.py](C:/Users/422mi/HarnessHub/.worktrees/issue-302/harnessiq/providers/gcloud/runtime.py) so sync-back is attempted for the full post-download workflow, not just the adapter invocation.
- Added explicit separation between execution errors and sync-back errors so successful runs still surface upload failures, while failed runs keep the original execution exception as the primary error.
- Added `test_run_runtime_syncs_back_when_model_resolution_fails` to [tests/test_gcloud_runtime.py](C:/Users/422mi/HarnessHub/.worktrees/issue-302/tests/test_gcloud_runtime.py) to prove upload still happens when failure occurs before adapter execution.

## Post-Critique Verification

- Re-ran `git diff --check`.
- Re-ran `pytest tests/test_gcloud_runtime.py`.
- Result: `4 passed in 0.30s`.
- Re-ran the inline smoke script and confirmed the download/upload ordering remained `download -> upload` with a completed payload.
