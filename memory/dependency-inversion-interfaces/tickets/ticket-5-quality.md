## Static Analysis

- No repository linter is configured in `pyproject.toml`, so I applied the existing codebase style conventions manually.
- Ran `python -m py_compile harnessiq/interfaces/cli.py harnessiq/interfaces/__init__.py harnessiq/cli/adapters/base.py harnessiq/cli/adapters/utils/factories.py tests/test_interfaces.py tests/test_cli_common.py`.
- Result: passed.

## Type Checking

- No repository type checker is configured in `pyproject.toml`.
- This ticket tightened the affected seams with explicit protocol types:
  - `PreparedStoreLoader` for `StoreBackedHarnessCliAdapter.store_loader`
  - `FactoryLoader` for assignment-map helper injection
  - new `IterableFactoryLoader` for iterable-producing factory injection

## Unit Tests

- Ran `pytest tests/test_interfaces.py tests/test_cli_common.py tests/test_cli_environment.py tests/test_platform_cli.py`.
- Result: `55 passed in 2.00s`.

## Integration And Contract Tests

- Ran `pytest tests/test_linkedin_cli.py tests/test_prospecting_cli.py`.
- Result: `11 passed in 1.19s`.
- Note: the run emitted a non-failing external LangSmith warning about `403 Forbidden` on multipart ingestion; pytest still exited successfully and the warning is unrelated to the contract refactor.

## Smoke And Manual Verification

- Ran a Python smoke script that injected structural fake loaders into:
  - `load_optional_iterable_factory(...)`
  - `load_factory_assignment_map(...)`
- Observed output:
  - `('pkg.tools:create', 'PKG.TOOLS:CREATE')`
  - `{'search': {'spec': 'pkg.search:create'}}`
- Confirmation:
  - both helpers accepted protocol-compatible injected loaders instead of relying on the concrete `load_factory` implementation
  - normalized tuple and assignment-map behavior remained unchanged
