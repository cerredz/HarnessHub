### 1a: Structural Survey

- The authoritative runtime code lives under `harnessiq/`, with tests under `tests/`, generated architecture guidance under `artifacts/`, and durable local engineering/runtime state under `memory/`.
- The Instagram harness is split across four main layers:
  - `harnessiq/agents/instagram/agent.py`: the concrete agent loop and lifecycle.
  - `harnessiq/shared/instagram.py`: constants, runtime parameter specs, and the `InstagramMemoryStore`.
  - `harnessiq/integrations/instagram_playwright.py`: the deterministic Google-to-Instagram Playwright backend.
  - `harnessiq/cli/runners/instagram.py` plus `harnessiq/cli/adapters/instagram.py`: CLI wiring that prepares memory, sets the browser session dir, and constructs the backend for a run.
- Shared Playwright browser lifecycle helpers live in `harnessiq/providers/playwright/browser.py`. The current helper supports a reusable `PlaywrightBrowserSession` with one live context and page reuse through `get_or_create_page()`.
- The Instagram CLI path already sets `HARNESSIQ_INSTAGRAM_SESSION_DIR` to `memory/<agent>/browser-data`, so the intended architecture is a persistent Chromium user-data directory per Instagram agent memory folder.
- The current test surface is focused and useful:
  - `tests/test_instagram_playwright.py` covers query building, URL normalization, fallback behavior, explicit Google block detection, and backend-level session reuse.
  - `tests/test_instagram_agent.py` covers the Instagram loop and search-tool integration.
  - `tests/test_instagram_cli.py` and `tests/test_cli_runners.py` cover CLI wiring and environment setup.
- Relevant adjacent patterns:
  - `harnessiq/integrations/google_maps_playwright.py` also uses persistent Playwright contexts.
  - LinkedIn and prospecting runners treat browser session directories as durable per-agent state and expect one browser session per run, not one browser launch per tool call.

### 1b: Task Cross-Reference

- User request: the Instagram agent “keeps using different browsers and not just different tabs.”
  - This maps to `harnessiq/integrations/instagram_playwright.py` and `harnessiq/providers/playwright/browser.py`, because the backend owns browser/context/page reuse.
  - It also maps to CLI construction in `harnessiq/cli/runners/instagram.py` and `harnessiq/cli/adapters/instagram.py`, because repeated backend construction would create repeated browser sessions.
- User request: Google/search results may be detecting the browser as AI/automation and “the search results are not popping up.”
  - This maps to the Instagram browser hardening constants in `harnessiq/shared/instagram.py` and the page-navigation/result-detection logic in `harnessiq/integrations/instagram_playwright.py`.
  - The current hardening only applies one launch arg and a small init script. There is no more realistic browser surface, no explicit user-agent override, and no recovery path when a persistent context restores multiple tabs or starts on an unexpected page.
- User request: use the repo CLI to test with `max_cycles=2` until fixed.
  - This maps to the dedicated CLI flow in `harnessiq/cli/instagram/commands.py` and `harnessiq/cli/runners/instagram.py`.
  - Live verification must use `harnessiq instagram run ... --max-cycles 2` or the equivalent module entrypoint.
- Files most likely in scope:
  - `harnessiq/integrations/instagram_playwright.py`
  - `harnessiq/providers/playwright/browser.py`
  - `harnessiq/shared/instagram.py`
  - `tests/test_instagram_playwright.py`
  - potentially `tests/test_cli_runners.py` if runner/session behavior changes.
- Existing behavior that must be preserved:
  - The backend should remain reusable within one run.
  - The CLI should keep defaulting the browser session dir to `memory/<agent>/browser-data`.
  - Search execution should still produce the same `InstagramSearchExecution` contract and continue surfacing explicit Google block errors.

### 1c: Assumption & Risk Inventory

- Assumption: “different browsers” means multiple Chromium windows/contexts are being created or restored when one persistent session should be reused for the whole run.
- Assumption: the right UX is one persistent browser context per run and one stable search tab within that context, with reused tabs preferred over opening new windows.
- Assumption: stronger browser hardening is acceptable as long as it remains opt-out through the existing `HARNESSIQ_INSTAGRAM_DISABLE_BROWSER_HARDENING` path.
- Risk: persistent contexts can restore multiple tabs from earlier runs; blindly using `context.pages[0]` can select an arbitrary restored tab instead of the dedicated search tab.
- Risk: changing generic Playwright session behavior too broadly could affect adjacent integrations. The safest change is additive or scoped to the Instagram backend.
- Risk: live CLI reproduction depends on local model/browser availability and may fail for reasons outside the browser fix. Unit tests must cover the deterministic parts so the behavior is still verifiable offline.

Phase 1 complete
