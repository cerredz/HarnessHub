Self-critique findings:

- The first JSON generation pass used PowerShell `ConvertTo-Json`, which serialized the prompt body incorrectly for this environment. That would have left the bundled `prompt` field structurally wrong even though some substring-based tests still passed.
- The new prompt asset changed generated repository docs, and leaving that drift unresolved would have violated the file-index guidance and docs-sync contract tests.

Post-critique improvements applied:

- Replaced the prompt JSON generation with a deterministic Python serialization step that writes a plain string `prompt` field from the verbatim source artifact.
- Regenerated repository docs with `python scripts/sync_repo_docs.py`.
- Removed the stale legacy `artifacts/live_inventory.json` artifact so `python scripts/sync_repo_docs.py --check` returns cleanly.
