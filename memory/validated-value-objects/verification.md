Implemented tickets and local commits:

- `#335` Add shared validated scalar value objects
  - Commit: `2558888` `add shared validated scalar types`
- `#336` Normalize provider and env credential models through validated scalars
  - Commit: `7490a3b` `normalize provider and env credential validation`
- `#337` Apply bounded integer value objects to context and reasoning tools
  - Commit: `047c8e5` `enforce bounded context and reasoning integers`
- `#338` Centralize typed tool-description construction across provider surfaces
  - Commit: `d9e4e85` `centralize typed tool descriptions`

Verification run:

- Command:
  - `python -m pytest tests/test_validated_shared.py tests/test_credentials_config.py tests/test_apollo_provider.py tests/test_attio_provider.py tests/test_serper_provider.py tests/test_google_drive_provider.py tests/test_resend_tools.py tests/test_provider_base.py tests/test_context_window_tools.py tests/test_context_compaction_tools.py tests/test_reasoning_tools.py tests/test_sdk_package.py -q`
- Result:
  - `275 passed, 3 warnings`

Warnings observed:

- Setuptools reports beta support for `[tool.setuptools]` in `pyproject.toml`.
- `wheel` emits a deprecation warning about `bdist_wheel` location.

Residual note:

- The shared grouped-description builder is now in place and wired into representative provider modules. Additional operation modules can be migrated onto the same helper with low risk if broader consolidation is desired later.
