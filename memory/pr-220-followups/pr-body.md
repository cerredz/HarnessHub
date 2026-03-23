Title: Implement PR 220 follow-up refactors and Google Drive expansion

Issue URL:
https://github.com/cerredz/HarnessHub/issues/240

Intent:
Address the seven inline review comments left on merged PR `#220` by restructuring the platform CLI adapter layer, tightening config/manifest helper boundaries, expanding the Google Drive surface, and regenerating the file index/docs so the resulting code is cleaner without regressing existing platform behavior.

Scope:
This ticket refactors the platform CLI adapter implementation into a dedicated package with shared adapter abstractions and helper utilities; extracts harness-manifest helper logic into `harnessiq/utils/harness_manifest/`; lightly decomposes provider-credential catalog code inside `harnessiq/config/`; expands the Google Drive operation catalog, client, and tool layer with additional researched operations; updates generated docs and file-index context for the new packages; and updates regression tests.
This ticket does not rewrite unrelated harness runtime logic, change non-Google-Drive provider surfaces, or modify the userâ€™s unrelated dirty branch state.

Relevant Files:
- `harnessiq/cli/platform_commands.py` - Update imports and adapter loading to use the new adapter package layout.
- `harnessiq/cli/platform_adapters.py` - Convert the old monolith into a compatibility shim or remove it in favor of package-based adapters.
- `harnessiq/cli/adapters/` - New authoritative adapter package with one harness adapter per module plus shared base/context code.
- `harnessiq/cli/adapters/utils/` - New helper modules for adapter store loading, result serialization, JSON helpers, and factory helpers.
- `harnessiq/shared/exa_outreach.py` - Update `cli_adapter_path` to the new adapter location.
- `harnessiq/shared/instagram.py` - Update `cli_adapter_path` to the new adapter location.
- `harnessiq/shared/knowt.py` - Update `cli_adapter_path` to the new adapter location.
- `harnessiq/shared/leads.py` - Update `cli_adapter_path` to the new adapter location.
- `harnessiq/shared/linkedin.py` - Update `cli_adapter_path` to the new adapter location.
- `harnessiq/shared/prospecting.py` - Update `cli_adapter_path` to the new adapter location.
- `harnessiq/shared/harness_manifest.py` - Keep the public dataclasses here while delegating helper logic to utility modules.
- `harnessiq/shared/harness_manifests.py` - Keep the public registry API here while delegating helper logic to utility modules.
- `harnessiq/utils/harness_manifest/` - New helper package for manifest coercion, validation, and registry support.
- `harnessiq/utils/__init__.py` - Re-export any new manifest-helper utilities that should be package-visible.
- `harnessiq/config/provider_credentials.py` - Decompose the current monolith into a cleaner package or narrower modules while preserving imports.
- `harnessiq/config/provider_credentials/` - New focused provider-credential catalog/models/helpers package if introduced.
- `harnessiq/config/__init__.py` - Preserve the public config import surface after decomposition.
- `harnessiq/shared/google_drive.py` - Expand the operation catalog metadata.
- `harnessiq/providers/google_drive/client.py` - Implement additional Google Drive client operations that fit the tool layer.
- `harnessiq/providers/google_drive/operations.py` - Keep provider-layer operation metadata aligned with the shared catalog.
- `harnessiq/providers/google_drive/__init__.py` - Re-export any newly surfaced Google Drive provider APIs.
- `harnessiq/tools/google_drive/operations.py` - Extend the tool definition and handler dispatch for the new operations.
- `harnessiq/tools/google_drive/__init__.py` - Re-export the updated Google Drive tool factory surface.
- `scripts/sync_repo_docs.py` - Teach the generated file index to describe notable nested packages like the new CLI adapter package and manifest-helper utilities.
- `artifacts/file_index.md` - Regenerated artifact reflecting the new adapter/util package context.
- `artifacts/live_inventory.json` - Regenerated machine-readable inventory.
- `README.md` - Regenerated if the docs sync output changes.
- `tests/test_platform_cli.py` - Keep platform CLI behavior covered after the adapter move.
- `tests/test_harness_manifests.py` - Cover manifest helper extraction regressions.
- `tests/test_google_drive_provider.py` - Cover new Google Drive operations and tool dispatch.
- `tests/test_docs_sync.py` - Keep docs-sync and operation-count behavior aligned with live code.

Approach:
Create an authoritative `harnessiq/cli/adapters/` package composed of shared context/base modules plus one module per harness adapter, then move the helper functions into `harnessiq/cli/adapters/utils/` with short docstrings describing each helperâ€™s use case. Keep a thin compatibility surface only where it prevents unnecessary breakage. Extract manifest-coercion and registry helper logic into `harnessiq/utils/harness_manifest/` so `shared/harness_manifest.py` and `shared/harness_manifests.py` remain focused on public contracts. Decompose provider-credential catalog code into smaller modules without changing `harnessiq.config` imports. For Google Drive, add a researched set of high-value metadata/organization/permission operations that fit the existing JSON tool contract and provider client. Finally, rerun the repo docs generator so the file index explicitly describes the new nested packages and all generated artifacts stay synchronized.

