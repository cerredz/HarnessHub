Title: Implement retrieval-profile resolution and the default dynamic selector

Issue URL: https://github.com/cerredz/HarnessHub/issues/388

Intent:
Build the core retrieval layer on top of the existing tool catalog and runtime tool definitions without modifying the catalog model itself. This ticket delivers the selector implementation but does not yet wire it into live agents.

Scope:
- Add a retrieval-profile resolution layer that derives `ToolProfile` records from existing catalog-backed tools and additive custom tools.
- Implement the default cosine-similarity dynamic selector in `harnessiq/toolset/`.
- Support always-on and mandatory-tool behavior.
- Keep the selector usable independently of `BaseAgent` integration for unit testing.

Scope Exclusions:
- No agent runtime integration.
- No prompt rendering changes.
- No CLI enablement.
- No documentation changes beyond inline code comments if needed.

Relevant Files:
- `harnessiq/toolset/dynamic_selector.py` — new default selector implementation.
- `harnessiq/toolset/` modules — additive profile-resolution helpers layered on top of the current catalog.
- `harnessiq/shared/tool_selection.py` — any small model refinements needed by the implementation.
- `tests/test_toolset_registry.py` and/or new selector tests — verify profile resolution and selection behavior.
- new targeted tests under `tests/` — verify scoring, subset invariants, always-on preservation, and custom-tool support.

Approach:
Do not modify `ToolEntry` semantics. Instead, build a parallel profile-resolution path that can:
- take existing tool keys from the catalog/runtime registry
- derive baseline retrieval text from current `ToolDefinition` metadata
- allow additive authored/explicit profile overrides where needed
- include additive custom `RegisteredTool` instances passed through Python construction

The selector should accept an embedding backend interface, precompute profile embeddings, and return deterministic `ToolSelectionResult` values.

Assumptions:
- The existing tool catalog remains the source of tool identity and lookup.
- Baseline retrieval profiles can be derived from current tool definitions even before authored enrichments are added everywhere.
- Custom tools with custom callables are supported through the Python API, not CLI-supplied functions.

Acceptance Criteria:
- [ ] A default selector implementation exists in `harnessiq/toolset/`.
- [ ] The selector indexes candidate profiles without mutating the current catalog model.
- [ ] The selector returns only keys inside the candidate ceiling.
- [ ] `always_on` and `mandatory_tools` behavior is enforced.
- [ ] Custom additive `RegisteredTool` objects can participate in profile resolution.
- [ ] The implementation is covered by focused unit tests.

Verification Steps:
- Static analysis on changed files.
- Type-check changed files or ensure all new code is annotated.
- Run targeted selector/profile-resolution unit tests.
- Run adjacent toolset catalog/registry tests.
- Perform a small smoke run of the selector in isolation with fake embeddings.

Dependencies:
- `ticket-1.md`

Drift Guard:
This ticket must not change `BaseAgent`, wire the selector into live model requests, add CLI flags, or update docs. It delivers the retrieval layer only.
