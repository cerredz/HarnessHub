### 1a: Structural Survey

**Repository**: Harnessiq — a provider-agnostic agent SDK in Python.

**Architecture Layers** (bottom-up):
1. **`harnessiq/shared/`** — data models and key constants shared across all layers. `tools.py` defines `ToolDefinition`, `ToolCall`, `ToolResult`, `RegisteredTool`, all tool key constants. `agents.py` defines the runtime types (`AgentModel`, `AgentModelRequest`, `AgentParameterSection`, etc.)
2. **`harnessiq/tools/`** — tool implementations. Each domain gets either a standalone module (`general_purpose.py`, `filesystem.py`, `context_compaction.py`, `prompting.py`, `resend.py`) or a subfolder for provider-backed tools (`creatify/`, `exa/`, `arcads/`, etc.). A `builtin.py` assembles the canonical tuple and `registry.py` provides `ToolRegistry` + `create_builtin_registry()`.
3. **`harnessiq/providers/`** — LLM provider translation and HTTP transport. Four LLM providers: Anthropic, OpenAI, Grok, Gemini. A separate set of data/service provider integrations (Creatify, Arcads, Instantly, Exa, etc.) live under their own sub-packages here and in `harnessiq/tools/`.
4. **`harnessiq/agents/`** — harnesses. `base.py` contains `BaseAgent` (abstract, provider-agnostic loop). Concrete agents subclass it: `linkedin.py` (LinkedIn job applier), `email.py` (Resend-backed email agent).
5. **`harnessiq/config/`** — credential loading (`CredentialLoader`) and credential models.
6. **`harnessiq/cli/`** — CLI entry points, currently only LinkedIn.

**Tool naming convention**: `{namespace}.{verb}` — e.g., `reason.brainstorm`, `knowt.create_script`. All namespaced key constants live in `harnessiq/shared/tools.py`.

**Tool implementation pattern**:
- Key constant in `harnessiq/shared/tools.py`
- Handler function `(ToolArguments) -> object` in the tool module
- `RegisteredTool(definition=ToolDefinition(key=..., name=..., description=..., input_schema={...}), handler=...)`
- For stateful tools (closures over agent state): factory function `create_X_tools(state_obj) -> tuple[RegisteredTool, ...]`
- For general tools: factory function `create_X_tools() -> tuple[RegisteredTool, ...]` added to `BUILTIN_TOOLS`

**Agent harness pattern**:
- Subclass `BaseAgent`
- Implement `build_system_prompt() -> str` and `load_parameter_sections() -> Sequence[AgentParameterSection]`
- Constructor builds a `ToolRegistry` from tool groups and passes it as `tool_executor`
- Stateful tools registered via closure: handler methods on `self` become `RegisteredTool` handlers
- Durable state tracked in a dedicated `MemoryStore`-style object
- System prompt in code (LinkedIn pattern) OR loaded from a file (planned for Knowt)

**Compaction tools**: Four special tool keys (`context.*`) that are intercepted by `BaseAgent._apply_compaction_result()` and directly rewrite `_parameter_sections` and `_transcript` instead of being recorded as normal results.

**Conventions**:
- `frozen=True, slots=True` on all dataclasses
- `additionalProperties: False` on all tool JSON schemas
- Tool handlers raise `ValueError` for invalid inputs; `BaseAgent._execute_tool()` catches all exceptions and returns `{"error": str(exc)}`
- `__all__` defined in every public module
- No global mutable state; stateful tools use closures or method references

**Existing video providers**: Creatify (`harnessiq/providers/creatify/`, `harnessiq/tools/creatify/`) and Arcads (`harnessiq/providers/arcads/`, `harnessiq/tools/arcads/`). Both are MCP-style tool factories with an `operations.py` defining a `*.request` tool.

---

### 1b: Task Cross-Reference

**Task 1 — Reasoning Tools**

What is requested:
> Tools that can be injected into any agent, take parameters, output reasoning tokens based on their description, and append this to the context window.

Mapping:
- New file: `harnessiq/tools/reasoning.py` — houses `reason.*` tool implementations
- New key constants in `harnessiq/shared/tools.py` — `REASON_BRAINSTORM`, `REASON_CHAIN_OF_THOUGHT`, `REASON_CRITIQUE`, etc.
- These are general-purpose (not agent-specific), so they should be addable to any `ToolRegistry`
- "Injectable into any agent" — they are `RegisteredTool` instances, passed to any agent's `ToolRegistry` constructor
- Tool output (reasoning text) is a `ToolResult` → appended to `_transcript` → visible in context window via `build_context_window()` — this is the standard path; no special handling needed
- `harnessiq/tools/__init__.py` needs to export the new factory function
- `harnessiq/tools/builtin.py` may or may not include reasoning tools by default (TBD in Phase 2)
- Tests: `tests/test_reasoning_tools.py`
- File index: `artifacts/file_index.md` needs updating

