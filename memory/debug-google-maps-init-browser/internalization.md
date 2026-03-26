### 1a: Structural Survey

Top-level architecture:
- `harnessiq/` is the authoritative runtime package. `build/`, `src/`, `harnessiq.egg-info/`, and caches are generated or derivative according to [artifacts/file_index.md](C:\Users\422mi\HarnessHub\artifacts\file_index.md).
- `harnessiq/cli/` owns argparse entrypoints and command-family modules. `harnessiq/cli/main.py` wires top-level commands and each harness-specific CLI module registers its own subcommands.
- `harnessiq/agents/` owns concrete harness implementations and their prompts. Harnesses compose tools, provider adapters, runtime config, and durable memory.
- `harnessiq/shared/` owns typed manifests, durable memory stores, defaults, and shared models. The manifest layer is the declarative contract for runtime parameters, custom parameters, memory files, and CLI exposure.
- `harnessiq/integrations/` contains concrete browser integrations and other runtime adapters. The Google Maps and LinkedIn browser sessions both live here as Playwright-backed session wrappers.
- `harnessiq/tools/` contains reusable tool definitions and factories; browser sessions bind live handler implementations onto shared browser tool definitions.
- `tests/` is a broad `unittest` suite covering CLI behavior, agents, providers, and tool integrations. The Google Maps browser integration currently has direct unit coverage in `tests/test_google_maps_playwright.py`, while CLI behavior is covered in `tests/test_prospecting_cli.py`.
- `memory/` is treated as first-class durable local state for both runtime agent memory and task artifacts. This aligns with the file index and the invoked workflow.

Technology and runtime conventions:
- Python 3.11+ package managed through `pyproject.toml`; test configuration is lightweight and uses `pytest` with many `unittest`-style tests.
- CLI modules follow a common pattern: parse args, resolve a memory store, optionally seed environment, instantiate a harness or integration, emit JSON for machine-readable results.
- Durable state is persisted under harness-specific memory roots, with prospecting using `memory/prospecting/<agent>/...`.
- Browser integrations use Playwright sync APIs and wrap browser actions as registered tools with deterministic JSON-like outputs.
- Existing code favors small helper functions, explicit defaults, typed dataclasses, and JSON/file-based persistence over hidden runtime state.

Relevant conventions and inconsistencies:
- LinkedIn `init-browser` performs explicit startup navigation and operator prompts in the integration layer. Prospecting `init-browser` launches a persistent context but does not navigate anywhere before returning control to the user.
- Prospecting CLI tests cover configure/show/run, but there is no direct CLI test for `init-browser`.
- Google Maps Playwright tests validate tool handlers after a page exists, but they do not assert session startup behavior such as initial navigation or startup URL selection.
- The repo prefers durable, operator-friendly bootstrap flows for browser-backed agents, so prospecting’s current blank startup page is inconsistent with adjacent browser harness behavior.

### 1b: Task Cross-Reference

User request mapping:
- “The browser that the agent is using is not successfully loading in Google Maps” maps directly to `harnessiq cli prospecting init-browser` in [harnessiq/cli/prospecting/commands.py](C:\Users\422mi\HarnessHub\harnessiq\cli\prospecting\commands.py), specifically `_handle_init_browser`.
- The browser session created by that CLI command is implemented in [harnessiq/integrations/google_maps_playwright.py](C:\Users\422mi\HarnessHub\harnessiq\integrations\google_maps_playwright.py), specifically `PlaywrightGoogleMapsSession.start()`.
- The durable session directory the user is trying to seed for sign-in lives in [harnessiq/shared/prospecting.py](C:\Users\422mi\HarnessHub\harnessiq\shared\prospecting.py) as `ProspectingMemoryStore.browser_data_dir`.
- Comparative expected behavior exists in [harnessiq/integrations/linkedin_playwright.py](C:\Users\422mi\HarnessHub\harnessiq\integrations\linkedin_playwright.py), where startup explicitly navigates to LinkedIn rather than leaving the page blank.
- Regression protection should land in [tests/test_google_maps_playwright.py](C:\Users\422mi\HarnessHub\tests\test_google_maps_playwright.py). Additional CLI-facing coverage may belong in [tests/test_prospecting_cli.py](C:\Users\422mi\HarnessHub\tests\test_prospecting_cli.py) if the fix changes user-visible bootstrap behavior.

Existing behavior that must be preserved:
- Prospecting memory preparation and persistent session directory creation must still happen under the configured agent memory root.
- `init-browser` must remain usable for a manual sign-in flow and continue writing session state to `browser-data`.
- The runtime browser tools created by `create_browser_tools()` must still work with the persisted session directory and should not force a manual step during agent-run startup.

Missing behavior / likely defect:
- The current Google Maps startup flow never calls `page.goto(...)` during session initialization, so the first visible tab can stay at the default blank page (`about:blank`). That directly explains the user-visible symptom.
- There is no automated assertion that the session opens on Google Maps or otherwise gives the operator a usable starting point.

Blast radius:
- Primary code change should be isolated to the Google Maps Playwright integration.
- Tests will need updates in the Google Maps Playwright suite, and possibly CLI coverage if startup messaging or invocation semantics change.
- No manifest, memory-schema, or agent-loop behavior needs to change if the bug is limited to browser initialization.

### 1c: Assumption & Risk Inventory

Assumptions:
- The blank screen symptom is caused by missing startup navigation rather than an environmental Chrome/Playwright installation issue. The code strongly supports this because `PlaywrightGoogleMapsSession.start()` launches a page but never navigates it.
- Opening directly to Google Maps is the intended operator experience for `prospecting init-browser`, because the user explicitly expects the browser to “load in Google Maps” and the parallel LinkedIn bootstrap already navigates to a concrete site.
- Fixing startup navigation inside the integration layer is preferable to bolting a one-off `page.goto` into the CLI handler, because the integration owns session startup semantics and is reused by the browser-tool factory path.

Risks:
- Google Maps can be more timing-sensitive than a generic page load; adding startup navigation should use the existing page-ready wait behavior and tolerate non-idle network states.
- If persistent Chrome launches with startup tabs or profile restore behavior, forcing navigation on the wrong page could be surprising. The safest approach is to reuse the first page and navigate it deterministically when initializing a prospecting session.
- The local checkout is currently dirty and on a feature branch, so syncing local `main` requires preserving unrelated user changes before branch/worktree operations.
- The requested workflow also asks to pull latest `main`; that must be done carefully to avoid overwriting unrelated uncommitted changes.

Phase 1 complete
