Title: Document the evaluation layer in generated repo artifacts

Intent:
Ensure the new evaluation architecture is discoverable in the repository’s canonical generated documentation, especially the requested file index.

Scope:
- Update the docs generator with evaluation package descriptions.
- Regenerate `artifacts/file_index.md`.
- Accept any other generated artifact changes caused by the same generator run.
- Do not manually edit generated outputs.

Relevant Files:
- `scripts/sync_repo_docs.py`: generated-doc source of truth.
- `artifacts/file_index.md`: generated file index.
- `README.md`: generated if changed by the sync script.

Approach:
Teach the generator about `harnessiq/evaluations/` as a live package, add focused descriptions for the new key files or subpackages, then rerun generation so the repository docs stay consistent with the source tree.

Assumptions:
- The file index should document the evaluation layer at the same level as other primary package surfaces.

Acceptance Criteria:
- [ ] The docs generator knows about the new evaluation package.
- [ ] `artifacts/file_index.md` mentions the evaluation layer and its responsibility.
- [ ] Generated outputs are in sync after the update.

Verification Steps:
- Run `python scripts/sync_repo_docs.py --check` after regeneration.

Dependencies:
- Ticket 1.

Drift Guard:
This ticket must not introduce hand-maintained documentation drift. All repo-artifact changes should flow through the generator.
