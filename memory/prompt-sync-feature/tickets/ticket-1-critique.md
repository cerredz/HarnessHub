## Self-Critique

### Findings
- The registry generator originally duplicated its serialization path in both `write_registry()` and `main()`. That is a small maintainability risk in a determinism-sensitive script because future formatting changes could accidentally update one path but not the other.
- The original generator tests validated `build_registry()` and `--check`, but they did not directly verify that the write path emits the same rendered payload to disk.

### Improvements Applied
- Added `render_registry()` as the single rendering path used by both `write_registry()` and `main()`.
- Added a direct write-path test that verifies `write_registry()` persists exactly the rendered content for a temporary prompt directory.

### Residual Risk
- The migrated artifact-backed `harnessiq.master_prompts` API still reflects repository-local files. That is acceptable for this ticket because the remaining Prompt Sync tickets replace the legacy bundled workflow entirely, but distribution behavior outside the repository will need to be resolved by the new sync runtime rather than by preserving the old packaged JSON model.
