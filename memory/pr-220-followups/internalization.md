# PR 220 Followups Internalization

### 1a: Structural Survey

HarnessHub is a Python 3.11+ SDK package (`pyproject.toml`) organized around a live source tree in `harnessiq/`, generated repository artifacts in `artifacts/`, supporting docs in `docs/`, repo tooling in `scripts/`, and test coverage in `tests/`. The authoritative runtime code is the `harnessiq/` package; generated directories like `build/`, `src/`, and caches are explicitly treated as non-authoritative by the generated file index.

The runtime architecture follows a layered pattern. `harnessiq/shared/` owns declarative metadata, typed dataclasses, manifest definitions, memory-store models, and cross-cutting constants. `harnessiq/agents/` owns orchestration logic for concrete harnesses. `harnessiq/providers/` wraps external systems and HTTP clients. `harnessiq/tools/` exposes deterministic tool factories and request surfaces over those providers. `harnessiq/cli/` builds an argparse CLI around harness flows and repo operations. `harnessiq/utils/` carries general runtime infrastructure such as ledger handling, sink rendering, run storage, and agent-instance storage.

The CLI already has a platform-first layer centered on `harnessiq/cli/platform_commands.py` and a monolithic `harnessiq/cli/platform_adapters.py`. `platform_commands.py` generates `prepare`, `show`, `run`, `inspect`, and `credentials` subcommands from manifest metadata, then loads a manifest-declared adapter factory. `platform_adapters.py` currently mixes the shared adapter context/protocol, the default base adapter, every harness-specific adapter implementation, and a flat set of private helper functions for store loading, result serialization, JSON reads, and factory resolution.

The config layer is partly decomposed already. `harnessiq/config/harness_profiles.py` cleanly owns persisted harness profile state. `harnessiq/config/loader.py` owns `.env` loading. `harnessiq/config/models.py` owns a base TypedDict. `harnessiq/config/provider_credentials.py`, however, still combines credential field/spec models, redaction logic, dataclass builders, and the full provider catalog in one file.

The manifest layer is similarly close to the requested shape but not fully decomposed. `harnessiq/shared/harness_manifest.py` correctly owns the public manifest dataclasses, yet it also owns coercion and validation helper functions. `harnessiq/shared/harness_manifests.py` correctly owns the registry API, but it also owns lower-level registry mutation and entrypoint-loading helpers inline.

The Google Drive surface is split across `harnessiq/shared/google_drive.py` for credentials and operation catalog metadata, `harnessiq/providers/google_drive/client.py` for Drive HTTP behavior, and `harnessiq/tools/google_drive/operations.py` for the tool-layer request surface. Today it exposes only three operations: `ensure_folder`, `find_file`, and `upsert_json_file`.

Documentation is generated, not hand-maintained. `scripts/sync_repo_docs.py` inspects the live tree and ASTs to regenerate `README.md`, `artifacts/file_index.md`, `artifacts/commands.md`, and `artifacts/live_inventory.json`. The file index currently explains top-level packages and key files, but it does not have a focused way to describe important nested subpackages such as a future CLI adapter package or a manifest-helper utility package.

Testing is mixed but consistent enough. The repo uses both `pytest`-style tests and `unittest` classes. Relevant regression coverage already exists in `tests/test_platform_cli.py`, `tests/test_harness_manifests.py`, `tests/test_google_drive_provider.py`, and `tests/test_docs_sync.py`. The existing tests assert public behavior, not internal implementation details, which is the right convention to preserve during structural refactors.

Notable inconsistencies with the current architecture:

- `harnessiq/cli/platform_adapters.py` is much more monolithic than the surrounding CLI package layout.
- `harnessiq/config/provider_credentials.py` combines models, catalog constants, and builder helpers in one module.
- `harnessiq/shared/harness_manifest.py` and `harnessiq/shared/harness_manifests.py` mix public manifest/registry contracts with lower-level helper logic.
- The generated file index can show child package names but does not yet explain why a notable nested package exists.

### 1b: Task Cross-Reference

The user asked to sequentially implement the review comments they left on merged PR `#220` and then open one new PR into `main`. The relevant inline review comments resolve to seven concrete change requests:

1. Refactor `harnessiq/cli/platform_adapters.py` into a `harnessiq/cli/adapters/` package with one adapter class per harness, plus a shared base/abstract adapter class.
Relevant files: `harnessiq/cli/platform_commands.py`, `harnessiq/cli/platform_adapters.py`, new `harnessiq/cli/adapters/` modules, harness manifest declarations in `harnessiq/shared/*.py`, generated docs via `scripts/sync_repo_docs.py`, `artifacts/file_index.md`, `artifacts/live_inventory.json`, and tests in `tests/test_platform_cli.py`.

