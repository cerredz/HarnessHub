Issue: #178

Self-critique findings
- The module docstring in `harnessiq/shared/credentials.py` still described the file as TypedDict-only even after it became the home for shared provider credential dataclasses.
- `harnessiq/providers/arxiv/__init__.py` was still re-exporting `ArxivConfig` indirectly through the provider client module, which obscured the new ownership after moving the config object into `harnessiq/shared/provider_configs.py`.

Post-critique improvements
- Updated `harnessiq/shared/credentials.py` to describe the broader shared credential/config role accurately.
- Updated `harnessiq/providers/arxiv/__init__.py` to import `ArxivConfig` directly from `harnessiq.shared.provider_configs` while preserving the public package export.

Verification rerun
- Passed:
  - `& 'C:\Users\Michael Cerreto\HarnessHub\.venv\Scripts\python.exe' -m pytest tests\test_arxiv_provider.py tests\test_creatify_provider.py -q`
- Import smoke passed for:
  - `harnessiq.providers.arxiv`
  - `harnessiq.shared.credentials`
  - `harnessiq.shared.provider_configs`
