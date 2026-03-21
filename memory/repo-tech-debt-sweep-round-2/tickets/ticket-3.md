Title: Decompose the toolset catalog module into focused builtin and provider catalog layers

Intent:
Make the toolset catalog easier to maintain by separating builtin-family factory wiring from provider metadata and provider factory dispatch, while preserving the stable `harnessiq.toolset.catalog` surface consumed by the registry and tests.

Issue URL: https://github.com/cerredz/HarnessHub/issues/212

Scope:

- Split `harnessiq/toolset/catalog.py` into smaller focused modules.
- Keep `harnessiq.toolset.catalog` as the stable import anchor for `ToolEntry`, builtin-family factories, provider entries, provider entry index, and provider factory map.
- Preserve builtin family ordering, provider entry metadata, and provider factory dispatch strings.
- Do not change registry behavior or introduce new tool families.

Relevant Files:

- `harnessiq/toolset/catalog.py`: convert from a mixed catalog module into a compatibility facade.
- `harnessiq/toolset/catalog_builtin.py`: new module for builtin family factory callables and builtin factory ordering.
- `harnessiq/toolset/catalog_provider.py`: new module for provider `ToolEntry` metadata, entry index, and provider factory dispatch strings.
- `harnessiq/toolset/registry.py`: keep imports aligned with the new catalog layout while preserving behavior.
- `tests/test_toolset_registry.py`: confirm registry behavior and provider catalog metadata remain unchanged.
- `tests/test_arxiv_provider.py`: preserve direct imports of `PROVIDER_ENTRY_INDEX` from the catalog surface.
- `harnessiq/tools/leads/operations.py`: preserve provider-factory-map imports used for family resolution.

Approach:

- Keep `ToolEntry` and the public catalog constants at the existing module path through re-exports.
- Move builtin-family factories into one module and provider catalog metadata / dispatch tables into another.
- Avoid semantic edits to ordering or strings so current registry behavior stays intact.

Assumptions:

- External code depends on the current `harnessiq.toolset.catalog` names but not on internal helper locations.
- `tests/test_toolset_registry.py` and `tests/test_arxiv_provider.py` provide adequate regression coverage for the catalog contracts.
- The current builtin family ordering is intentional and must remain stable.

Acceptance Criteria:

- [ ] The toolset catalog implementation is split into focused builtin and provider modules with `harnessiq.toolset.catalog` remaining the public compatibility surface.
- [ ] Public imports of `ToolEntry`, `BUILTIN_FAMILY_FACTORIES`, `PROVIDER_ENTRIES`, `PROVIDER_ENTRY_INDEX`, and `PROVIDER_FACTORY_MAP` continue to work.
- [ ] Builtin family ordering and provider metadata / dispatch values remain unchanged.
- [ ] Toolset registry tests continue to pass after the refactor.
- [ ] The resulting `harnessiq/toolset/catalog.py` file is materially smaller and easier to scan.

Verification Steps:

- Static analysis: run `python -m compileall harnessiq tests`.
- Type checking: no configured type checker; keep the extracted catalog modules fully annotated.
- Unit tests: run `.venv\Scripts\pytest.exe -q tests/test_toolset_registry.py`.
- Integration and contract tests: run `.venv\Scripts\pytest.exe -q tests/test_arxiv_provider.py tests/test_sdk_package.py` and document unrelated baseline failures if present.
- Smoke/manual verification: run a short `.venv\Scripts\python.exe` snippet that imports catalog symbols from `harnessiq.toolset.catalog` and confirms provider-family lookup still works.

Dependencies:

- None.

Drift Guard:

This ticket is a pure catalog-structure refactor. It must not add new tool families, rename tool keys, change provider factory targets, or redesign `ToolsetRegistry` behavior beyond the minimal import adjustments required to preserve compatibility.
