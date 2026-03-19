## Summary

- add `inspect_tools()` to `BaseAgent` so every agent inherits a shared tool-inspection helper
- add registry and registered-tool inspection payloads with descriptions, schemas, parameter metadata, and backing function identity
- add regression tests for the shared runtime and inherited Knowt agent path
- update `artifacts/file_index.md` and record planning, quality, and critique artifacts under `memory/agent-tool-introspection/`

## Quality Pipeline Results

- No repository-configured linter or type-checker command is declared in `pyproject.toml`
- Passed:
  `$env:PYTHONPATH='C:\Users\Michael Cerreto\HarnessHub\Lib\site-packages'; & 'C:\Users\Michael Cerreto\HarnessHub\.venv\Scripts\python.exe' -m pytest tests\test_tools.py tests\test_agents_base.py tests\test_knowt_agent.py tests\test_linkedin_agent.py tests\test_exa_outreach_agent.py tests\test_email_agent.py`
- Result: `83 passed in 1.26s`

## Post-Critique Changes

- preserve required parameters even when a schema omits a matching `properties` entry
- preserve the original `additionalProperties` value instead of coercing it to a boolean
