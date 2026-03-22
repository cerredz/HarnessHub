# Self-Critique — Ticket 1

## What I checked
1. Does `factory.py` follow codebase conventions? Yes — same pattern as `reasoning/core.py` (module docstring with examples, `__all__`, `from __future__ import annotations`).
2. Are the error messages good? Yes — they name the offending value, state what's supported, and mention future types by name.
3. Is `tool_type` excluded from `as_dict()` correctly? Yes — only SDK metadata, not API payload.
4. Is the `_validate_tool_type` function's split between "planned" and "unknown" types clear? Yes — planned types get a targeted message ("planned for a future SDK release"), unknown get a generic one.
5. Do the tests assert on behavior, not implementation details? Yes.
6. Is `_PLANNED_TOOL_TYPES` exhaustive? It could grow — but the set is documented and easily extended.

## Issues found and fixed
None beyond what was already implemented. The factory is clean, minimal, and complete.

## Pre-existing bugs fixed as a side-effect
- `harnessiq/tools/__init__.py` had two duplicate/broken imports for `create_reasoning_tools` from `reasoning.core` (which was renamed to `create_injectable_reasoning_tools`). Removed the two orphaned lines.
- `harnessiq/toolset/catalog.py` `_builtin_reason()` also imported the old name. Fixed to `create_injectable_reasoning_tools`.

These fixes were necessary to unblock the test suite and are strictly correct — no behavior change, just fixing broken imports.
