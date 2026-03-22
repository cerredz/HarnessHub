# Self-Critique — Ticket 2

## What I checked

1. **Correct isolation between registry instances** — each `ToolsetRegistry()` has its own `_custom_by_key` and `_custom_by_family` dicts. Module singleton pollution is not possible from tests that use direct instances.

2. **`_resolve_family` logic is clear** — The updated `_resolve_family` correctly handles three cases: (a) built-in-only family, (b) custom-only family, (c) mixed family (built-in + custom). The tuple unpacking `(*builtin, *custom)` is idiomatic and readable.

3. **Collision check order** — Checking built-ins first, then providers, then existing custom keys is the correct priority. The error messages are specific about which category caused the collision.

4. **Module-level `register_tool` uses the parameter name `tool_instance`** — I renamed the parameter from `tool` to `tool_instance` to avoid shadowing the `tool` decorator imported at the top of `__init__.py`. This is a good defensive choice.

5. **The `pragma: no cover` comment** — The `_resolve_family` dead-code branch (`if family in self._custom_by_family` after the earlier combined check) was annotated with `# pragma: no cover`. On reflection, I removed this dead branch entirely since it's unreachable; the earlier `if builtin is not None or custom:` covers all cases where the family exists in custom.

6. **`list()` ordering** — Custom entries appear after provider entries. This is consistent: built-ins first, providers second, custom last. Makes sense conceptually (custom tools are user-defined additions, not catalog items).

## Issues found and fixed

- Removed the unreachable dead-code branch in `_resolve_family` that I had originally left with `# pragma: no cover`. Cleaner to remove it.

## No further issues found
The implementation is minimal, correct, and follows all existing patterns in the registry.
