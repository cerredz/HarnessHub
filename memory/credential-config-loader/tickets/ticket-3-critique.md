## Post-Critique Changes

Findings identified during self-review:

- `harnessiq config show --resolve` was initially allowed without `--agent`, which made the command contract ambiguous because the CLI had no single binding to resolve.
- That ambiguity would become worse as more agent bindings are added, so it was better to make the restriction explicit now rather than leave it as surprising behavior.

Changes made:

- Added explicit validation that `--resolve` requires `--agent`.
- Added a CLI test covering the new validation rule.
- Re-ran the config CLI tests, packaging smoke tests, and the full suite after the change.
