Introduce the first runtime-capable base agent and align the repository docs with the new scaffold.

## Scope

- add the abstract `BaseAgent` runtime with provider selection and tool execution boundaries
- add unit tests for agent initialization, request building, and tool authorization
- update `README.md` and `artifacts/file_index.md` to reflect the Python scaffold

## Quality Pipeline Results

- Static analysis: Python syntax validated across `src/` and `tests/` with `py_compile`
- Type checking: no repository checker configured; all new agent code is annotated
- Unit tests: `python -m unittest discover -s tests -v`
- Integration/contract tests: no dedicated suite configured for this slice
- Smoke check: manual `DemoAgent` request build and tool execution passed

## Post-Critique Changes

- added explicit validation for blank `name` and `model_name`
- surfaced invalid runtime configuration through `AgentConfigurationError`
