## Static Analysis

No dedicated linter configuration is present in `pyproject.toml`, so no separate static-analysis command was available to run for this ticket. The change was kept small and style was validated through the targeted test runs and direct code inspection.

## Type Checking

No dedicated type-checker configuration is present in `pyproject.toml`, so no separate repository type-check command was available to run for this ticket. The new module was written with explicit type annotations throughout.

## Unit Tests

- `python -m pytest tests/test_interfaces.py`
- Result: `20 passed`

## Integration & Contract Tests

- `python -m pytest tests/test_output_sinks.py tests/test_toolset_dynamic_selector.py`
- Result: `26 passed`

- `python -m pytest tests/test_harness_manifests.py tests/test_validated_shared.py tests/test_tool_selection_shared.py`
- Result: `22 passed`

## Smoke & Manual Verification

- Manual import-path verification happened indirectly through the test suite by importing `harnessiq.interfaces` from the public SDK surface and instantiating concrete subclasses of the new abstract bases.
- This also exercised the shared-package lazy-export fix that was needed to keep the public import path stable.
