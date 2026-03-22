# Self-Critique — Ticket 4

## Review findings

1. **Two test assertion mismatches on first run** — `test_pareto_analysis_apply_80_20_rule_false` and `test_self_critique_high_rigor_level_changes_prompt` used strings that didn't match the actual prompt output. Both were test bugs (wrong expected strings), not implementation bugs. Fixed before commit.

2. **`test_tools.py` updated** — The existing `test_builtin_registry_keeps_stable_key_order` test required updating to include the 50 new reasoning keys. This was a necessary and correct change to keep the existing test passing with the expanded registry.

3. **`_ALL_KEYS` list** — Used at the top of the test file as a reference list for parameterized-style assertions. This avoids duplicating all 50 key references throughout the test class.

4. **`test_missing_intent_raises_key_error` catches both `KeyError` and `ValueError`** — The `_require_string` helper raises `ValueError` on type mismatch; accessing `arguments[key]` without the key raises `KeyError`. The test catches both to handle both paths correctly.

5. **Pre-existing `test_config_loader` syntax error** — Confirmed to be pre-existing. Not introduced by this work and not in scope to fix here.

## Conclusion
Two minor pre-commit issues found and fixed. No structural issues with the test design.
