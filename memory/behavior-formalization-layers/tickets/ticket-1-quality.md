## Stage 1: Static Analysis

- No dedicated linter or static-analysis command is configured in `pyproject.toml`.
- Applied the repository's existing style conventions manually and verified the changed files import cleanly.

## Stage 2: Type Checking

- No dedicated type-checker configuration is present in the repository.
- Validated the new runtime signatures and export surface through targeted import checks and the passing test suite.

## Stage 3: Unit Tests

- Command:
  - `python -m pytest tests/test_agents_base.py tests/test_interfaces.py`
- Result:
  - `58 passed in 3.43s`

## Stage 4: Integration & Contract Tests

- Used the same targeted test run as the contract and integration slice for this ticket because the change is concentrated in shared runtime and interface contracts.
- The updated tests cover:
  - `behaviors=` integration in `BaseAgent`
  - ordering relative to explicit formalization layers
  - call-aware behavior hooks
  - runtime validation of result-hook return contracts
  - shared behavior-base self-documentation
  - top-level and legacy-compatible exports

## Stage 5: Smoke & Manual Verification

- Import smoke test:
  - Ran a Python snippet importing `harnessiq.interfaces`, `harnessiq.formalization`, and `harnessiq.interfaces.formalization.behaviors`.
  - Confirmed `BaseBehaviorLayer` resolves from both the interface and legacy-compatible surfaces.
- Runtime smoke behavior:
  - The new agent test exercises a behavior layer that observes a full `ToolCall` before execution and transforms the result with the originating arguments still available.
  - Verified the transformed transcript payload contains the original tool-call arguments, proving the call-aware runtime hook is wired end to end.
