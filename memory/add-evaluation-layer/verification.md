## Verification

### Commands Run

1. `python -m pytest tests/test_evaluations.py`
   - Result: passed (`21 passed`)

2. `python -m pytest tests/test_sdk_package.py -k "top_level_package_exposes_sdk_modules or package_builds_wheel_and_sdist_and_imports_from_wheel"`
   - Result: passed (`2 passed, 4 deselected`)

3. `python -m pytest tests/test_evaluations.py tests/test_sdk_package.py`
   - Result: partial failure
   - Notes: the new evaluation tests passed, but an unrelated pre-existing failure remains in `tests/test_sdk_package.py::HarnessiqPackageTests::test_agents_and_providers_keep_shared_definitions_out_of_local_modules` due existing constants in `harnessiq/agents/base/agent_helpers.py`.

4. `python scripts/sync_repo_docs.py`
   - Result: regenerated `artifacts/commands.md`, `artifacts/file_index.md`, and `README.md`

5. `python scripts/sync_repo_docs.py --check`
   - Result: passed (`Generated docs are in sync.`)

### Summary

- The new `harnessiq.evaluations` package imports correctly and passes its focused test suite.
- The top-level package export and packaging smoke path touched by this change pass.
- Generated repository docs are in sync after the update.
- One unrelated pre-existing SDK hygiene test failure remains outside the scope of this task.
