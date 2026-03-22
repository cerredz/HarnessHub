# Ticket 2: Custom tool creation — `define_tool()` and `@tool` decorator

## Title
Add `define_tool()` factory and `@tool` decorator with `tool_type` forward compatibility

## Intent
Users need a simple, ergonomic way to create custom tools that integrate seamlessly with the SDK's `ToolRegistry` and agent harnesses. The API should be as close to the existing toolset style as possible, hiding the verbose `ToolDefinition` + `RegisteredTool` construction. The `tool_type` field on `ToolDefinition` future-proofs the type system for code_interpreter, computer_use, multi_agent, and other upcoming tool types.

## Scope
- Adds `tool_type: str = "function"` field to `ToolDefinition` in `harnessiq/shared/tools.py`
- Creates `harnessiq/toolset/factory.py` with `define_tool()` and `tool()`
- Updates `harnessiq/toolset/__init__.py` to export `define_tool` and `tool`
- Creates `tests/test_toolset_factory.py`

Does not touch provider tools, agents, or any factory outside `toolset/`.

## Relevant Files
- `harnessiq/shared/tools.py` — modify: add `tool_type: str = "function"` to `ToolDefinition`, update `as_dict()`
- `harnessiq/toolset/factory.py` — create: `define_tool()` and `tool()`
- `harnessiq/toolset/__init__.py` — modify: add `define_tool`, `tool` exports
- `tests/test_toolset_factory.py` — create: full test coverage

## Approach

**`ToolDefinition` change:**
Add `tool_type: str = "function"` as the last field (has a default so it must come after all required fields). Update `as_dict()` to include `"tool_type": self.tool_type`. This is 100% backwards-compatible — all existing `ToolDefinition(key=..., name=..., description=..., input_schema=...)` calls still work.

**`define_tool()`:**
```python
def define_tool(
    *,
    key: str,
    description: str,
    parameters: dict[str, Any],
    handler: ToolHandler,
    name: str | None = None,
    required: Sequence[str] | None = None,
    additional_properties: bool = False,
    tool_type: str = "function",
) -> RegisteredTool:
```
- `parameters` maps directly to `input_schema["properties"]` — users write `{"text": {"type": "string", "description": "..."}}` not the full JSON Schema object
- `name` defaults to the last segment of `key` (e.g. `"custom.my_tool"` → `"my_tool"`)
- `required` defaults to `[]` (no required fields) when None
- `tool_type` is validated against `_SUPPORTED_TOOL_TYPES = frozenset({"function"})`; unsupported types raise `ValueError` with a clear message mentioning future support
- Builds and returns `RegisteredTool(definition=ToolDefinition(...), handler=handler)`

**`@tool` decorator:**
```python
def tool(
    *,
    key: str,
    description: str,
    parameters: dict[str, Any],
    name: str | None = None,
    required: Sequence[str] | None = None,
    additional_properties: bool = False,
    tool_type: str = "function",
) -> Callable[[ToolHandler], RegisteredTool]:
```
- Returns a decorator that takes a `ToolHandler` and calls `define_tool()` with all the same args
- The decorated function is replaced by the resulting `RegisteredTool`

**Handler convention:** handlers take `ToolArguments` (a `dict[str, Any]`) — consistent with all existing handlers in the codebase.

## Assumptions
- `tool_type: str = "function"` on `ToolDefinition` is backwards-compatible (verified: all existing `ToolDefinition` constructors use keyword args, `tool_type` has a default)
- Future tool types will be added to `_SUPPORTED_TOOL_TYPES` when implemented; the `ValueError` message will explain this to users who try unsupported types now
- `required=None` → no required fields (empty list), not "infer from parameters" — explicit is better

## Acceptance Criteria
- [ ] `from harnessiq.toolset import define_tool, tool` works
- [ ] `define_tool(key="custom.shout", description="...", parameters={"text": {"type": "string"}}, handler=fn)` returns a `RegisteredTool`
- [ ] The returned `RegisteredTool.definition.input_schema` has `type="object"`, correct `properties`, `required=[]`, `additionalProperties=False`
- [ ] `define_tool(..., required=["text"])` sets `input_schema["required"] == ["text"]`
- [ ] `define_tool(..., additional_properties=True)` sets `input_schema["additionalProperties"] == True`
- [ ] `define_tool(..., name="my_name")` sets `definition.name == "my_name"`
- [ ] `define_tool(..., name=None, key="custom.shout")` infers `definition.name == "shout"`
- [ ] `define_tool(..., tool_type="function")` works; `definition.tool_type == "function"`
- [ ] `define_tool(..., tool_type="computer_use")` raises `ValueError` with informative message
- [ ] `@tool(key=..., description=..., parameters=...) def fn(args): ...` produces `RegisteredTool`
- [ ] The custom tool can be added to `ToolRegistry([..., my_tool])` without error
- [ ] The custom tool executes correctly via `ToolRegistry.execute(key, args)`
- [ ] All existing `ToolDefinition` constructions in the codebase still work (no breaking change)
- [ ] `ToolDefinition.as_dict()` includes `"tool_type"` key

## Verification Steps
1. `python -c "from harnessiq.toolset import define_tool; t = define_tool(key='x.y', description='test', parameters={'v': {'type': 'string'}}, handler=lambda a: a['v']); from harnessiq.tools import ToolRegistry; r = ToolRegistry([t]); print(r.execute('x.y', {'v': 'hi'}).output)"`
2. Run full existing test suite to confirm no regressions: `python -m pytest tests/ -v --tb=short`
3. `python -m pytest tests/test_toolset_factory.py -v --tb=short`
4. `python -m mypy harnessiq/shared/tools.py harnessiq/toolset/factory.py`

## Dependencies
Ticket 1 (toolset package must exist before we add exports to `__init__.py`)

## Drift Guard
Must not touch any provider factory, agent, or existing tool definition file other than `harnessiq/shared/tools.py`. The `ToolDefinition` change must be backwards-compatible. Must not implement multi-agent, code-execution, or any future tool type — only declare `tool_type` and validate the current supported set.
