# Ticket 1: Toolset catalog and registry package

## Title
Add `harnessiq/toolset/` package with `ToolEntry` catalog and `ToolsetRegistry`

## Intent
Users need a plug-and-play API for retrieving SDK tools by key or family — mirroring the `master_prompts` pattern exactly. This ticket introduces the `harnessiq.toolset` module with a lazy-loaded registry that covers all built-in and provider tool families and exposes `get_tool()`, `get_tools()`, `get_family()`, and `list_tools()` at the module level.

## Scope
Creates `harnessiq/toolset/` as a new subpackage with three files. Does not touch any existing tool factories, providers, agents, or the top-level `harnessiq/__init__.py` (that is Ticket 3). Does not add `define_tool()` or `@tool` (that is Ticket 2).

## Relevant Files
- `harnessiq/toolset/__init__.py` — create: module-level API + lazy singleton
- `harnessiq/toolset/catalog.py` — create: `ToolEntry` dataclass, built-in family map, provider family map
- `harnessiq/toolset/registry.py` — create: `ToolsetRegistry` class
- `tests/test_toolset_registry.py` — create: full test coverage

## Approach
Mirror the `master_prompts` module exactly:
- `ToolEntry` is to `MasterPrompt` as `ToolsetRegistry` is to `MasterPromptRegistry`
- Family is derived from the key prefix (everything before the first `.`)
- Built-in families are loaded by calling their respective factory functions once; results are cached
- Provider families are loaded on-demand by calling their factory with the supplied `credentials` object
- The registry caches built-in tools by key in a `dict[str, RegisteredTool]` and by family in a `dict[str, tuple[RegisteredTool, ...]]`
- `ToolEntry` objects for built-in tools are derived from `RegisteredTool.definition` fields; provider entries are declared statically (since they cannot be instantiated without credentials)
- Module-level functions delegate to a `_registry` singleton initialized on first call

**Family → factory mapping (built-in):**
Import lazily inside methods to avoid circular imports:
- `core` → from `harnessiq.tools.builtin` filter keys starting with `core.`
- `context` → `create_context_compaction_tools()`
- `text` + `records` + `control` → `create_general_purpose_tools()`
- `prompt` → `create_prompt_tools()`
- `filesystem` → `create_filesystem_tools()`
- `reason` → from `harnessiq.tools.reasoning.core` `create_reasoning_tools()`
- `reasoning` → from `harnessiq.tools.reasoning.lenses` `create_reasoning_tools()`

**Family → factory mapping (provider, requires credentials):**
Each declared statically as family name → import path + function name. Resolved lazily.

## Assumptions
- All provider factory functions accept a `credentials=` keyword argument
- Family is unambiguously the key prefix (no tool crosses family boundaries)
- Knowt tools (`knowt.*`) are excluded from the catalog — they are internal pipeline tools
- Proxycurl is deprecated but still included (note in `requires_credentials=True` and docs)

## Acceptance Criteria
- [ ] `from harnessiq.toolset import get_tool, get_tools, get_family, list_tools` works
- [ ] `get_tool("reason.brainstorm")` returns the correct `RegisteredTool` and it is executable
- [ ] `get_tool("reason.brainstorm").execute({"topic": "AI"})` returns a `ToolResult` with `reasoning_instruction` in output
- [ ] `get_tools("reason.brainstorm", "reason.chain_of_thought")` returns a tuple of 2 tools
- [ ] `get_family("reason")` returns a tuple of 3 tools
- [ ] `get_family("reasoning")` returns a tuple of 50 tools
- [ ] `get_family("reasoning", count=4)` returns the first 4 tools
- [ ] `get_family("filesystem")` returns a tuple of 8 tools
- [ ] `list_tools()` returns a list of `ToolEntry` objects covering all registered families
- [ ] Each `ToolEntry` has correct `key`, `name`, `description`, `family`, `requires_credentials`
- [ ] `get_tool("creatify.request")` raises `ValueError` with a clear message about missing credentials
- [ ] `get_tool("unknown.key")` raises `KeyError` with a clear message listing available keys
- [ ] `get_family("unknown_family")` raises `KeyError` with a clear message listing available families
- [ ] `get_family("reasoning", count=4)` returns exactly the first 4 tools in insertion order
- [ ] Module-level singleton is initialized only once (repeated calls return the same registry instance)

## Verification Steps
1. `python -c "from harnessiq.toolset import get_tool; t = get_tool('reason.brainstorm'); print(t.key, t.execute({'topic': 'AI'}).output)"`
2. `python -c "from harnessiq.toolset import get_family; tools = get_family('reasoning', count=4); print(len(tools), [t.key for t in tools])"`
3. `python -c "from harnessiq.toolset import list_tools; entries = list_tools(); print(len(entries), entries[0])"`
4. `python -m pytest tests/test_toolset_registry.py -v --tb=short`
5. `python -m mypy harnessiq/toolset/`

## Dependencies
None (Ticket 1 is the foundation)

## Drift Guard
This ticket must not touch any existing tool factory, provider, agent, or `harnessiq/__init__.py`. It must not introduce `define_tool()` or `@tool` (Ticket 2). It must not write docs (Ticket 3).
