Critique review focused on whether the Research Sweep extraction preserved the less-common bound-credential path rather than only the explicit factory path.

Improvements applied:
- Added a direct runner regression test for the stored Serper credential binding fallback so the migration now covers both supported credential-resolution paths, not just `--serper-credentials-factory`.
- Re-ran the Research Sweep compile step, the focused builder/runner/CLI pytest suite, and the manual smoke check after adding that coverage. All checks remained green.

The runner boundary now has explicit coverage for the same credential-resolution behavior the legacy command module provided.
