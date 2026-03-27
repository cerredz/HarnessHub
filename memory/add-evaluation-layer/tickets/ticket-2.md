Title: Add reusable baseline evaluation helpers and tests

Intent:
Provide a starter set of simple, general-purpose evaluation helpers so future contributors can write behavior-focused evals quickly instead of reinventing basic checks.

Scope:
- Add roughly 10-15 reusable evaluation helper functions.
- Keep the helpers generic and pytest-friendly.
- Add focused tests for helper behavior and any top-level package export changes.
- Do not build domain-specific production eval suites yet.

Relevant Files:
- `harnessiq/evaluations/assertions.py`: reusable baseline evaluation helpers.
- `harnessiq/evaluations/__init__.py`: exports for helper functions.
- `tests/test_evaluations.py`: focused behavior tests for the new layer.
- `tests/test_sdk_package.py`: packaging/export coverage updates if needed.

Approach:
Represent evaluation checks as small pure functions over a normalized evaluation context and return structured outcomes rather than ad hoc booleans. Cover both correctness-style assertions and efficiency/tool-use primitives so future evals can be composed out of these helpers.

Assumptions:
- Structured `EvaluationResult`/`EvaluationCheckResult` style payloads are more maintainable than raw asserts for library code.
- Pytest compatibility is satisfied by plain functions plus normal test modules.

Acceptance Criteria:
- [ ] Around 10-15 simple reusable evaluation helpers exist.
- [ ] Helpers cover basic output, tool-use, metadata, and efficiency checks.
- [ ] New tests exercise the helper surface and edge cases.
- [ ] Package export behavior remains valid.

Verification Steps:
- Run the targeted evaluation-layer tests.
- Run packaging smoke tests if the top-level public package surface changes.

Dependencies:
- Ticket 1.

Drift Guard:
This ticket must not turn the scaffolding into a benchmark suite. The helpers should remain generic primitives, not product-specific evaluation logic.
