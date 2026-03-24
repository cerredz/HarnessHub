### 1a: Structural Survey

- `harnessiq/` is the live runtime source tree; generated build residue exists under `build/` and `src/` but is not authoritative.
- The repo is a Python 3.11+ SDK with argparse-based CLIs under `harnessiq/cli/`, harness implementations under `harnessiq/agents/`, shared manifests/state models under `harnessiq/shared/`, deterministic tool factories under `harnessiq/tools/`, and concrete external runtime adapters under `harnessiq/integrations/`.
- The prospecting path is split cleanly:
  - `harnessiq/cli/prospecting/commands.py` parses persisted memory/config, loads a model factory and browser-tools factory, and starts `GoogleMapsProspectingAgent.from_memory(...)`.
  - `harnessiq/agents/prospecting/agent.py` composes canonical browser tool definitions with runtime handlers, prospecting-specific public/internal tools, and durable memory/state updates.
  - `harnessiq/shared/prospecting.py` owns the manifest, defaults, typed custom/runtime parameter coercion, and durable files under `memory/prospecting/<agent>/`.
  - `harnessiq/integrations/google_maps_playwright.py` provides the Playwright-backed browser handlers and the CLI browser-tools factory used by `--browser-tools-factory`.
- Shared browser-tool definitions are centralized in `harnessiq/tools/browser.py`. That module expects integrations to bind the canonical definitions to concrete handlers via `create_browser_tools(handlers=...)`.
- Test coverage follows the same boundaries: CLI tests in `tests/test_prospecting_cli.py`, shared browser tool tests in `tests/test_prospecting_tools.py`, and Google Maps Playwright integration tests in `tests/test_google_maps_playwright.py`.
- Conventions observed in the relevant code:
  - Durable runtime state lives under `memory/`.
  - CLI factory hooks use `module:callable` strings and validate type/shape eagerly.
  - Shared abstractions are preferred over duplicating tool schemas in integrations.

### 1b: Task Cross-Reference

- User task: run the existing Google Maps prospecting agent command successfully and fix the traceback preventing startup.
- Failing path:
  - `harnessiq/cli/prospecting/commands.py::_handle_run` imports and calls the `--browser-tools-factory`.
  - The configured factory resolves to `harnessiq.integrations.google_maps_playwright:create_browser_tools`.
  - Inside `PlaywrightGoogleMapsSession.build_tools()` the module currently calls `create_browser_tools(handlers=...)`.
  - That module also defines its own zero-argument `create_browser_tools()` factory later in the file, so the global name resolves to the local factory at runtime instead of the imported shared binder, producing `TypeError: create_browser_tools() got an unexpected keyword argument 'handlers'`.
- Files directly touched by this fix:
  - `harnessiq/integrations/google_maps_playwright.py`: remove the name collision by calling the shared browser-tool binder through an unambiguous alias.
  - `tests/test_google_maps_playwright.py`: add regression coverage that executes `session.build_tools()` so this collision fails in tests instead of only at runtime.
- Existing behavior that must be preserved:
  - The public CLI factory name `harnessiq.integrations.google_maps_playwright:create_browser_tools` must remain unchanged because the user command already depends on it.
  - Shared browser tool definitions and handler names must stay aligned with `harnessiq/tools/browser.py`.
  - Prospecting CLI behavior, memory layout, and runtime parameter semantics should not change.

### 1c: Assumption & Risk Inventory

- Assumption: the immediate blocker is the namespace collision, and once fixed the command should at least start the browser-tool layer successfully. This is strongly supported by the traceback and current source.
- Assumption: keeping the exported CLI factory name unchanged is required because the user explicitly wants the same terminal command to work.
- Risk: after the collision fix, later runtime issues may still appear (Playwright install, browser profile corruption, Google Maps page changes, API/model configuration). The success check therefore needs a real rerun of the user’s command, not tests alone.
- Risk: the repo already has untracked runtime state under `memory/prospecting/`; implementation should avoid mutating or deleting that data except through the user’s requested run.

Phase 1 complete.
