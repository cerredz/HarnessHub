## Stage 1: Static Analysis

- No dedicated linter or static-analysis command is configured in `pyproject.toml`.
- Applied the repository's existing Python style and import conventions manually across the new behavior modules and export surfaces.

## Stage 2: Type Checking

- No dedicated type-checker configuration is present in the repository.
- Kept explicit annotations on all new typed specs, behavior bases, and concrete behavior classes.
- Validated the export surface with direct import smoke checks from both `harnessiq.interfaces` and `harnessiq.formalization`.

## Stage 3: Unit Tests

- Command:
  - `python -m pytest tests/test_formalization_behaviors_tool_pace.py`
- Result:
  - `7 passed in 1.15s`

## Stage 4: Integration & Contract Tests

- Command:
  - `python -m pytest tests/test_formalization_behaviors_tool_pace.py tests/test_interfaces.py`
- Result:
  - `31 passed in 1.15s`
- Additional runtime regression slice:
  - `python -m pytest tests/test_agents_base.py -k behaviors_run_before_explicit_formalization_layers_and_receive_tool_call_context`
  - Result: `1 passed, 34 deselected in 1.22s`

## Stage 5: Smoke & Manual Verification

- Import smoke test:
  - Ran a Python snippet importing `ToolCallLimitBehavior` and `ReflectionCadenceBehavior` from the public interface surface and `ProgressCheckpointBehavior` and `VerificationBehavior` from the legacy-compatible formalization surface.
  - Confirmed all four classes resolved successfully.
- Manual state-transition smoke test:
  - Instantiated `ToolCallLimitBehavior({'exa.*': 1})` and confirmed visible tool keys changed from `('exa.request', 'serper.request')` to `('serper.request',)` after one simulated `exa.request` result.
  - Instantiated `ReflectionCadenceBehavior(every_n_calls=1, reasoning_patterns=('reason.*',), blocked_until_reflected=('exa.*',))` and confirmed visible tool keys changed from `('exa.request', 'reason.chain_of_thought')` to `('reason.chain_of_thought',)` after one simulated non-reasoning result.
