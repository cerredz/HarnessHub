Issue: #178
Branch: `issue-178`
Implementation commit: `ab8c770`

Stage 1 - Static Analysis
- No repository linter is configured in `pyproject.toml`.
- Applied a manual static pass to the changed provider/shared files and removed stale client imports left behind by the credential extraction.

Stage 2 - Type Checking
- No repository type checker is configured in `pyproject.toml`.
- Verified the changed provider packages import successfully under the project virtualenv.

Stage 3 - Unit Tests
- Passed:
  - `& 'C:\Users\Michael Cerreto\HarnessHub\.venv\Scripts\python.exe' -m pytest tests\test_arcads_provider.py tests\test_arxiv_provider.py tests\test_attio_provider.py tests\test_creatify_provider.py tests\test_exa_provider.py tests\test_instantly_provider.py tests\test_lemlist_provider.py tests\test_outreach_provider.py tests\test_paperclip_provider.py -q`
- Result: `267 passed`

Stage 4 - Integration & Contract Tests
- No separate provider integration/contract suite is configured for these provider adapters.
- Ran package-level import smoke for every provider package:
  - Imported all `harnessiq.providers.<provider>` packages via the project virtualenv.
- Result: all provider package imports succeeded.

Stage 5 - Smoke & Manual Verification
- Swept for remaining misplaced provider definitions:
  - `rg -n "^DEFAULT_(BASE_URL|API_VERSION|BULK_BASE_URL)\s*=|^class\s+[A-Za-z0-9_]+Credentials\b|^class\s+ArxivConfig\b" harnessiq/providers`
- Result: no remaining inline provider endpoint constants, credential dataclasses, or `ArxivConfig` definitions matched in `harnessiq/providers/`.

Additional package-surface verification
- Ran:
  - `& 'C:\Users\Michael Cerreto\HarnessHub\.venv\Scripts\python.exe' -m pytest tests\test_sdk_package.py -q`
- Result: failed for a pre-existing syntax error in `harnessiq/agents/exa_outreach/agent.py` (`keyword argument repeated: runtime_config`), which is outside ticket #178 scope and belongs to the agent-side normalization slice.
