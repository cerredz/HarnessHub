### 1a: Structural Survey

Top-level structure:
- `artifacts/` holds repo-level reference documents such as [`artifacts/file_index.md`](C:\Users\Michael Cerreto\HarnessHub\.worktrees\instagram-keyword-agent\artifacts\file_index.md), which describes the intended architectural boundaries.
- `docs/` contains end-user package documentation.
- `harnessiq/` is the shipping SDK package. Its main subpackages align with the repository artifact: `agents/` for harnesses, `cli/` for command entrypoints, `integrations/` for runtime adapters, `providers/` for provider/client/helper abstractions, `shared/` for cross-module types and constants, `tools/` for executable tool definitions, `toolset/` for catalog-backed tool lookup, and `utils/` for shared runtime infrastructure.
- `tests/` is a mixed `unittest`/`pytest` suite with module-level coverage across agents, CLI, toolset, providers, and integrations.
- `memory/` stores prior planning artifacts for earlier tasks and PRs.

Technology and runtime conventions:
- Packaging is defined in `pyproject.toml` for Python 3.11+ with setuptools.
- Agent harnesses subclass `BaseAgent`, inject a `ToolRegistry`, and persist durable state under a memory folder.
- Shared constants and runtime contracts live under `harnessiq/shared/*`; tool metadata and handlers are represented by `ToolDefinition` and `RegisteredTool` in `harnessiq/shared/tools.py`.
- Reusable deterministic tools belong in `harnessiq/tools/*` and can be surfaced through `harnessiq/toolset/*`.
- External-service glue and lower-level runtime helpers belong under `harnessiq/providers/*`; provider families already expose lazy factories through `harnessiq/toolset/catalog.py`.
- Browser-specific runtime code currently exists in `harnessiq/integrations/linkedin_playwright.py` and the new Instagram integration, but the architectural artifact explicitly prefers tool/provider indirection over ad hoc direct calls.

Relevant existing implementation patterns:
- `harnessiq/agents/linkedin/agent.py` still defines internal tools directly, but Instagram PR feedback explicitly requests stricter separation for the new agent.
- `harnessiq/tools/*` modules typically expose `create_*_tools()` factories that return `tuple[RegisteredTool, ...]`.
- `harnessiq/toolset/catalog.py` discovers built-in tools through lazy family factories and provider-backed tools through a separate provider factory map.
- `harnessiq/providers/__init__.py` is the package export surface for provider helpers and clients.

Test strategy:
- Targeted unit tests exist for Instagram agent behavior, CLI wiring, and Playwright helper behavior in `tests/test_instagram_agent.py`, `tests/test_instagram_cli.py`, and `tests/test_instagram_playwright.py`.
- Broader package/export expectations are covered by `tests/test_sdk_package.py` and `tests/test_toolset_registry.py`.

Observed inconsistencies:
- The new Instagram agent currently builds its own `RegisteredTool` inline rather than sourcing it from the main tools layer.
- `harnessiq/integrations/instagram_playwright.py` mixes domain logic, Playwright lifecycle management, parsing helpers, and module-local constants.
- The toolset catalog does not yet expose Instagram tools, so the agent cannot consume them through the standard registry path.

### 1b: Task Cross-Reference

User request: apply the owner comments left on PR #163.

Mapped feedback to code:
1. "toolset for agent should be defined in our main tools folder... register them into our toolset"
   - Current source: `harnessiq/agents/instagram/agent.py` defines `_build_internal_tools()` and `_tool_definition()` inline.
   - Needed change: introduce an Instagram tools module under `harnessiq/tools/`, register it in `harnessiq/toolset/catalog.py`, and have the agent import/resuse those tools instead of defining them locally.

2. "constants should do in shared folder"
   - Current source: `harnessiq/integrations/instagram_playwright.py` defines `_GOOGLE_SEARCH_URL`, `_DEFAULT_TIMEOUT_MS`, and `_NETWORK_IDLE_TIMEOUT_MS`.
   - Needed change: move reusable Instagram Playwright constants to `harnessiq/shared/instagram.py` (or another shared module) and import them from there.

3. "extrapolate the playwright helper function into the provider layer... create subfolder 'playwright' in provider folder"
   - Current source: `harnessiq/integrations/instagram_playwright.py` owns page-ready waiting, URL normalization, page text/title extraction, browser/context lifecycle, and direct Playwright import.
   - Needed change: add a new provider subpackage under `harnessiq/providers/playwright/` containing generic Playwright helper functions with parameterized behavior, then reduce the Instagram integration to orchestrating domain-specific search behavior through those helpers.

Concrete files likely touched:
- `harnessiq/agents/instagram/agent.py`
- `harnessiq/integrations/instagram_playwright.py`
- `harnessiq/shared/instagram.py`
- new `harnessiq/tools/instagram.py` or equivalent package module
- `harnessiq/tools/__init__.py`
- `harnessiq/toolset/catalog.py`
- new `harnessiq/providers/playwright/*`
- `harnessiq/providers/__init__.py`
- `tests/test_instagram_agent.py`
- `tests/test_instagram_playwright.py`
- potentially `tests/test_toolset_registry.py` and `tests/test_sdk_package.py`

Behavior that must be preserved:
- `InstagramKeywordDiscoveryAgent` must still expose the same search capability and refresh parameter sections after search execution.
- CLI `instagram run` must still default to the Playwright backend factory and return the same output shape.
- Search result extraction semantics, durable-memory persistence, and duplicate-search protection must remain unchanged.

Blast radius:
- Agent wiring and tool lookup for the Instagram feature.
- Toolset catalog listing and built-in family discovery.
- Provider export surface for the new Playwright helper package.
- Tests covering Instagram behavior and toolset visibility.

### 1c: Assumption & Risk Inventory

Assumptions:
- The three PR comments are the full scope of requested changes; no hidden summary-level review body exists beyond those line comments.
- It is acceptable to add Instagram as a built-in tool family in the toolset catalog even though the tool is agent-specific, because the review explicitly asks for toolset registration.
- "Helper functions in the provider layer" means extracting reusable Playwright browser/context/page primitives, not moving the entire Instagram search backend into `providers/`.

Risks:
- Over-generalizing the provider helper layer could introduce abstraction that the rest of the repo does not yet use.
- Changing tool registration could break the current agent tests if handler binding is no longer instance-aware.
- Adding a new tool family affects global toolset listing; tests may need to be updated to reflect the extra built-in family.
- The repository already contains a parallel LinkedIn Playwright implementation that does not yet use the provider layer. The requested change is limited to the Instagram PR and should not opportunistically refactor LinkedIn.

Resolution status:
- No material ambiguities remain for implementation. The requested feedback is specific enough to proceed directly.

Phase 1 complete
