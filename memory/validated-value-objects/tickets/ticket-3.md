Title: Apply bounded integer value objects to context and reasoning tools

Issue URL: https://github.com/cerredz/HarnessHub/issues/337

Intent:
Introduce the same “invalid value cannot be constructed” pattern to integer-heavy tool inputs, especially the context-window indices/counts and reasoning-tool counts that currently rely on downstream range checks.

Scope:
Refactor context and reasoning coercion helpers to produce semantically validated integer values at parse time, and update the structural/context handlers that currently enforce positivity or index semantics after raw `int` extraction. This ticket does not touch provider credential models or provider operation-description builders.

Relevant Files:
- `harnessiq/tools/context/__init__.py`: add semantic integer parsers/coercers backed by shared validated scalars
- `harnessiq/tools/context/executors/structural.py`: replace downstream positivity/index-range checks where a semantic integer parser can enforce them earlier
- `harnessiq/tools/context/definitions/structural.py`: keep schemas aligned with the new runtime semantics
- `harnessiq/tools/reasoning/core.py`: centralize bounded count/step parsing through shared scalar helpers
- `harnessiq/tools/reasoning/injectable.py`: centralize bounded brainstorm-count parsing
- `harnessiq/tools/reasoning/lenses.py`: reuse shared integer parsers for counts and max-step parameters where applicable
- `tests/test_context_window_tools.py`: add/update coverage for invalid and valid index/count construction
- `tests/test_context_compaction_tools.py`: preserve context compaction behavior

Approach:
Use shared semantic integer parsers for non-negative indices, strictly positive counts, and bounded counts. The important shift is to validate at parse time rather than letting handlers accept a raw `int` and then re-check it. Preserve zero-based indexing where it is intentional (`start_index`, `end_index`, `entry_index`) and use strictly positive types only for arguments such as `keep_last`. Keep end-vs-start relational checks where they encode pairwise semantics instead of primitive validity.

Assumptions:
- Context indices are intentionally zero-based and `0` is valid.
- Arguments like `keep_last` are conceptually positive counts and should reject `0` at parse time.
- Pairwise comparisons such as `end_index >= start_index` still belong in handlers because they depend on multiple values, not one primitive.

Acceptance Criteria:
- [ ] Context and reasoning integer coercion paths construct semantic validated integers instead of trusting raw ints.
- [ ] Positive-count arguments reject invalid values before handler logic proceeds.
- [ ] Zero-based index arguments preserve current behavior for `0` while still rejecting invalid types.
- [ ] Context and reasoning test coverage passes with new assertions for invalid numeric input handling.

Verification Steps:
- Run `tests/test_context_window_tools.py`.
- Run `tests/test_context_compaction_tools.py`.
- Run any focused reasoning-tool test coverage that exercises the updated coercion helpers, or add such coverage if absent.

Dependencies:
- Ticket 1

Drift Guard:
This ticket must not redesign the context tool surface or reasoning prompt content. It is limited to primitive parsing/validation and aligned schema/runtime semantics.
