# Internalization

## 1a: Structural Survey

Repository shape:

- `src/tools/` is the canonical local tool runtime layer. Tool families are implemented as pure helpers plus `RegisteredTool` factories, then assembled into `BUILTIN_TOOLS`.
- `src/shared/` holds canonical tool keys and shared data models. Any new built-in tool family adds stable public identifiers here first.
- `src/agents/` contains the generic agent runtime and a LinkedIn-specific harness. The base runtime already understands tool-driven pause behavior and compaction behavior, but it does not have any built-in concept of mutating its own system prompt during a run.
- `src/providers/` consumes tool definitions as provider-facing metadata and builds provider request payloads. Provider code does not execute local tools.
- `tests/` uses `unittest` and favors pure helper tests plus registry-level integration coverage.
- `artifacts/file_index.md` is the maintained architecture index and should be updated when the meaning of the tool layer expands.

Technology and conventions:

- Plain Python package with stdlib `unittest`; no repo-level linter or type checker is configured.
- The current tool layer is deterministic and synchronous. Existing built-ins are local transformations or control-flow helpers, not wrappers around external shell execution.
- New tool families are typically added in a dedicated module under `src/tools/`, exported through `src/tools/__init__.py`, and appended to `BUILTIN_TOOLS` in stable order.
- Tool validation is intentionally lightweight at the registry layer, so each handler is responsible for clear runtime validation and failure messages.

Relevant existing architecture:

- `src/tools/general_purpose.py` is the strongest recent pattern for reusable built-ins: small helper functions, typed validation helpers, a factory, and focused tests.
- `src/agents/base.py` has a fixed `build_system_prompt()` abstraction and no runtime hook for applying a tool result back into the request's system prompt.
- Existing tools can return plain dict payloads or `AgentPauseSignal`; there is no current tool result type for "replace the agent's system prompt".

## 1b: Task Cross-Reference

User request mapping:

- "Create System Prompt Tool" maps to a new built-in tool family under `src/tools/`, but the exact behavior is ambiguous: it could mean generate a prompt string, persist prompt configuration, or actively replace an agent's system prompt during runtime.
- "another element called System Prompt 2 an Agent" appears to reference either a second prompt-related tool or a second prompt block attached to an agent, but the current codebase has no matching concept by that exact name.
- "add terminal-based tools so that an agent could interact with a computer's file system" maps to a second new tool family under `src/tools/`, likely using explicit per-command tools rather than a generic shell executor because the request says each command should get its own tool call.

Concrete code impact if implemented:

- `src/shared/tools.py`: add canonical keys for the system-prompt and terminal/file-system tools.
- `src/tools/`: add one or more new modules for prompt-generation/prompt-control behavior and terminal/file-system behavior.
- `src/tools/builtin.py` and `src/tools/__init__.py`: register and export the new tool families.
- `tests/`: add helper-level tests and registry/agent integration coverage.
- Potentially `src/agents/base.py`: only if the chosen meaning of the system-prompt tool requires live mutation of the agent request rather than returning generated prompt text.

Behavior to preserve:

- Existing built-ins and registry ordering semantics must remain deterministic.
- The generic agent loop should not gain unsafe ambient file-system access without explicit boundaries.
- Provider adapters should remain unaffected beyond receiving more tool metadata.

## 1c: Assumption & Risk Inventory

Assumptions:

- The user wants provider-agnostic local tools in the repository runtime, not provider-specific tool payload builders.
- The terminal/file-system portion should likely be modeled as explicit tools such as list/read/write/mkdir rather than a single unrestricted shell tool, because the request calls for one tool call per command.
- The new tool family should probably be added to the default built-in registry so future agents can opt into it directly.

Ambiguities and risks requiring clarification:

- The phrase "System Prompt 2 an Agent" is not precise enough to know whether the tool should generate prompt text, attach prompt metadata to an agent, or mutate an agent's live system prompt during execution.
- A true terminal/file-system tool set can range from safe workspace-only file utilities to unrestricted machine access, including destructive operations. That safety boundary materially affects both implementation and tests.
- "Each different command gets a tool call" could mean a narrow file-system command set, or a large terminal surface that includes search, copy, move, delete, current-directory inspection, and command execution. The first cut needs a concrete boundary.
- If live system-prompt mutation is required, the base agent runtime needs a new tool-result contract and state transition path. That is a larger architectural change than simply adding a prompt-generation helper.

Phase 1 complete
