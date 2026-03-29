## Stage 1: Static Analysis

- No dedicated linter or static-analysis command is configured in `pyproject.toml`.
- Applied the repository's existing Python style and import conventions manually across the new reasoning and quality behavior modules, export surfaces, and tests.

## Stage 2: Type Checking

- No dedicated type-checker configuration is present in the repository.
- Kept explicit annotations on all new typed specs, behavior bases, concrete behavior classes, and helper callables.
- Validated the export surface with direct import smoke checks from both `harnessiq.interfaces` and `harnessiq.formalization`.

## Stage 3: Unit Tests

- Command:
  - `python -m pytest tests/test_formalization_behaviors_reasoning_quality.py`
- Result:
  - `6 passed in 0.93s`

## Stage 4: Integration & Contract Tests

- Command:
  - `python -m pytest tests/test_formalization_behaviors_reasoning_quality.py tests/test_interfaces.py`
- Result:
  - `31 passed in 0.97s`
- Additional runtime regression slice:
  - `python -m pytest tests/test_agents_base.py -k behaviors_run_before_explicit_formalization_layers_and_receive_tool_call_context`
  - Result: `1 passed, 34 deselected in 1.03s`

## Stage 5: Smoke & Manual Verification

- Import and reasoning smoke test:
  - Ran a Python snippet importing `HypothesisTestingBehavior` and `PreActionReasoningBehavior` from `harnessiq.interfaces` plus `ScopeEnforcementBehavior`, `CitationRequirementBehavior`, and `QualityGateBehavior` from `harnessiq.formalization`.
  - Confirmed the reasoning-gated write flow changed visible tools from `('reason.chain_of_thought',)` before reasoning to `('artifact.write_json', 'reason.chain_of_thought')` after a simulated reasoning result.
- Quality-gate smoke test:
  - Ran a Python snippet constructing `QualityGateBehavior` around a `READY` criterion and executing the real `control.mark_complete` tool from a temporary memory root.
  - Confirmed completion was blocked first with `['READY']`, then allowed after flipping the tracked state, returning `control.mark_complete`.
