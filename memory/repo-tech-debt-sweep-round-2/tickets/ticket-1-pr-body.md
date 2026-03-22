Title: Decompose the shared Resend metadata module behind a compatibility facade

## Summary

- Split `harnessiq/shared/resend.py` into focused `resend_models`, `resend_paths`, and `resend_catalog` modules.
- Kept `harnessiq.shared.resend` as the stable compatibility facade for public imports.
- Preserved the shared `__module__` ownership contract and catalog size while tightening facade coverage in tests.

## Testing

- `python -m compileall harnessiq tests`
- `.venv\Scripts\pytest.exe -q tests/test_resend_tools.py tests/test_email_agent.py`
- `.venv\Scripts\pytest.exe -q tests/test_sdk_package.py` (`origin/main` baseline failure remains in unrelated agent modules)
- Manual smoke snippet importing the shared Resend facade and checking dataclass module ownership plus catalog length

## Post-Critique Changes

- Added explicit test coverage for `ResendOperation` and `ResendPreparedRequest` module ownership through the shared facade.
