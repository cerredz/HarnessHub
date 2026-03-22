# Ticket 1: Port define_tool() factory, @tool decorator, and tool_type to main

## Title
Port define_tool() factory, @tool decorator, and ToolDefinition.tool_type from PR #112

## Intent
PR #112 added `define_tool()` and `@tool` to the `harnessiq.toolset` SDK so consumers can create custom tools without manually constructing `ToolDefinition` objects. The PR merged into `origin/issue-108` but never landed in `main`. This ticket brings those changes to `main` as required by the PR comment: "they should be in the sdk of people creating their own tools."

## Scope
**In scope:**
- Add `tool_type: str = "function"` field to `ToolDefinition` in `harnessiq/shared/tools.py`
- Create `harnessiq/toolset/factory.py` with `define_tool()` and `@tool`
- Update `harnessiq/toolset/__init__.py` to import and export `define_tool` and `tool`
- Port `tests/test_toolset_factory.py`

**Out of scope:**
- Custom tool registration into the catalog (Ticket 2)
- Any changes to provider tools, agents, CLI, or other toolset sub-modules

## Relevant Files
- `harnessiq/shared/tools.py` — add `tool_type: str = "function"` to `ToolDefinition`; update `as_dict()` docstring to note omission of `tool_type`; no changes to constants or other types
- `harnessiq/toolset/factory.py` — new file; `define_tool()`, `@tool`, `_validate_tool_type()`, `_name_from_key()`, `_build_input_schema()`
- `harnessiq/toolset/__init__.py` — add `from .factory import define_tool, tool`; add both to `__all__`
- `tests/test_toolset_factory.py` — new file; port 441-line test suite from `origin/issue-108`

## Approach
Port `factory.py` verbatim from `origin/issue-108`. Add `tool_type` to `ToolDefinition` with the same default and `as_dict()` omission behavior. Update `__init__.py` to expose the new symbols. Port tests directly — they already exercise all factory contracts.

The `tool_type` field uses `"function"` as its default so all existing `ToolDefinition` constructions continue to work without any changes to call sites.

## Assumptions
- `harnessiq/shared/tools.py` on `main` does not have `tool_type` on `ToolDefinition` (confirmed by reading the file)
- `factory.py` from `origin/issue-108` does not reference `KNOWT_CREATE_FILE`/`FILES_CREATE_FILE` or any constants that diverged between branches (confirmed — it only imports from `harnessiq.shared.tools`)
- No existing test relies on `ToolDefinition` NOT having a `tool_type` attribute

## Acceptance Criteria
- [ ] `ToolDefinition` has a `tool_type: str = "function"` field
- [ ] `ToolDefinition.as_dict()` does NOT include `tool_type` in its output
- [ ] `harnessiq/toolset/factory.py` exists with `define_tool` and `tool` as public exports
- [ ] `from harnessiq.toolset import define_tool, tool` works
- [ ] `define_tool(key=..., description=..., parameters=..., handler=...)` returns a `RegisteredTool`
- [ ] `@tool(key=..., ...)` decorator returns a `RegisteredTool`
- [ ] `define_tool(..., tool_type="function")` succeeds; `tool_type="computer_use"` raises `ValueError`
- [ ] Unknown `tool_type` raises `ValueError` listing supported and planned types
- [ ] `define_tool` name defaults to the last dot-segment of the key
- [ ] All 441 tests in `tests/test_toolset_factory.py` pass
- [ ] Full existing test suite still passes

## Verification Steps
1. `flake8 harnessiq/toolset/factory.py harnessiq/shared/tools.py harnessiq/toolset/__init__.py`
2. `mypy harnessiq/toolset/factory.py harnessiq/shared/tools.py harnessiq/toolset/__init__.py`
3. `pytest tests/test_toolset_factory.py -v`
4. `pytest tests/ -x` (full suite)
5. Manual smoke: `python -c "from harnessiq.toolset import define_tool, tool; print('OK')"`

## Dependencies
None — this is the first ticket.

## Drift Guard
This ticket must not add any registration mechanism to `ToolsetRegistry`. It must not touch any agent, CLI, provider, or tool handler files. It must not rename or remove any existing `ToolDefinition` fields. Its only additions are the `tool_type` field (with default), the `factory.py` module, and the updated imports/exports.