2. Move the flat helper functions from the adapter module into a `utils/` package under the new CLI adapter package.
Relevant files: new `harnessiq/cli/adapters/utils/` modules, adapter classes that import them, `harnessiq/cli/platform_commands.py`, generated file index content, and platform CLI tests.

3. Add short explanatory comments directly under the relevant helper function signatures.
Relevant files: new helper modules under `harnessiq/cli/adapters/utils/` plus the manifest-helper utility modules requested below. The cleanest codebase-compatible implementation is concise docstrings on each helper, because the repo already uses docstrings as the primary inline explanation mechanism.

4. Clean up config-folder organization so each file has a tighter responsibility boundary.
Relevant files: `harnessiq/config/provider_credentials.py`, `harnessiq/config/__init__.py`, and new focused submodules or a subpackage under `harnessiq/config/` that preserve the existing public import surface used by `platform_commands.py` and tests.

5. Expand the Google Drive catalog and tool layer based on researched, future-useful Drive operations.
Relevant files: `harnessiq/shared/google_drive.py`, `harnessiq/providers/google_drive/client.py`, `harnessiq/providers/google_drive/operations.py`, `harnessiq/tools/google_drive/operations.py`, `harnessiq/tools/google_drive/__init__.py`, possibly `harnessiq/providers/google_drive/__init__.py`, generated docs, and tests in `tests/test_google_drive_provider.py` and `tests/test_docs_sync.py`.

6. Extract helper functions from `harnessiq/shared/harness_manifest.py` into a utility location and add short explanatory comments under each helper function signature.
Relevant files: `harnessiq/shared/harness_manifest.py`, new `harnessiq/utils/harness_manifest/` modules, `harnessiq/utils/__init__.py`, and manifest tests.

7. Apply the same decomposition to helper functions in `harnessiq/shared/harness_manifests.py`, potentially using a `harness_manifest` utility subfolder.
Relevant files: `harnessiq/shared/harness_manifests.py`, new `harnessiq/utils/harness_manifest/` modules, `harnessiq/shared/__init__.py`, and manifest tests.

The blast radius is moderate but well-bounded. The runtime behavior that must be preserved is:

- Platform CLI commands still resolve manifests, profiles, and credential bindings the same way.
- Manifest coercion, registry lookup, and entrypoint loading continue to raise the same kinds of errors for invalid input.
- Existing Google Drive operations remain backwards compatible while new ones are added.
- `harnessiq.config` and `harnessiq.shared` remain stable public import surfaces for the rest of the package and tests.
- Generated docs stay in sync with live source after the refactor.

Because the user asked for one follow-up PR, the implementation should group the seven review comments into one coherent branch/PR while still handling them sequentially inside the change set.

### 1c: Assumption & Risk Inventory

- Assumption: the user wants all seven PR comments implemented in a single follow-up PR, not one PR per comment. This follows the explicit request for “a new pull request” after implementation.
- Assumption: preserving public import compatibility is desirable even when code moves. A thin compatibility shim is acceptable if it keeps external callers from breaking while the new package structure becomes authoritative.
- Assumption: “add a 1-2 line comment right below each function sig” can be satisfied with concise helper docstrings, because this repo already uses docstrings rather than standalone inline comment blocks for function-level explanations.
- Assumption: “clean it up and decompose it a little bit” for the config folder means targeted decomposition around `provider_credentials`, not a repo-wide rewrite of all config modules.
- Assumption: the Google Drive expansion should favor high-value, JSON-friendly operations that fit the existing tool architecture instead of binary-download workflows that would force a different tool contract.

- Risk: changing manifest `cli_adapter_path` strings and platform CLI imports could break runtime loading if any new module path is mistyped.
- Risk: moving helper functions out of `shared/harness_manifest.py` and `shared/harness_manifests.py` could subtly change coercion/validation behavior or error text if not covered by tests.
- Risk: adding a CLI adapter package without generated-doc updates would leave `artifacts/file_index.md` out of sync and fail the docs-sync workflow.
- Risk: Google Drive tool expansion touches shared catalog metadata, provider client behavior, and tool request parsing at once; weak tests would make regressions easy.
- Risk: the root checkout is dirty on a user branch, so all writes must stay inside the isolated `pr-220-followups` worktree to avoid trampling unrelated user work.

Phase 1 complete.
