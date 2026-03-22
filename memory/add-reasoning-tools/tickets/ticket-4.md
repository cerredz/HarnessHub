# Ticket 4: Write tests for the reasoning tools

## Title
Write comprehensive unit tests for all 50 reasoning lens tools.

## Intent
Verify that every reasoning lens tool is correctly registered, returns the expected output shape, enforces the required `intent` parameter, and produces a `reasoning_prompt` string that is non-empty and contains the provided intent. Also verify registry round-trip execution for a representative sample from each category.

## Scope
- **In scope**: `tests/test_reasoning_tools.py` — new test file.
- **Out of scope**: Modifying any implementation file, any other test files.

## Relevant Files
- **NEW** `tests/test_reasoning_tools.py`

## Approach

### Test structure
One `unittest.TestCase` subclass: `ReasoningToolsTests`.

### Test coverage plan
1. **`test_create_reasoning_tools_returns_50_tools`** — assert `len(create_reasoning_tools()) == 50`.
2. **`test_all_tools_have_reasoning_prefix`** — assert all keys start with `"reasoning."`.
3. **`test_all_tools_require_intent`** — for each tool, assert `"intent"` is in `required`.
4. **`test_all_tools_have_no_additional_properties`** — assert `additionalProperties == False` for all.
5. **`test_intent_only_invocation_returns_expected_shape`** — for each of the 50 tools, call handler with `{"intent": "test intent"}` and assert `"lens"` and `"reasoning_prompt"` are present and non-empty strings.
6. **`test_reasoning_prompt_contains_intent`** — assert `"test intent"` appears in the `reasoning_prompt` for each tool when called with that intent.
7. **`test_step_by_step_uses_granularity_in_prompt`** — call with `granularity="high"` and assert the prompt reflects high granularity.
8. **`test_tree_of_thoughts_uses_branch_factor`** — call with `branch_factor=5` and assert the prompt references 5 branches.
9. **`test_root_cause_analysis_methodology_fishbone`** — call with `methodology="fishbone"` and assert prompt references fishbone.
10. **`test_six_thinking_hats_colors`** — call with each of the 6 hat colors and assert the prompt is hat-specific.
11. **`test_devils_advocate_aggression_level`** — call with `aggression_level=9` and assert prompt reflects high aggression.
12. **`test_self_critique_with_prior_output`** — call with `prior_output="some prior text"` and assert prompt references it.
13. **`test_missing_intent_raises_key_error`** — assert `KeyError` when `intent` is absent.
14. **`test_registry_executes_sample_reasoning_tools`** — use `create_builtin_registry()` to execute 5 representative tools (one per category) and assert output shapes.
15. **`test_all_lens_names_are_unique`** — assert no two tools share the same `"lens"` value in their output.

## Assumptions
- Tickets 1, 2, and 3 are complete.
- Tests import from `harnessiq.tools.reasoning` for the factory and from `harnessiq.shared.tools` for constants.

## Acceptance Criteria
- [ ] All tests pass under the project's test runner.
- [ ] No test imports or tests functionality from outside `harnessiq.tools.reasoning`, `harnessiq.shared.tools`, and `harnessiq.tools.registry`.
- [ ] Coverage includes at least one handler-level test per category (8 categories).
- [ ] The registry round-trip test exercises at least 5 different tools.

## Verification Steps
1. `python -m pytest tests/test_reasoning_tools.py -v` → all tests pass.
2. `python -m pytest tests/test_reasoning_tools.py --tb=short` → zero failures, zero errors.
3. `python -m pytest tests/` → full suite still passes (no regressions).

## Dependencies
Tickets 1, 2, and 3.

## Drift Guard
This ticket must not modify any production source file. It adds a single new test file only.
