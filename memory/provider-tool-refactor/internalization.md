### 1a: Structural Survey

**Repository Shape:**
- `harnessiq/` — production Python SDK
- `harnessiq/shared/` — shared types, constants, configs for cross-module reuse
- `harnessiq/tools/` — tool runtime layer (builtin tools + Resend)
- `harnessiq/providers/` — provider adapters grouped by domain
- `harnessiq/agents/` — agent harnesses
- `harnessiq/cli/` — CLI entrypoints
- `harnessiq/config/` — credential config loader

**Provider Taxonomy (post-merge):**

_LLM providers_ (anthropic, openai, grok, gemini): message/tool normalization helpers; no credentials.py, no operations.py.

_Service providers with operations.py_ (arcads, creatify, exa, instantly, lemlist, outreach): MCP-style operation catalog (OrderedDict of Operation dataclasses), a `build_*_request_tool_definition()` function, and a `create_*_tools()` factory. The tool factory + tool definition currently lives inside `providers/{name}/operations.py`, which belongs to the tool layer, not the provider layer.

_Data providers_ (coresignal, leadiq, peopledatalabs, phantombuster, proxycurl, salesforge, snovio, zoominfo): raw API clients (`api.py`, `client.py`, `requests.py`) + `credentials.py` with a provider-specific TypedDict. No tool layer built yet.

**Tool Layer (`harnessiq/tools/`):**
- Flat files only: `builtin.py`, `registry.py`, `general_purpose.py`, `context_compaction.py`, `filesystem.py`, `prompting.py`, `resend.py`
- `resend.py` is the only external-service tool integration; all others are core runtime tools
- No provider subfolders exist yet

**Shared (`harnessiq/shared/tools.py`):**
- Defines `ToolDefinition`, `RegisteredTool`, `ToolCall`, `ToolResult`, `ToolHandler`, `JsonObject`, `ToolArguments`
- Contains tool key string constants for all core tools (ECHO_TEXT, REMOVE_TOOLS, etc.)
- Does NOT yet contain provider tool key constants

**Key conventions:**
- Tool key constants live in `shared/tools.py`
- Operations catalog: `Operation` dataclass (frozen, slots), `OrderedDict` catalog, `build_*_operation_catalog()`, `get_*_operation()` accessors
- Tool factory: `create_*_tools(credentials, client, allowed_operations) -> tuple[RegisteredTool, ...]`
- Handler returns `{"operation": ..., "method": ..., "path": ..., "response": ...}`
- Description built dynamically from catalog: one line per category listing operation summaries

---

### 1b: Task Cross-Reference

**User's feedback summary:**
- PR #42 (creatify): Move tool registry from `providers/creatify/operations.py` → `tools/creatify/`
- PR #43 (arcads): Move tool registry from `providers/arcads/operations.py` → `tools/arcads/`; tool descriptions → `shared/`; increase semantic descriptions
- PR #44 (exa, instantly, lemlist, outreach): Same as #43
- PR #55 (snovio): Build and register tools in `tools/snovio/`
- PR #56 (leadiq): Build and register tools in `tools/leadiq/`
- PR #57 (salesforge): Build and register tools in `tools/salesforge/`
- PR #58 (phantombuster): Build and register tools in `tools/phantombuster/`
- PR #59 (zoominfo): Build and register tools in `tools/zoominfo/`
- PR #60 (peopledatalabs): Build and register tools in `tools/peopledatalabs/`
- PR #61 (proxycurl): Build and register tools in `tools/proxycurl/`
- PR #62 (coresignal): Build and register tools in `tools/coresignal/`
- General: Provider credential TypedDicts → `harnessiq/shared/`

**Files affected by migration (Group B):**
- `providers/{name}/operations.py` → split: keep API operation dataclass/catalog in providers, move tool factory to `tools/{name}/operations.py`
- `harnessiq/shared/tools.py` → add `*_REQUEST` key constants for each provider
- `tests/test_{name}_provider.py` → update imports if tool factory moves

**Files affected by new tools (Group C):**
- `harnessiq/tools/{name}/__init__.py` + `operations.py` → new files
- `tests/test_{name}_provider.py` → add tool tests

**Files affected by shared credentials:**
- `providers/{name}/credentials.py` → thin re-export pointing to shared
- `harnessiq/shared/credentials.py` → new file with all provider TypedDicts
- `providers/{name}/client.py` + `__init__.py` → update imports

---

### 1c: Assumption & Risk Inventory

1. **Split vs. full move of operations.py**: The provider layer should own the operation catalog (dataclass + dict) since it defines the API surface. The tool factory (`create_*_tools()`) and tool definition builder belong in `tools/{name}/`. Current tests import from `providers/{name}/operations.py`; those imports need updating.

2. **"Tool description in shared folder"**: Interpreted as adding provider tool key constants (e.g., `CREATIFY_REQUEST = "creatify.request"`) to `harnessiq/shared/tools.py`, and enhancing description strings to be semantically richer. The descriptions remain dynamically built in the tools module from the catalog.

3. **Data provider tool pattern**: Snovio and others use individual endpoint functions rather than REST CRUD paths. The operations catalog for these providers should model each client method as a named operation with its HTTP method and path hint. The `client.py` methods are the natural source of operation definitions.

4. **Backward compat for tests**: Existing tests for service providers (creatify, arcads, etc.) test both the operation catalog and the tool factory together. After the split, tests should be updated to import the tool factory from `tools/{name}/` and the catalog accessors from `providers/{name}/operations.py`.

5. **proxycurl is deprecated**: The provider was merged with a note that the service shut down Jan 2025. We should still build a tool layer for consistency but include a deprecation notice in the description.

Phase 1 complete.
