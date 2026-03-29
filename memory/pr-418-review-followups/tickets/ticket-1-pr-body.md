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


## Quality Pipeline Results
# Quality Pipeline: Ticket 1

## Stage 1: Static Analysis

No project linter or standalone static-analysis command is configured in `pyproject.toml`.
Applied the repository's existing Python style manually while refactoring the
formalization package and shared record module.

Result: pass

## Stage 2: Type Checking

No configured type-checker entrypoint is present in `pyproject.toml`.
Maintained explicit type annotations on the new shared records and abstract
formalization interfaces.

Result: pass

## Stage 3: Unit Tests

Commands:

- `python -m pytest tests/test_interfaces.py`
- `python -m pytest tests/test_docs_sync.py`

Observed:

- `tests/test_interfaces.py`: 21 passed
- `tests/test_docs_sync.py`: 13 passed
- After the punctuation normalization follow-up: `python -m pytest tests/test_interfaces.py tests/test_docs_sync.py` -> 34 passed

Result: pass

## Stage 4: Integration & Contract Tests

Commands:

- `python -m pytest tests/test_output_sinks.py tests/test_toolset_dynamic_selector.py`
- `python -m pytest tests/test_harness_manifests.py tests/test_validated_shared.py tests/test_tool_selection_shared.py`

Observed:

- `tests/test_output_sinks.py tests/test_toolset_dynamic_selector.py`: 26 passed
- `tests/test_harness_manifests.py tests/test_validated_shared.py tests/test_tool_selection_shared.py`: 22 passed

Result: pass

## Stage 5: Smoke & Manual Verification

Manual checks:

- Ran `python scripts/sync_repo_docs.py` and confirmed `artifacts/file_index.md`
  regenerated with `harnessiq/interfaces/` and
  `harnessiq/interfaces/formalization/` entries.
- Ran `python -c "import harnessiq.interfaces as i; import harnessiq.shared as s; print('ok', hasattr(i, 'BaseFormalizationLayer'), hasattr(s, 'FieldSpec'))"`
  and confirmed the refactored interface package and shared exports load
  together without circular-import failure.
- Confirmed the old monolithic `harnessiq/interfaces/formalization.py` path was
  replaced by the package directory with one module per formalization base.

Result: pass


## Post-Critique Changes
# Post-Critique: Ticket 1

## Findings

1. The user explicitly asked for the identity prose to be a single string, but
   the test suite did not protect that requirement. A future refactor could
   have reintroduced the labeled `What:` / `Why:` / `How:` / `Intent:` format
   without failing tests.
2. The copied ticket artifact had mojibake in a few workflow notes, which would
   have leaked into the new PR body if left unchanged.

## Improvements Implemented

- Added regression assertions in `tests/test_interfaces.py` to ensure the
  contract-layer identity prose stays in one continuous string rather than
  reverting to labeled sections.
- Normalized the ticket wording to plain ASCII and marked the acceptance
  criteria complete so the PR body reflects the final state of the work.

## Re-Verification

- `python -m pytest tests/test_interfaces.py tests/test_docs_sync.py`
- `python -m pytest tests/test_output_sinks.py tests/test_toolset_dynamic_selector.py`
- `python -m pytest tests/test_harness_manifests.py tests/test_validated_shared.py tests/test_tool_selection_shared.py`

All commands passed after the critique changes.