**Task 2 — Knowt Agent**

What is requested:
> A TikTok content creation harness for Knowt/Vidbyte with a master prompt, specific tools, and deterministic agent memory.

Mapping:
- New directory: `harnessiq/agents/knowt/` — agent harness
- New files: `harnessiq/agents/knowt/__init__.py`, `harnessiq/agents/knowt/agent.py`
- New directory: `harnessiq/agents/knowt/prompts/` — prompt files
- New file: `harnessiq/agents/knowt/prompts/master_prompt.md` — system prompt (loaded at runtime, not hardcoded)
- New directory: `harnessiq/tools/knowt/` — Knowt-specific tools in the tool layer
- New files: `harnessiq/tools/knowt/__init__.py`, `harnessiq/tools/knowt/operations.py`
- New key constants in `harnessiq/shared/tools.py`: `KNOWT_CREATE_SCRIPT`, `KNOWT_CREATE_AVATAR_DESCRIPTION`, `KNOWT_CREATE_VIDEO`, `KNOWT_CREATE_FILE`, `KNOWT_EDIT_FILE`
- `KnowtAgentMemory` — deterministic in-code state tracking: `script_created: bool`, `avatar_description_created: bool`, `current_script: str | None`, `current_avatar_description: str | None`
- `create_video` tool: reads memory, returns semantic error if `script_created` or `avatar_description_created` is False
- `harnessiq/agents/__init__.py` needs to export `KnowtAgent`
- Tests: `tests/test_knowt_agent.py`
- File index: needs updating

**Relationship between tasks**: The reasoning tools are independent of the Knowt agent but may be used by the Knowt agent (e.g., `create_script` could internally call `reason.brainstorm` or the Knowt agent's tool set could include reasoning tools).

**Video creation provider**: Both Creatify (`harnessiq/tools/creatify/`) and Arcads (`harnessiq/tools/arcads/`) exist. The `create_video` tool's implementation depends on which provider to use (or whether it's a stub).

---

### 1c: Assumption & Risk Inventory

**A1 — Reasoning tools are local (no LLM calls)**
The codebase architecture makes a hard separation: all LLM generation goes through `AgentModel`. Tools are synchronous Python functions that return structured data. "Output reasoning tokens based on their description" most likely means the tools return structured text scaffolds (e.g., a brainstorm template, a CoT outline) that the model uses as reasoning context. If reasoning tools themselves called an LLM, they would need an `AgentModel` parameter — unusual in this architecture.
*Risk*: If the user wants reasoning tools that actually invoke an LLM, this changes the implementation significantly.

**A2 — create_video calls an existing video provider (Creatify or Arcads)**
Two video providers already exist. The `create_video` tool likely delegates to one of them. Which one is unspecified.
*Risk*: Wrong provider chosen, or user wants `create_video` to be a non-API tool (e.g., just prepares a creation job description).

**A3 — Vidbyte content in master prompt uses placeholders**
The user mentioned "vidbyte background information, common pain points, ICP, example scripts, recent scripts." This content is domain-specific and not provided. Placeholders must be used unless the user provides actual content.
*Risk*: Prompts with only placeholders may not be useful for actual runs.

**A4 — KnowtAgentMemory is in-memory (not file-backed)**
The LinkedIn agent persists state to files. For the Knowt agent, "agent memory" appears to be session-level (e.g., within one `run()` call: script created → avatar created → video created). File persistence may not be required.
*Risk*: If the user wants memory to survive agent restarts, in-memory state is insufficient.

**A5 — create_script brainstorm is a single-tool multi-phase output**
The user says `create_script` outputs a brainstorm (10-15 ideas), then creates the script, then stores in agent memory. This could mean: (a) `create_script` returns all three phases in one tool call, or (b) there is a separate `reason.brainstorm` step that the agent calls first, then passes the output to `create_script`. Architecture-wise, (a) is simpler; (b) uses reasoning tools as building blocks.
*Risk*: Wrong decomposition chosen.

**A6 — create_file / edit_file are Knowt-specific wrappers vs reusing filesystem tools**
The user mentions these for "memory storage." The existing filesystem tools (`filesystem.write_text_file`, `filesystem.append_text_file`) already provide this functionality. The Knowt tools may just be named wrappers that write to a specific memory directory.
*Risk*: Duplication if re-implementing what filesystem tools already do.

**Phase 1 complete.**
