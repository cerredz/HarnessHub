### 1a: Structural Survey

The repository contract in [artifacts/file_index.md](/C:/Users/422mi/HarnessHub/artifacts/file_index.md) states that `harnessiq/` is the only authoritative runtime source tree. The architecture is layered:

- `harnessiq/agents/` owns orchestration and the long-running harness runtime.
- `harnessiq/tools/` owns deterministic operations and provider-backed tool factories.
- `harnessiq/providers/` wraps external service clients and operation catalogs.
- `harnessiq/shared/` owns reusable DTOs, manifests, validated types, and cross-cutting runtime models.
- `harnessiq/interfaces/` exposes the SDK-facing dependency seams used across providers, tools, integrations, and utilities.
- `tests/` is pytest/unittest-first and is the authoritative verification layer for public behavior and generated docs.

The current formalization work from PR #418 lives in a monolithic file at `harnessiq/interfaces/formalization.py` on branch `formalization-layer-interfaces-pr`. It combines four concerns in one module:

1. shared formalization records/specs (`LayerRuleRecord`, `FieldSpec`, `StageSpec`, etc.),
2. the universal `BaseFormalizationLayer` abstraction,
3. seven typed abstract bases (`BaseContractLayer`, `BaseArtifactLayer`, `BaseHookLayer`, `BaseStageLayer`, `BaseRoleLayer`, `BaseStateLayer`, `BaseToolContributionLayer`),
4. helper formatting and default self-documentation behavior.

The public SDK surface is centralized in [harnessiq/interfaces/__init__.py](/C:/Users/422mi/HarnessHub/harnessiq/interfaces/__init__.py). The shared package currently uses a lazy `__getattr__` export pattern in [harnessiq/shared/__init__.py](/C:/Users/422mi/HarnessHub/harnessiq/shared/__init__.py) to avoid import cycles between `interfaces`, `shared`, and provider/tool modules.

The file-index artifact is generator-owned by [scripts/sync_repo_docs.py](/C:/Users/422mi/HarnessHub/scripts/sync_repo_docs.py). It builds the package tables from static lists plus AST-derived inventory. If review feedback wants formalization-layer package visibility in the file index, the correct path is to update the generator inputs or inventory-producing code and rerun the generator, not hand-edit `artifacts/file_index.md`.

Relevant tests:

- [tests/test_interfaces.py](/C:/Users/422mi/HarnessHub/tests/test_interfaces.py): public interface exports and formalization behavior.
- [tests/test_docs_sync.py](/C:/Users/422mi/HarnessHub/tests/test_docs_sync.py): generated-doc sync and repository-doc inventory behavior.
- [tests/test_output_sinks.py](/C:/Users/422mi/HarnessHub/tests/test_output_sinks.py), [tests/test_toolset_dynamic_selector.py](/C:/Users/422mi/HarnessHub/tests/test_toolset_dynamic_selector.py), [tests/test_harness_manifests.py](/C:/Users/422mi/HarnessHub/tests/test_harness_manifests.py), [tests/test_validated_shared.py](/C:/Users/422mi/HarnessHub/tests/test_validated_shared.py), and [tests/test_tool_selection_shared.py](/C:/Users/422mi/HarnessHub/tests/test_tool_selection_shared.py): adjacent contract/import coverage that guards the shared/interface boundary.

Conventions that matter for this task:

- Keep `interfaces/` as the public SDK seam.
- Put reusable cross-layer types in `shared/` when they are not specific to one package.
- Preserve the public import surface from `harnessiq.interfaces`.
- Treat generated docs as generator outputs.
- Prefer explicit, high-signal documentation and tests over implicit behavior.

### 1b: Task Cross-Reference

The user asked to use the review comments on PR #418 as the spec. Those comments require five concrete changes:

1. Move the shared formalization records/specs into `harnessiq/shared/`.
Mapped files:
- `harnessiq/interfaces/formalization.py` currently owns those records and must be split.
- `harnessiq/shared/` needs a new formalization data module and corresponding exports.
- `harnessiq/interfaces/__init__.py` will need to re-export from the new package layout.

2. Replace the single-file interface module with a package under `harnessiq/interfaces/formalization/`.
Mapped files:
- Delete `harnessiq/interfaces/formalization.py`.
- Add `harnessiq/interfaces/formalization/__init__.py`.
- Add one file per formalization base class or concern.
- Update imports in `harnessiq/interfaces/__init__.py` and tests.

3. Significantly enhance default descriptions so they explain what, why, how, and intent.
Mapped files:
- `harnessiq/interfaces/formalization/base.py` or equivalent shared base implementation.
- Possibly each typed base file if they own type-specific identity/contract rendering.
- Tests need to assert richer default prose at least for representative classes.

4. Add extensive multi-line documentation comments at the top of each file and around each class.
Mapped files:
- every new file under `harnessiq/interfaces/formalization/`.
- the new shared formalization records module under `harnessiq/shared/`.

5. Add the formalization-layer information to the generated file index.
Mapped files:
- `scripts/sync_repo_docs.py` for focused subpackage or key-file visibility.
- regenerated `artifacts/file_index.md`.
- likely `README.md` if the generator output changes there.
- `tests/test_docs_sync.py` if additional assertions are warranted.

Existing behavior that must be preserved:

- `from harnessiq import interfaces` and `from harnessiq.interfaces import ...` must continue to work.
- the formalization feature remains interface-only; this follow-up should not wire it into `BaseAgent`.
- the shared lazy-export fix must keep import cycles resolved.

Blast radius:

- moderate within `interfaces/`, `shared/`, generated-doc tooling, and their tests.
- low outside those areas if the feature remains interface-only.

### 1c: Assumption & Risk Inventory

1. Assumption: the comment saying “typed dicts” really means the shared formalization record/spec types, which are currently dataclasses and aliases.
Why it matters: implementing a literal TypedDict migration would change the design direction; the current request reads as “move the shared formalization data types into `harnessiq/shared/`.”

2. Assumption: “create a visualization folder in the interfaces folder at `harnessiq/interfaces/formalization`” means convert the current module into a package at that path, not create a folder literally named `visualization`.
Why it matters: the quoted path is explicit and the rest of the comment discusses formalization classes in their own files, which fits a package split.

3. Risk: the public import surface may regress during the module-to-package split.
Mitigation: keep `harnessiq/interfaces/__init__.py` as the stable façade and add/update export tests.

4. Risk: moving shared formalization records into `harnessiq/shared/` could accidentally reintroduce the import-cycle problem fixed in PR #418.
Mitigation: keep the shared formalization data module dependency-light and verify adjacent import-path tests.

5. Risk: generator-owned docs may drift if the source generator is updated but the outputs are not regenerated.
Mitigation: update `scripts/sync_repo_docs.py`, rerun it, and run `tests/test_docs_sync.py`.

Phase 1 complete.
