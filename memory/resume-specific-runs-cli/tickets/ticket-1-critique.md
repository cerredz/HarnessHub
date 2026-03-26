## Post-Critique Changes

- I looked specifically for backward-compatibility gaps in the new historical snapshot model and found one important edge case: legacy profiles only store `last_run`, so selecting a historical run could have reset runtime/custom parameters to empty defaults.
- I addressed that by hydrating legacy `last_run` snapshots from the profile's stored runtime/custom parameters when those fields are missing, and I added regression coverage for that loader path in `tests/test_harness_profiles.py`.
- I also tightened the CLI failure paths with explicit tests for `--run` without `--resume` and for requesting a non-existent run number, then reran the full focused regression suite plus doc sync.
