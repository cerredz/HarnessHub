Initial critique findings:
- The first implementation pass left the LinkedIn harness with several stale imports and helper functions after moving the memory/runtime-definition layer into `harnessiq/shared/linkedin.py`.
- Leaving those remnants in place would weaken the architectural goal of the ticket because the harness would still read like it owns the moved definition surface.

Post-critique improvements implemented:
- Removed stale LinkedIn harness imports for constants that now only belong to the shared module.
- Removed now-unused LinkedIn harness helper functions that were only relevant to the in-module memory-store implementation before extraction.
- Re-ran the targeted import smoke and test suite to confirm the cleanup did not regress behavior.

Residual risks reviewed:
- `test_sdk_package.py` remains environment-blocked in this repo-local runner because `setuptools` is unavailable to `Scripts\pytest.exe`; this is not introduced by the ticket diff.
- The remaining tickets will need to preserve the same package-surface discipline as provider definitions move into shared modules.
