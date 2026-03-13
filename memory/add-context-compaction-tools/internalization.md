# Internalization

## 1a: Structural Survey

Repository shape:

- `src/` is a small Python package centered around two merged concerns today:
- `src/tools/` owns canonical tool metadata, runtime handlers, and deterministic registry/validation behavior.
- `src/providers/` owns provider-agnostic message normalization plus provider-specific request builders and clients for OpenAI, Grok, Anthropic, and Gemini.
- `src/shared/` holds reusable type definitions and constants shared across the tool and provider layers.
- `tests/` contains `unittest` coverage for tools, provider helpers, provider clients, and LangSmith tracing helpers.
- `artifacts/file_index.md` is the maintained architecture artifact for this repository.

Technology and conventions:

- Plain Python package with standard-library `unittest`.
- Runtime abstractions are intentionally lightweight: dataclasses, typed dicts, protocols, and pure helper functions.
- Tooling is modeled canonically as `ToolDefinition` + `RegisteredTool`, executed through `ToolRegistry`.
- Public API exposure is curated through package `__init__.py` files.
- There is no configured linter or type checker in the repository root; code quality is enforced through annotations, small functions, and tests.

Relevant existing architecture:

- `src/shared/tools.py` defines the current canonical tool contracts, including `ToolDefinition`, `ToolCall`, `ToolResult`, and `RegisteredTool`.
- `src/tools/builtin.py` contains the default built-in runtime tools, currently only `echo_text` and `add_numbers`.
- `src/tools/registry.py` validates arguments and executes registered tools deterministically.
- Provider request builders consume tool definitions, but there is no merged agent runtime or transcript model on `main`.

Important repository-state finding:

- Older remote branches `origin/issue-2` and `origin/issue-3` contain an unmerged `src/agents/base.py`, but that work is not present on `main`.
- That means the current branch has no first-class concept of an agent context window, parameter messages, or transcript compaction.

## 1b: Task Cross-Reference

User request mapping:

- The requested additions are new custom tool functions:
- `remove_tool_results`: remove tool-result entries from an agent context window.
- `remove_tools`: remove both tool-call and tool-result entries from an agent context window.
- `heavy_compaction`: retain only the agent's leading parameter messages and strip the rest of the context window.
- `log_compaction`: summarize the full context window through a separate summarizer/LLM call, append that summary after the parameter messages, then strip the rest.

Concrete code impact on the merged codebase:

- `src/shared/`: add a small agent-context data model because current shared types only model provider chat messages, not tool-call/result transcript items.
- `src/tools/`: add reusable compaction helpers and register the new context-compaction tools alongside the existing built-ins.
- `src/tools/__init__.py`: export the new public tool constants and factory surface.
- `tests/`: add coverage for context compaction behavior and registry integration.

Why the change should land here:

- The user asked for injectable tooling functions, and the merged codebase's existing extension point for injectable runtime behavior is `RegisteredTool` inside the `src/tools/` layer.
- Adding a narrow shared agent-context model plus compaction tools is the smallest merged-codebase change that supports the requested behavior without depending on the unmerged `src/agents` branch.

Behavior to preserve:

- Existing built-in tool keys and execution semantics must remain stable.
- Existing provider payload builders must remain unaffected because they consume tool definitions only, not runtime compaction behavior.

## 1c: Assumption & Risk Inventory

Assumptions:

- The requested compaction functions should be added to the merged `main` branch as reusable tool/runtime primitives, not only to the older unmerged agent branch.
- A generic agent-context-window representation can be introduced without implementing the full agent harness in this task.
- "parameters at the beginning of the context window" should be represented explicitly in the new context model so compaction behavior is deterministic rather than inferred from free-form message text.
- `log_compaction` should support an injected summarizer callable because the repository's tool registry supports injectable runtime handlers, while the summarization behavior requires a separate model/agent call.

Risks and edge cases:

- If the future merged agent runtime chooses a transcript shape incompatible with the new context model, adapters will be required. Keeping the model small and explicit reduces this risk.
- A built-in registry cannot construct `log_compaction` correctly without a summarizer dependency; the implementation needs a factory surface rather than hard-wiring a fake summary behavior.
- Compaction helpers must preserve leading parameter entries exactly and maintain stable ordering for all retained items.
- The repository currently has no tool-execution error type beyond validation and key lookup errors, so summarizer dependency failures must use clear existing exception behavior or avoid default registration without a summarizer.

Phase 1 complete
