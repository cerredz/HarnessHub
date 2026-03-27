Critique review focused on whether the extracted Leads lifecycle services leave the CLI with clearer boundaries and better operator behavior.

Improvements applied:
- Added an explicit precondition check in `LeadsCliRunner.run()` so `harnessiq leads run` now raises a clear configure-first error when no persisted run configuration exists, instead of surfacing a lower-level store failure.
- Added a direct runner regression test covering the missing-configuration path to keep that operator-facing error stable.
- Removed leftover command-module imports from the pre-refactor implementation so the adapter layer stays aligned with the pure-wrapper pattern used by the other migrated CLIs.

Post-critique verification reran the ticket 6 compile step, the targeted builder/runner/leads CLI pytest suite, and the manual smoke run. All checks passed after the refinement.
