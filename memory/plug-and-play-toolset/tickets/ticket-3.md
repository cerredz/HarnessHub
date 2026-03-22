# Ticket 3: Top-level export and documentation

## Title
Expose `harnessiq.toolset` at the top level and write `docs/toolset.md`

## Intent
The `toolset` module must be accessible via `import harnessiq; harnessiq.toolset.get_tool(...)` — identical to how `harnessiq.master_prompts` is exposed. The docs file shows the complete end-to-end story: retrieving built-in tools, retrieving provider tools, creating custom tools, and composing everything into a registry for use in an agent.

## Scope
- Updates `harnessiq/__init__.py`: adds `"toolset"` to `_EXPORTED_MODULES`
- Creates `docs/toolset.md`: comprehensive documentation
- Updates `artifacts/file_index.md`: adds entries for all new files

Does not change any implementation code (that is Tickets 1 and 2).

## Relevant Files
- `harnessiq/__init__.py` — modify: add `"toolset"` to `_EXPORTED_MODULES`
- `docs/toolset.md` — create: full documentation
- `artifacts/file_index.md` — modify: add new module and test entries

## Approach

**`harnessiq/__init__.py`:** One-line change — add `"toolset"` to `_EXPORTED_MODULES`:
```python
_EXPORTED_MODULES = frozenset({"agents", "cli", "config", "master_prompts", "providers", "toolset", "tools"})
```

**`docs/toolset.md`:** Follow the concise style of `docs/tools.md` and `docs/agent-runtime.md`. Show:
1. Retrieve a single built-in tool by key
2. Retrieve multiple tools by key
3. Retrieve an entire tool family
4. Retrieve first N tools from a family
5. List all available tools
6. Retrieve a provider tool (with credentials)
7. Create a custom tool with `define_tool()`
8. Create a custom tool with the `@tool` decorator
9. Compose built-in + custom tools into a `ToolRegistry` and use in an agent

## Assumptions
- The lazy `__getattr__` pattern in `harnessiq/__init__.py` handles the rest automatically once `"toolset"` is in `_EXPORTED_MODULES`
- Docs style is concise code-first (matching existing docs)

## Acceptance Criteria
- [ ] `import harnessiq; harnessiq.toolset.get_tool("reason.brainstorm")` works
- [ ] `"toolset" in dir(harnessiq)` is True
- [ ] `docs/toolset.md` exists and covers all 9 usage patterns listed in Approach
- [ ] `artifacts/file_index.md` has entries for `harnessiq/toolset/`, all new source files, and new test files

## Verification Steps
1. `python -c "import harnessiq; t = harnessiq.toolset.get_tool('reason.brainstorm'); print(t.key)"`
2. `python -c "import harnessiq; print('toolset' in dir(harnessiq))"`
3. Read `docs/toolset.md` and confirm all 9 patterns are demonstrated with working code

## Dependencies
Ticket 1 and Ticket 2 (both must be complete before docs can be finalized)

## Drift Guard
Must not touch any implementation file other than `harnessiq/__init__.py`. All changes here are additive only.