Assumptions:
- One follow-up PR is required for the whole comment set.
- Official Google Drive API documentation is the source of truth for which future-useful operations to add.
- The new package layout should become the primary import path, but preserving compatibility is preferable when cheap.
- Helper docstrings satisfy the request for short comments under helper function signatures.
- Generated docs should be updated through `scripts/sync_repo_docs.py`, not by hand.

Acceptance Criteria:
- [ ] The platform CLI adapter implementation lives under `harnessiq/cli/adapters/` with a shared base/abstract adapter and one module per harness adapter.
- [ ] Adapter helper functions are moved into a `utils/` subpackage under the new adapter package and each helper has a short explanatory docstring.
- [ ] The config-layer cleanup reduces `provider_credentials` responsibility sprawl without breaking existing `harnessiq.config` imports.
- [ ] Harness-manifest coercion and registry helper functions move into a `harnessiq/utils/harness_manifest/` utility package with short explanatory docstrings.
- [ ] Existing manifest registry/coercion behavior remains correct and covered by tests.
- [ ] The Google Drive catalog and tool layer expose additional researched operations beyond the original three, and the new operations are wired through shared metadata, provider client behavior, and tool dispatch.
- [ ] The generated file index explicitly gives context for the new adapter and manifest-helper packages.
- [ ] Generated docs are in sync after the source changes.
- [ ] Relevant platform CLI, manifest, Google Drive, and docs-sync tests pass.

Verification Steps:
- Run `pytest tests/test_platform_cli.py tests/test_harness_manifests.py tests/test_google_drive_provider.py tests/test_docs_sync.py -q`.
- Run `python scripts/sync_repo_docs.py --check`.
- Run any narrower targeted tests added during implementation if new modules need extra regression coverage.
- Manually inspect the regenerated `artifacts/file_index.md` to confirm it explains the new nested packages instead of only listing them.

Dependencies:
- None.

Drift Guard:
This ticket must stay anchored to the seven review comments on PR `#220`. It should not turn into a general cleanup pass across the whole repository, a redesign of unrelated CLI commands, or a broad Google Drive product surface beyond operations that fit the existing provider/tool architecture. Structural refactors are allowed only where they directly serve the requested adapter, config, and manifest-helper decomposition.


## Quality Pipeline Results
# Ticket 1 Quality Results

## Stage 1 - Static Analysis

- No dedicated linter or standalone static-analysis tool is configured in `pyproject.toml` or `requirements.txt`.
- Applied manual static review to the changed Python modules while keeping the new helper packages and adapter modules fully type-annotated.

## Stage 2 - Type Checking

- No dedicated type checker such as `mypy` or `pyright` is configured in this repository.
- Preserved and added explicit annotations on the new adapter, manifest-helper, provider-credential, and Google Drive code paths to keep the structure self-describing.

## Stage 3 - Unit Tests

- Ran `pytest tests/test_platform_cli.py tests/test_harness_manifests.py tests/test_google_drive_provider.py tests/test_docs_sync.py -q`
- Result: `42 passed`

## Stage 4 - Integration and Contract Tests

- Ran `python -m unittest tests.test_docs_sync tests.test_google_drive_provider`
- Result: `Ran 33 tests in 4.710s - OK`
- These checks exercise the generated-doc workflow plus the Google Drive provider/tool integration paths under the stdlib test runner the repo also uses.

## Stage 5 - Smoke and Manual Verification

- Ran `python scripts/sync_repo_docs.py`
- Observed regenerated outputs for `README.md`, `artifacts/commands.md`, `artifacts/file_index.md`, and `artifacts/live_inventory.json`.
- Ran `python scripts/sync_repo_docs.py --check`
- Result: `Generated docs are in sync.`
- Manually inspected the regenerated file index and confirmed it now contains a `Focused Subpackages` section for:
  - `harnessiq/cli/adapters/`
  - `harnessiq/cli/adapters/utils/`
  - `harnessiq/config/provider_credentials/`
  - `harnessiq/utils/harness_manifest/`
- Manually confirmed the generated provider surface now reports `google_drive` with `10` operations, matching the expanded live catalog.


## Post-Critique Changes
# Ticket 1 Post-Critique Review

## Improvements Applied

- Tightened `GoogleDriveClient.list_files()` so non-positive `page_size` values fail fast locally instead of turning into invalid Drive API requests.
- Tightened `GoogleDriveClient.move_file()` so it never tries to remove the same parent folder it is adding as the destination.
- Added regression coverage for both edge cases in `tests/test_google_drive_provider.py`.

## Re-Verification After Critique

- Ran `pytest tests/test_platform_cli.py tests/test_harness_manifests.py tests/test_google_drive_provider.py tests/test_docs_sync.py -q`
- Result: `42 passed`
- Ran `python scripts/sync_repo_docs.py --check`
- Result: `Generated docs are in sync.`
- Ran `python -m unittest tests.test_docs_sync tests.test_google_drive_provider`
- Result: `Ran 33 tests in 4.710s - OK`

