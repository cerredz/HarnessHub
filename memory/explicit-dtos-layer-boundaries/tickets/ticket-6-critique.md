Post-critique review found one meaningful gap in the first legacy-provider pass: the new DTO seam was covered directly at the client layer for every family, but the two auth-wrapping tool handlers (`snovio` and `zoominfo`) did not yet prove that they were injecting the temporary access token / JWT into the DTO payload before dispatching to `execute_operation(...)`.

Implemented improvement:

- Added explicit tool-boundary tests in [test_snovio_provider.py](C:/Users/422mi/HarnessHub/.worktrees/issue-331/tests/test_snovio_provider.py) and [test_zoominfo_provider.py](C:/Users/422mi/HarnessHub/.worktrees/issue-331/tests/test_zoominfo_provider.py) that mock the client and assert:
  - the tool handler calls `execute_operation(...)` with a `ProviderPayloadRequestDTO`
  - the DTO payload includes the injected `access_token` for Snovio
  - the DTO payload includes the injected `jwt` for ZoomInfo

Reverification after the critique change:

- `python -m pytest tests/test_provider_payloads.py tests/test_google_drive_provider.py tests/test_arxiv_provider.py tests/test_coresignal_provider.py tests/test_leadiq_provider.py tests/test_peopledatalabs_provider.py tests/test_phantombuster_provider.py tests/test_proxycurl_provider.py tests/test_salesforge_provider.py tests/test_snovio_provider.py tests/test_zoominfo_provider.py tests/test_sdk_package.py -q`
- The Coresignal legacy-provider smoke check repeated successfully.
