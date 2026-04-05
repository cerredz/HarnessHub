Title: Add repo-local import boundary enforcement and break the current top-level package cycle

Issue URL: https://github.com/cerredz/HarnessHub/issues/464

Intent:
Add mechanical import-boundary checks for the documented package architecture and remove the existing dependency leaks that would otherwise make those checks fail immediately.

Scope:
Add a repo-local AST checker, wire it into tests, update the architecture artifact, and refactor the existing `shared -> tools`, `tools -> toolset`, `shared -> utils`, and `utils -> providers` cycle-causing seams. Preserve public imports and runtime behavior.

Acceptance Criteria:

- [x] A mechanical import-boundary checker exists in the repo and is exercised by tests.
- [x] `shared` no longer imports `tools`, and the repo rejects future regressions.
- [x] `agents` importing provider families with matching tool seams is rejected.
- [x] `cli` importing lower-level provider/tool/toolset internals is rejected.
- [x] The top-level package graph is acyclic.
- [x] Public output-sink and toolset catalog import surfaces remain stable.
- [x] `artifacts/file_index.md` documents the new enforcement surface.


## Quality Pipeline Results
## Quality Pipeline

Stage 1 - Static Analysis

- No project linter or static-analysis tool is configured in `pyproject.toml`.
- Verified by searching for `ruff`, `mypy`, `pyright`, `flake8`, `pylint`, `black`, and pytest config sections in `pyproject.toml`; no repo-level tool config was present.

Stage 2 - Type Checking

- No project type checker is configured in `pyproject.toml`.
- All new helper code and refactored public facades were written with explicit type annotations.

Stage 3 - Unit Tests

- Passed:
  `C:\Users\Michael Cerreto\HarnessHub\.venv\Scripts\pytest.exe -q tests\test_import_boundaries.py tests\test_output_sinks.py tests\test_exa_outreach_shared.py tests\test_leads_shared.py tests\test_toolset_registry.py tests\test_exa_outreach_agent.py tests\test_knowt_agent.py`

Stage 4 - Integration & Contract Tests

- Passed:
  `C:\Users\Michael Cerreto\HarnessHub\.venv\Scripts\pytest.exe -q tests\test_import_boundaries.py tests\test_sdk_package.py tests\test_output_sinks.py tests\test_exa_outreach_shared.py tests\test_leads_shared.py tests\test_toolset_registry.py tests\test_exa_outreach_agent.py tests\test_knowt_agent.py`
- Result: `203 passed`

Stage 5 - Smoke & Manual Verification

- Passed manual checker invocation:
  `python -c "from pathlib import Path; from tests.import_boundaries import find_import_boundary_violations; print(find_import_boundary_violations(Path('harnessiq')))"` via the repo `.venv`
- Observed output: `violations=0`


## Post-Critique Changes
## Self-Critique

Findings from review:

1. The first checker pass still reported two agent-to-provider violations in the existing codebase:
   - `harnessiq/agents/exa_outreach/agent.py` imported `harnessiq.providers.exa.operations`
   - `harnessiq/agents/knowt/agent.py` imported provider-only Creatify types for annotations
   Follow-up applied: switched the Exa helper to `harnessiq.tools.exa.create_exa_tools` and removed the provider-only typing dependency from `KnowtAgent`.

2. The initial cycle-breaking refactor left the old provider output-sink implementation files as unstaged deletions.
   Follow-up applied: committed the file removals so the verified tree matches the enforced architecture.

Post-critique result:

- Re-ran the architecture and compatibility suites after the follow-up fixes.
- Final checker result is clean with zero boundary violations and an acyclic top-level package graph.

