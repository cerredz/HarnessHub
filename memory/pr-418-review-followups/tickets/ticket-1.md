Title: Address PR #418 formalization review feedback

Issue URL: https://github.com/cerredz/HarnessHub/issues/419

Intent: Incorporate the owner's review feedback on PR #418 so the formalization-layer surface is packaged, documented, and indexed the way the repository expects before it is proposed again for merge.

Scope: Move the reusable formalization record/spec types out of the interface layer and into `harnessiq/shared/`, split `harnessiq/interfaces/formalization.py` into a package with one concern per file, expand the default identity/contract prose, add substantial explanatory comments, update the doc generator inputs as needed, regenerate generated docs, and update the relevant tests. This ticket does not add runtime formalization injection into `BaseAgent`.

Relevant Files:
- `harnessiq/shared/`: new shared formalization record/spec module plus export updates.
- `harnessiq/interfaces/formalization/`: new package structure for the formalization base classes.
- `harnessiq/interfaces/__init__.py`: public export surface updates.
- `tests/test_interfaces.py`: interface/export behavior coverage updates.
- `scripts/sync_repo_docs.py`: generated file-index support for the new formalization package shape.
- `artifacts/file_index.md`: regenerated file index.
- `README.md`: regenerated if changed by the docs sync script.
- `tests/test_docs_sync.py`: doc-generator regression coverage if the inventory surface changes.
- `memory/pr-418-review-followups/*`: planning, verification, and critique artifacts for this task.

Approach: Start from a clean branch off `main`, cherry-pick the original formalization PR commits, then refactor the feature into a package layout. Keep the shared data definitions dependency-light in `harnessiq/shared/`, keep `interfaces/__init__.py` as the stable public facade, and make the richer self-documentation live in the interface layer where the abstract behavior is defined. Update the docs generator rather than hand-editing generated artifacts.

Assumptions:
- "typed dicts" means the current shared formalization record/spec types, even though they are implemented as dataclasses.
- The target package path is `harnessiq/interfaces/formalization/`.
- The new PR should supersede PR #418 by targeting `main` with the original feature plus these review-driven changes.

Acceptance Criteria:
- [x] The shared formalization record/spec types live under `harnessiq/shared/`.
- [x] The interface layer uses a `harnessiq/interfaces/formalization/` package instead of one monolithic module.
- [x] Each formalization class/base concern lives in its own file with large top-of-file and class-level explanatory comments.
- [x] Default description text is materially richer and explains what, why, how, and intent for the injected formalization layers.
- [x] Generated docs are updated through `scripts/sync_repo_docs.py`, including file-index visibility for the formalization-layer package.
- [x] Targeted interface, shared, and docs-sync tests pass on the final branch.

Verification Steps:
- Run any configured static analysis; if none exists, document that fact.
- Run any configured type checker; if none exists, document that fact.
- Run targeted interface tests.
- Run targeted shared/import-boundary tests.
- Run docs-sync verification after regenerating outputs.
- Inspect the regenerated file index to confirm the formalization package is visible.

Dependencies: None.

Drift Guard: Do not wire formalization layers into `BaseAgent`, alter unrelated harness behavior, or fold in any of the unrelated dirty worktree changes present on the developer machine. Keep the work centered on the formalization package, shared type placement, generated docs, and the tests that guard those seams.
