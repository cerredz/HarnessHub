# Internalization

## 1a: Structural Survey

Repository shape:

- `src/tools/` is the main extension surface for executable tools. It contains canonical built-ins, the deterministic registry, and the context-compaction helpers used by the generic agent runtime.
- `src/shared/` holds stable data contracts and public tool key constants that are shared across agents, providers, and tests.
- `src/agents/` contains the provider-agnostic runtime loop plus a concrete LinkedIn harness that already demonstrates how tool outputs can mutate context or pause execution.
- `src/providers/` translates tool metadata and model requests across OpenAI, Anthropic, Gemini, and Grok adapters, but does not own local tool behavior.
- `tests/` is a standard-library `unittest` suite. Coverage is organized by subsystem and favors pure-function behavior plus registry-level integration checks.
- `artifacts/file_index.md` is the maintained architectural index for the repository and should reflect meaningful structural additions or shifts in module responsibility.

Technology and conventions:

- Plain Python package with `unittest`; no dedicated linter or type-checker configuration is present in the repo root.
- Runtime models are intentionally small and explicit: dataclasses, typed dicts, protocols, and pure helper functions.
- New tool families are introduced through pure helpers plus `RegisteredTool` factories, then exported from `src/tools/__init__.py`.
- Built-in tools are ordered deterministically and exposed through `create_builtin_registry()`, so expanding the built-in set affects registry ordering tests.

Relevant existing architecture:

- `src/shared/tools.py` defines canonical tool metadata and the current built-in keys.
- `src/tools/builtin.py` is the composition point for the default built-in tool suite.
- `src/tools/context_compaction.py` is the strongest existing pattern for a reusable tool family: pure helpers, a tool factory, and focused tests.
- `src/agents/base.py` recognizes special tool outputs such as compaction results and `AgentPauseSignal`, so a general pause-control tool can plug into existing runtime behavior without additional agent changes.

## 1b: Task Cross-Reference

User request mapping:

- "Brainstorm and include 10 generalizable tools" maps cleanly to the `src/tools/` layer because that is the repository's provider-agnostic runtime tool surface.
- The request asks for tools that are broadly important across many agent types, so the new tools should avoid domain-specific side effects and instead focus on reusable text transformation, record manipulation, and control-flow primitives.

Concrete code impact:

- `src/shared/tools.py`: add the new canonical tool keys so every subsystem uses stable public identifiers.
- `src/tools/`: add a new reusable tool-family module, wire it into built-ins, and export the public surface.
- `tests/`: add focused coverage for the new helper behaviors and update registry-order expectations.
- `artifacts/file_index.md`: update the tool-layer description to reflect that it now contains a broader general-purpose transformation toolkit.

Behavior to preserve:

- Existing built-in tools (`core.echo_text`, `core.add_numbers`, and the context-compaction tools) must continue to work unchanged.
- Tool metadata must remain provider-agnostic and JSON-serializable.
- Registry ordering must stay deterministic even after adding more built-ins.

## 1c: Assumption & Risk Inventory

Assumptions:

- "Tools" refers to repository-native `RegisteredTool` implementations, not external MCP integrations or provider-specific tool payload builders.
- The most useful broadly reusable tools in this scaffold are deterministic local helpers for text cleanup, regex extraction, record shaping/filtering/sorting, and controlled human escalation.
- The new tools should be available in the default built-in registry so any future agent can opt into them without extra assembly work.

Risks and edge cases:

- The registry's lightweight validation only checks required and unexpected keys, so each tool handler must validate types and bad option values clearly.
- Overly clever generic tools would be hard to reason about; the suite should stay small, orthogonal, and composable rather than trying to encode a mini query language.
- Adding many built-ins changes default tool order and could affect any future tests or code that assume the current six-key registry.
- A general pause tool must return `AgentPauseSignal` in the same shape the base agent already understands.

Phase 1 complete
