# Ticket 2: Add register_tool() / register_tools() to ToolsetRegistry

## Title
Add register_tool() and register_tools() to ToolsetRegistry and module-level toolset API

## Intent
The PR #112 comment asks that custom tools "be inserted into the harnessiq tools that we have registered." Currently `ToolsetRegistry` is read-only after initialization — there is no way to add a custom tool so that `get_tool("custom.shout")` works after registration. This ticket adds `register_tool(tool)` and `register_tools(*tools)` to both `ToolsetRegistry` and the module-level `harnessiq.toolset` API.

## Scope
**In scope:**
- Add `register_tool(tool: RegisteredTool) -> None` method to `ToolsetRegistry`
- Add `register_tools(*tools: RegisteredTool) -> None` method to `ToolsetRegistry`
- Registered custom tools are retrievable via `get_tool(key)`, `get_many(...)`, `get_family(family)`, and appear in `list_tools()`
- Raise `ValueError` on key collision with any built-in or already-registered custom tool
- Add module-level `register_tool` and `register_tools` functions to `harnessiq/toolset/__init__.py`
- Extend `tests/test_toolset_registry.py` with custom-tool registration tests

**Out of scope:**
- Persistence of registered tools across process restarts
- Unregistering or replacing tools
- Provider tool registration
- Any changes to agents, CLI, or provider modules

## Relevant Files
- `harnessiq/toolset/registry.py` — add `register_tool`, `register_tools` methods; add `_custom_by_key` and `_custom_by_family` dicts to `__init__`; update `get`, `get_family`, `list` to include custom tools
- `harnessiq/toolset/__init__.py` — add module-level `register_tool` and `register_tools` delegating to `_get_registry()`; add both to `__all__`
- `tests/test_toolset_registry.py` — extend with tests: register single tool, register batch, retrieve by key, retrieve by family, appear in list, key collision raises

## Approach
Add a `_custom_by_key: dict[str, RegisteredTool]` store to `ToolsetRegistry.__init__` (populated eagerly, not lazily, since it starts empty). `register_tool` validates the key does not collide with built-ins or existing custom tools, then inserts into `_custom_by_key` and the appropriate `_custom_by_family` bucket.

`get` checks `_custom_by_key` after the built-in check and before raising `KeyError`. `get_family` merges built-in and custom families. `list` appends custom entries after provider entries.

Key collision check must check both built-in keys (after loading them) and custom keys. This means `_ensure_builtin_loaded()` must be called during `register_tool`.

Module-level functions follow the same delegation pattern as `get_tool` / `get_family`.

## Assumptions
- Ticket 1 is complete (factory.py, tool_type, exports exist)
- `ToolsetRegistry` is a singleton per module instance; test isolation uses `_registry = None` reset between tests or directly constructs `ToolsetRegistry()` instances
- Custom tools registered on the module singleton persist for the lifetime of the process (same as built-in lazy cache)

## Acceptance Criteria
- [ ] `register_tool(my_tool)` on the module-level registry makes `get_tool(my_tool.key)` return `my_tool`
- [ ] `register_tools(tool_a, tool_b)` registers both
- [ ] After `register_tool`, the tool's family appears in `get_family(family)` results
- [ ] After `register_tool`, the tool appears in `list_tools()` output
- [ ] `register_tool` with a key that matches a built-in raises `ValueError` with a descriptive message
- [ ] `register_tool` with a key that was already custom-registered raises `ValueError`
- [ ] Custom tools do not interfere with built-in tool lookup or `get_family` for built-in families
- [ ] `from harnessiq.toolset import register_tool, register_tools` works
- [ ] All new tests pass; full test suite still passes

## Verification Steps
1. `flake8 harnessiq/toolset/registry.py harnessiq/toolset/__init__.py`
2. `mypy harnessiq/toolset/registry.py harnessiq/toolset/__init__.py`
3. `pytest tests/test_toolset_registry.py -v`
4. `pytest tests/ -x`
5. Smoke: `python -c "from harnessiq.toolset import define_tool, register_tool, get_tool; t = define_tool(key='x.y', description='test', parameters={}, handler=lambda a: None); register_tool(t); print(get_tool('x.y'))"`

## Dependencies
Ticket 1 must be complete.

## Drift Guard
This ticket must not change how built-in or provider tool resolution works. It must not add persistence, serialization, or any I/O to the registration mechanism. It must not touch agents, providers, CLI, or tool handler modules.
