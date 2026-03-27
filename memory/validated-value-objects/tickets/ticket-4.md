Title: Centralize typed tool-description construction across provider surfaces

Issue URL: https://github.com/cerredz/HarnessHub/issues/338

Intent:
Apply the value-object pattern to the repository’s tool-description strings so provider/tool layers stop treating descriptions as arbitrary raw text assembled ad hoc in each module.

Scope:
Introduce shared typed description normalization and a reusable provider-operation description builder, then wire high-leverage tool-definition entrypoints onto it. This ticket does not change provider credentials or numeric argument parsing.

Relevant Files:
- `harnessiq/shared/tools.py`: validate tool names/descriptions through shared scalars
- `harnessiq/providers/base.py`: consume the normalized description surface when serializing provider tools
- `harnessiq/tools/context/__init__.py`: use the typed description path for context tool definitions
- `harnessiq/providers/apollo/operations.py`: migrate to a shared provider-operation description builder
- analogous provider/tool operation modules that currently implement near-identical `_build_tool_description` functions
- `tests/test_provider_base.py`: preserve provider tool serialization behavior
- `tests/test_context_window_tools.py`: preserve description quality expectations for context injection tools

Approach:
Introduce a shared typed description abstraction backed by validated non-empty text, then use helper builders for repetitive provider operation-description patterns instead of bespoke `_build_tool_description` functions everywhere. Keep the outward description text stable where possible; the win is centralized construction and earlier invalid-text rejection, not large copy edits. Start with the shared `ToolDefinition` path and one representative provider-operation family, then extend to other equivalent families in the same ticket if the helper proves stable.

Assumptions:
- Tool descriptions are part of the runtime contract and should never be blank or malformed.
- The provider operation modules are repetitive enough that a shared builder will reduce drift without hurting readability.
- Existing tests that assert multi-sentence descriptions should continue to pass without content weakening.

Acceptance Criteria:
- [ ] Tool-definition construction validates descriptions through the shared scalar layer.
- [ ] At least one shared provider-operation description builder replaces duplicated per-module description assembly.
- [ ] Provider/tool serialization behavior remains compatible.
- [ ] Existing description-oriented tests pass, with added coverage for invalid description construction if needed.

Verification Steps:
- Run `tests/test_provider_base.py`.
- Run `tests/test_context_window_tools.py`.
- Run at least one focused provider tool test covering a migrated operation-description module.

Dependencies:
- Ticket 1

Drift Guard:
This ticket must not become a mass copy-edit of tool prose. It is a construction and normalization refactor only, with behavior-preserving text output as the default.
