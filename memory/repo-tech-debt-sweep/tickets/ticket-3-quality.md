Verification for issue `#206`

Commands run:

- `python -m compileall harnessiq tests`
- `..\..\.venv\Scripts\pytest.exe -q tests\test_resend_tools.py tests\test_tools.py`
- `..\..\.venv\Scripts\pytest.exe -q tests\test_sdk_package.py`
- Resend import smoke snippet via `..\..\.venv\Scripts\python.exe -`

Results:

- `python -m compileall harnessiq tests`: passed.
- `tests/test_resend_tools.py tests/test_tools.py`: passed with `15 passed in 0.23s`.
- Resend import smoke snippet: passed, confirmed:
  - `harnessiq.tools.ResendClient is harnessiq.tools.resend.ResendClient`
  - `harnessiq.tools.ResendCredentials is harnessiq.tools.resend.ResendCredentials`
  - the catalog still exposes `64` operations
  - `create_resend_tools` remains callable from the public package surface
- `tests/test_sdk_package.py`: 1 failure, pre-existing on `origin/main` and unrelated to the Resend refactor:
  - `tests/test_sdk_package.py::HarnessiqPackageTests::test_agents_and_providers_keep_shared_definitions_out_of_local_modules`
    - baseline violations come from unrelated agent modules defining shared-style constants/classes:
      - `harnessiq\agents\exa_outreach\agent.py` defines `_LEGACY_DEFAULT_AGENT_IDENTITIES`
      - `harnessiq\agents\exa_outreach\agent.py` defines `ExaOutreachAgentConfig`
      - `harnessiq\agents\prospecting\agent.py` defines `_GOOGLE_MAPS_SEARCH_BASE_URL`
      - `harnessiq\agents\prospecting\agent.py` defines `_SEARCH_SUMMARY_SYSTEM_PROMPT`
      - `harnessiq\agents\prospecting\agent.py` defines `_NEXT_QUERY_SYSTEM_PROMPT`
