Critique review focused on whether the new regression coverage still missed any meaningful CLI-surface behavior introduced by the builder/runner migrations.

Improvements applied:
- Added a Research Sweep CLI regression test for `configure --custom-param query=...` so the suite now covers the alternate query entrypoint that must still persist the query and reset progress after the architecture migration.
- Re-ran the full targeted CLI suite and focused smoke checks after adding that case. All targeted tests remained green.

This leaves the verification layer covering both shared helper behavior and the important per-command edge contracts without reopening the underlying architecture.
