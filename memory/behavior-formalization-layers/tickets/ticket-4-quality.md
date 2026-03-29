## Stage 1: Static Analysis

- No dedicated linter or static-analysis command is configured in `pyproject.toml`.
- Applied the repository's existing Python style and import conventions manually across the new recovery and safety behavior modules, export surfaces, and tests.

## Stage 2: Type Checking

- No dedicated type-checker configuration is present in the repository.
- Kept explicit annotations on all new typed specs, behavior bases, concrete behavior classes, and helper functions.
- Validated the export surface with direct import smoke checks from both `harnessiq.interfaces` and `harnessiq.formalization`.

## Stage 3: Unit Tests

- Command:
  - `python -m pytest tests/test_formalization_behaviors_recovery_safety.py`
- Result:
  - `6 passed in 0.95s`

## Stage 4: Integration & Contract Tests

- Command:
  - `python -m pytest tests/test_formalization_behaviors_recovery_safety.py tests/test_interfaces.py`
- Result:
  - `32 passed in 0.99s`
- Additional runtime regression slice:
  - `python -m pytest tests/test_agents_base.py -k behaviors_run_before_explicit_formalization_layers_and_receive_tool_call_context`
  - Result: `1 passed, 34 deselected in 1.05s`

## Stage 5: Smoke & Manual Verification

- Retry and recovery smoke test:
  - Ran a Python snippet constructing `RetryStrategyBehavior(monitored_patterns=("exa.*",), max_retries=1)` and a repeated `exa.request` call.
  - Confirmed the first `on_tool_call(...)` returned `ToolCall`, then after recording one failing result the next identical call was blocked with strategy `retry`.
- Irreversible confirmation smoke test:
  - Ran a Python snippet constructing `IrreversibleActionGateBehavior(irreversible_patterns=("filesystem.write_*",))`.
  - Confirmed visible tools initially collapsed to `('behavior.confirm_action',)`, then `behavior.confirm_action` returned `{"confirmed": true, ...}` and the protected write tool became visible for the next call.
- Scope-guard smoke test:
  - Ran a Python snippet constructing `ScopeGuardBehavior` with a forbidden `path` substring of `"..\\"`.
  - Confirmed a `filesystem.write_text_file` call targeting `..\\outside.txt` was blocked and returned guardrail `SCOPE_GUARD`.
