Establish the first canonical tool-registry slice for HarnessHub.

## Scope

- add a provider-agnostic tool definition schema
- add a deterministic runtime registry keyed by stable public strings
- add two built-in tools for the initial slice
- add unit tests for execution, ordering, duplication, and validation failures

## Quality Pipeline Results

- Static analysis: `python -m compileall src tests`
- Type checking: no repository checker configured; all new code is annotated
- Unit tests: `python -m unittest discover -s tests -v`
- Integration/contract tests: no dedicated suite configured for this slice
- Smoke check: manual registry metadata and execution verification passed

## Post-Critique Changes

- added explicit runtime argument validation to the registry boundary
- prevented accidental mutation of shared tool metadata by deep-copying exported schemas
- kept generated Python bytecode out of version control with a minimal `.gitignore`
