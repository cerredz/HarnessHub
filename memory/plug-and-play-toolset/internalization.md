### 1a: Structural Survey

**Architecture:** Harnessiq is a provider-agnostic Python SDK for building AI agents. Core layers:
- `harnessiq/shared/`: core types — `ToolDefinition`, `RegisteredTool`, `ToolResult`, `ToolHandler`, `ToolArguments`, and all key constants. No external dependencies.
- `harnessiq/tools/`: tool family factories and the `ToolRegistry`. Each family exports a `create_*_tools() -> tuple[RegisteredTool, ...]` factory. `create_builtin_registry()` combines all non-provider families.
- `harnessiq/providers/`: HTTP clients and operation catalogs for external APIs (Creatify, Resend, Exa, etc.). Provider tools live in `harnessiq/tools/{provider}/`.
- `harnessiq/agents/`: `BaseAgent` and concrete harnesses (email, linkedin, knowt). Agents consume tools via `AgentToolExecutor` protocol (implemented by `ToolRegistry`).
- `harnessiq/master_prompts/`: plug-and-play catalog for system prompts. API: `get_prompt(key)`, `get_prompt_text(key)`, `list_prompts()`. Lazy singleton pattern. **This is the exact model to replicate for tools.**

**Tool key conventions:** `namespace.name` — e.g. `reason.brainstorm`, `creatify.request`, `filesystem.read_text_file`. Family = key prefix before the dot.

**Tool families by key namespace:**
- Built-in (no credentials): `core`, `context`, `text`, `records`, `control`, `prompt`, `filesystem`, `reason` (3 core), `reasoning` (50 lenses)
- Provider (credentials required): `creatify`, `resend`, `arcads`, `exa`, `instantly`, `lemlist`, `outreach`, `snovio`, `leadiq`, `salesforge`, `phantombuster`, `zoominfo`, `peopledatalabs`, `proxycurl`, `coresignal`
- Internal agent pipeline (excluded from public catalog): `knowt`

**Provider factory import paths:**
- Subpackages: `harnessiq.tools.{provider}` → `create_{provider}_tools(credentials=...)`
- Module: `harnessiq.tools.resend` → `create_resend_tools(client=...)`
- All accept `credentials=` as a keyword arg (some also accept `client=`)

**`ToolDefinition`** (frozen dataclass, slots): `key`, `name`, `description`, `input_schema`. No `tool_type` field yet.

**`RegisteredTool`** (frozen dataclass, slots): `definition`, `handler`. Exposes `.key` property and `.execute()`.

**`master_prompts` pattern (reference):**
- `MasterPrompt` dataclass: `key`, `title`, `description`, `prompt`
- `MasterPromptRegistry` with `get(key)`, `get_prompt_text(key)`, `list()`
- Module-level singleton `_registry` loaded lazily
- Module-level functions `get_prompt()`, `get_prompt_text()`, `list_prompts()`
- `harnessiq/__init__.py` includes `master_prompts` in `_EXPORTED_MODULES`

**Conventions:** frozen dataclasses with `slots=True`, `from __future__ import annotations`, lazy imports for circular-dependency-prone areas, `__all__` on every public module, snake_case functions, docstrings on all public APIs.

### 1b: Task Cross-Reference

**1. Plug-and-play tool retrieval** ("get the create video tool for creatify", "get 4 reasoning tools"):
- **Missing:** `harnessiq/toolset/` package does not exist. Must create.
- **Pattern to follow:** `harnessiq/master_prompts/` exactly.
- **Needed:** `ToolEntry` dataclass, `ToolsetRegistry`, module-level `get_tool()`, `get_tools()`, `get_family()`, `list_tools()`
- **Touches:** new files only. No changes to existing tool or provider code.

**2. Custom tool creation** ("create their own custom tools very easily"):
- **Missing:** No `define_tool()` or `@tool` decorator exists. `RegisteredTool` + `ToolDefinition` construction is verbose.
- **Needed:** `define_tool()` factory + `@tool` decorator in `harnessiq/toolset/factory.py`
- **Forward compat note:** User explicitly says future tool types (code_interpreter, computer_use, multi_agent, etc.) are planned. `tool_type` field should be added to `ToolDefinition` now.
- **Touches:** `harnessiq/shared/tools.py` (add `tool_type: str = "function"` to `ToolDefinition`)

**3. Top-level exposure:**
- `harnessiq/__init__.py`: add `"toolset"` to `_EXPORTED_MODULES`
- `docs/toolset.md`: new documentation file
- `artifacts/file_index.md`: update

### 1c: Assumption & Risk Inventory

1. **Knowt tools excluded:** `knowt.*` tools are internal pipeline tools tied to file-backed agent state — not intended for plug-and-play use by external users. Excluding from catalog. No risk.

2. **Proxycurl deprecated Jan 2025:** Including in catalog but will note in docs as deprecated. The key `proxycurl.request` still exists in shared/tools.py.

3. **`tool_type` on ToolDefinition:** Adding `tool_type: str = "function"` as the last field with a default. Backwards-compatible (no existing call sites need to change). The `as_dict()` method will be updated to include it.

4. **Provider tool resolution with credentials:** Provider tools need typed credentials. The `get_tool(key, credentials=...)` API will accept `object | None` and delegate to the appropriate factory with a `credentials=` kwarg. The factory itself validates the credential type and raises a clear error if wrong. No type-checking at the catalog layer — validation is delegated downstream.

5. **RESEND_REQUEST key:** Unlike other provider keys, `RESEND_REQUEST` is defined in `harnessiq/tools/resend.py`, not `harnessiq/shared/tools.py`. The catalog will import it from `harnessiq.tools.resend`.

6. **`create_reasoning_tools` name conflict in `tools/__init__.py`:** Line 129 of `tools/__init__.py` overrides the lens factory with the core factory. The `toolset` catalog will import directly from `harnessiq.tools.reasoning.lenses` and `harnessiq.tools.reasoning.core` to avoid this ambiguity.

**Phase 1 complete.**
