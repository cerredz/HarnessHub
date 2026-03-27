Critique review focused on whether the Prospecting extraction left a clean builder/runner boundary without introducing awkward cross-module coupling.

Improvements applied:
- Promoted the default Prospecting browser-tools factory string to a public runner constant so the command adapter no longer imports a private implementation detail just to preserve the CLI flag default/help text.
- Re-ran the Prospecting compile step, focused builder/runner/CLI pytest suite, and the manual smoke checks after the API-surface cleanup to confirm the command layer stayed behaviorally identical.

The resulting Prospecting CLI module now depends only on public builder/runner entrypoints and shared exported constants, which keeps the adapter boundary cleaner for the remaining legacy migrations.
