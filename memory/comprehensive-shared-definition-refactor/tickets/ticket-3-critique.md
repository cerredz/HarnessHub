Issue: #179

Self-critique findings
- The automated extraction copied old module docstrings into the new `harnessiq/shared/*.py` files, leaving several modules claiming to contain tool factories even though they now only own shared metadata.
- The first cleanup pass removed `OrderedDict` too broadly from provider `operations.py` files, even where `_build_tool_description()` still groups operation summaries with it.

Post-critique improvements
- Rewrote the generated shared-module docstrings so they accurately describe the new shared metadata ownership.
- Tightened the import cleanup by restoring `OrderedDict` only in the provider `operations.py` files that still use it for tool-description rendering.

Verification rerun
- Passed:
  - `& 'C:\Users\Michael Cerreto\HarnessHub\.venv\Scripts\python.exe' -m pytest <all provider tests> tests\test_resend_tools.py -q`
- Result: `628 passed, 1 warning`
- Import smoke passed for:
  - `harnessiq.tools.resend`
  - `harnessiq.tools`
