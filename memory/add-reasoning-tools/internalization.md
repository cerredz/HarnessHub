# Internalization: add-reasoning-tools

## 1a: Structural Survey

### Architecture
Harnessiq is a Python SDK (`harnessiq/`) with a layered architecture:
- `harnessiq/shared/` — shared data models, type aliases, and **tool key constants**. `tools.py` is the single source of truth for all string keys.
- `harnessiq/tools/` — tool runtime layer. Houses the `ToolDefinition` + `RegisteredTool` + `ToolRegistry` pattern. Factory functions (`create_X_tools()`) return `tuple[RegisteredTool, ...]` and are composed into `BUILTIN_TOOLS` in `builtin.py`.
- `harnessiq/agents/`, `harnessiq/providers/`, `harnessiq/cli/` — agent runtime, provider translation, and CLI layers respectively.
- `tests/` — `unittest.TestCase` tests, one file per tool family.

### Tool System Conventions
- All tool key constants live in `harnessiq/shared/tools.py` and follow `"domain.snake_case_name"`.
- Each family has a `create_X_tools()` factory returning `tuple[RegisteredTool, ...]`.
- Handlers are private `_snake_case` functions accepting `ToolArguments = dict[str, Any]`.
- Input schema: `{"type": "object", "properties": {...}, "required": [...], "additionalProperties": False}`.
- Return type: `dict[str, Any]` (serializable structured data).
- `builtin.py` composes all factory results into `BUILTIN_TOOLS = (...)`.
- `harnessiq/tools/__init__.py` re-exports everything with an explicit `__all__`.

### Argument extraction helpers pattern (from `general_purpose.py`)
- `_require_string(arguments, key)` — mandatory string
- `_require_optional_string(arguments, key)` — optional string or None
- `_require_bool(arguments, key, default)` — optional bool with default
- `_require_int(arguments, key, default)` — optional int with default
- Each helper raises `ValueError` on type mismatch with a clear message.

### Test Conventions
- Import the pure Python functions AND the registry execution path.
- Test happy path + key edge cases + at least one `registry.execute(KEY, {...})` call.
- One `unittest.TestCase` subclass per logical group.

## 1b: Task Cross-Reference

### What to build
A new subfolder `harnessiq/tools/reasoning/` with 50 reasoning lens tools. Each tool:
- Accepts `intent: str` (required) plus lens-specific optional parameters.
- Returns `{"lens": str, "reasoning_prompt": str}` — a formatted cognitive frame the agent uses to generate its next reasoning pass.
- Has a uniquely descriptive `ToolDefinition.description` explaining the cognitive method.
- Is registered under a `"reasoning.X"` key.

### Files touched / created
- **NEW** `harnessiq/tools/reasoning/__init__.py` — public exports for the package
- **NEW** `harnessiq/tools/reasoning/lenses.py` — all 50 tool definitions + handlers + factory
- **MODIFIED** `harnessiq/shared/tools.py` — 50 new key constants + `__all__` expansion
- **MODIFIED** `harnessiq/tools/builtin.py` — add `create_reasoning_tools()` to `BUILTIN_TOOLS`
- **MODIFIED** `harnessiq/tools/__init__.py` — import and re-export `create_reasoning_tools`
- **NEW** `tests/test_reasoning_tools.py` — full test coverage
- **MODIFIED** `artifacts/file_index.md` — document new module and test file

## 1c: Assumption & Risk Inventory

### Resolved assumptions (no clarification needed)
1. **Output contract**: Each tool returns `{"lens": str, "reasoning_prompt": str}`. The `reasoning_prompt` is a formatted instruction the agent uses as its cognitive scaffold. This is consistent with how other tools return structured data that becomes a `tool_result` entry in the context window.
2. **`intent` only required parameter**: All other parameters are optional with sensible defaults. This makes the tools easy to call without exhaustive configuration.
3. **50th tool**: The task text was truncated at tool 49 (`falsification_test`). I add `abductive_reasoning` as the 50th (abductive inference = inference to the best explanation, a natural third pillar of the scientific methods category).
4. **Python identifier fix**: `80_20_focus: boolean` → `apply_80_20_rule: bool` (not a valid Python identifier).
5. **`provocation_operation_po`**: Named `provocation_operation` in the key/name — the `po` suffix is a de Bono abbreviation that is redundant once the full name is used.
6. **Always in BUILTIN_TOOLS**: Reasoning tools are provider-agnostic, universally useful cognitive primitives. They belong in `BUILTIN_TOOLS` alongside general_purpose, context_compaction, etc.
7. **Data-driven factory**: With 50 near-identical tools, a `_build_reasoning_definition()` helper keeps the factory DRY without violating the codebase's explicit-over-implicit convention. Each tool still has a unique `RegisteredTool` instance and a distinct handler function.

Phase 1 complete.
