## Ticket 2 Post-Critique

Review findings:
- The wheel smoke test should import the CLI function explicitly instead of relying on the package attribute shape of `harnessiq.cli.main`.

Improvements applied:
- Tightened the packaging smoke test to import `main` directly from `harnessiq.cli.main`, making the assertion robust to package-level symbol exports.

Regression check:
- Re-ran `python -m unittest`.
- Result: pass
