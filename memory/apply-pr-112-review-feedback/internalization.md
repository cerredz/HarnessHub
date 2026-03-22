### 1a: Structural Survey

PR #112 added `define_tool()` factory and `@tool` decorator. It was merged into the `origin/issue-108` branch but the changes never landed in `main` because PR #111 (which merged `issue-108` → `main`) had already been submitted first. As a result, three things are missing from `main`:

1. `tool_type: str = "function"` field on `ToolDefinition` in `harnessiq/shared/tools.py`
2. `harnessiq/toolset/factory.py` — contains `define_tool()` and `@tool`
3. `tests/test_toolset_factory.py` — 441-line test suite covering both

Additionally, `harnessiq/toolset/__init__.py` on `main` does not import `define_tool` or `tool`, and its `__all__` list is missing them.

The single PR comment reads: *"For this category of tools, they should be in the sdk of people creating their own tools, and also inserted into the harnessiq tools that we have registered"*

This has two parts:
- **Part 1** — `define_tool`/`@tool` should be first-class members of the public `harnessiq.toolset` SDK so SDK consumers can create their own tools ergonomically. This requires porting the missing factory and updating the module exports.
- **Part 2** — Custom tools produced by `define_tool`/`@tool` should be registerable into the central `ToolsetRegistry` so they appear alongside built-in tools when you call `get_tool()`, `list_tools()`, etc. Currently `ToolsetRegistry` has no such mechanism.

**Affected modules:**
- `harnessiq/shared/tools.py` — add `tool_type` to `ToolDefinition`
- `harnessiq/toolset/factory.py` — new file, port from `origin/issue-108`
- `harnessiq/toolset/__init__.py` — add imports and exports for `define_tool`, `tool`, `register_tool`, `register_tools`
- `harnessiq/toolset/registry.py` — add `register_tool` and `register_tools` methods
- `tests/test_toolset_factory.py` — new file, port from `origin/issue-108`
- `tests/test_toolset_registry.py` — extend with custom-tool registration tests

**Existing test coverage on main:**
- `tests/test_toolset_registry.py` — covers `get_tool`, `get_many`, `get_family`, `list_tools`; no custom-registration tests

**Patterns to follow:**
- `ToolsetRegistry` uses lazy initialization (`_ensure_builtin_loaded`); custom tools should have a separate store that doesn't interfere with builtins
- Module-level helpers delegate to `_get_registry()`; `register_tool` should follow the same delegation pattern
- All public API functions are in `__all__`

### 1b: Task Cross-Reference

| Requirement | File | What changes |
|---|---|---|
| `tool_type` on `ToolDefinition` | `harnessiq/shared/tools.py` | Add `tool_type: str = "function"` field; update `as_dict()` docstring |
| `define_tool()` factory | `harnessiq/toolset/factory.py` | New file (port from `origin/issue-108`) |
| `@tool` decorator | `harnessiq/toolset/factory.py` | Same file as above |
| SDK exports | `harnessiq/toolset/__init__.py` | Import `define_tool`, `tool` from `.factory`; add to `__all__` |
| `register_tool(tool)` | `harnessiq/toolset/registry.py` + `__init__.py` | New method on registry + module-level delegation |
| `register_tools(*tools)` | `harnessiq/toolset/registry.py` + `__init__.py` | New method on registry + module-level delegation |
| Factory tests | `tests/test_toolset_factory.py` | New file (port from `origin/issue-108`) |
| Registration tests | `tests/test_toolset_registry.py` | Extend with custom-tool registration tests |

### 1c: Assumption & Risk Inventory

1. **The `tool_type` field must not break `as_dict()` serialization** — currently `as_dict()` outputs `key`, `name`, `description`, `input_schema`. The PR #112 version intentionally omits `tool_type` from `as_dict()` because it is SDK metadata, not an API payload field. All existing tests that assert on `as_dict()` output will still pass.

2. **`register_tool` on the shared module-level registry** — the module uses a singleton `_registry`. Calls to `register_tool` must mutate the singleton and also reset correctly if tests rely on registry isolation. Test isolation will require either per-test registry instances or a `clear_custom_tools()` helper.

3. **Key collision between custom and built-in tools** — if `register_tool` is called with a key that already exists in the built-in catalog, the behavior must be defined (raise or override). Raising `ValueError` on collision is the safest choice consistent with the registry's existing strict error messages.

4. **The `test_toolset_factory.py` test file references `from harnessiq.toolset import define_tool, tool`** — this import will fail on main until both `factory.py` and the updated `__init__.py` are in place.

5. **`KNOWT_CREATE_FILE`/`KNOWT_EDIT_FILE` vs `FILES_CREATE_FILE`/`FILES_EDIT_FILE`** — `main` uses `FILES_CREATE_FILE`/`FILES_EDIT_FILE` while `origin/issue-108` uses `KNOWT_CREATE_FILE`/`KNOWT_EDIT_FILE`. This is a divergence introduced by a separate PR between #112 and current main. The `factory.py` file is independent of these constants so no conflict exists there, but `shared/tools.py` on main must be respected.

Phase 1 complete.
