Title: Decompose the toolset catalog module into focused builtin and provider catalog layers

## Summary

- Split the mixed `harnessiq.toolset.catalog` implementation into dedicated builtin and provider catalog modules.
- Kept `harnessiq.toolset.catalog` as the stable import facade for `ToolEntry` and the public catalog constants.
- Added compatibility coverage for the facade surface and removed an unintended new public alias during self-critique.

## Testing

- `python -m compileall harnessiq tests`
- `.venv\Scripts\pytest.exe -q tests/test_toolset_registry.py`
- `.venv\Scripts\pytest.exe -q tests/test_arxiv_provider.py`
- `.venv\Scripts\pytest.exe -q tests/test_sdk_package.py` (`origin/main` baseline failure remains in unrelated agent modules)
- Manual smoke snippet importing the public catalog surface and checking module ownership plus provider lookup

## Post-Critique Changes

- Removed the unintended `BuiltinFactory` export so the facade does not widen the original public API.
