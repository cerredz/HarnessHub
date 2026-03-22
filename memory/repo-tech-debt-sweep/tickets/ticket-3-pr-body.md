## Summary

- split `harnessiq.tools.resend` into focused client, catalog, and tool-factory modules
- keep `harnessiq.tools.resend` as a compatibility facade and preserve package-level exports
- add compatibility coverage proving the Resend public surface remains stable

## Testing

- `python -m compileall harnessiq tests`
- `..\..\.venv\Scripts\pytest.exe -q tests\test_resend_tools.py tests\test_tools.py`
- `..\..\.venv\Scripts\pytest.exe -q tests\test_sdk_package.py` *(contains 1 pre-existing baseline failure unrelated to this refactor; documented below)*
- Resend import smoke snippet via `..\..\.venv\Scripts\python.exe -`

## Known baseline failure

- `tests/test_sdk_package.py::HarnessiqPackageTests::test_agents_and_providers_keep_shared_definitions_out_of_local_modules`
