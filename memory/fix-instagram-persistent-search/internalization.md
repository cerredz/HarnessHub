### 1a: Structural Survey

- Top-level architecture follows the file index in `artifacts/file_index.md`: shipped runtime code lives under `harnessiq/`, repository guidance under `artifacts/`, and public usage docs in `README.md` / `docs/`.
- `harnessiq/agents/base/agent.py` owns the generic run loop, parameter refresh, transcript lifecycle, context resets, and final run completion. Concrete harnesses are expected to specialize prompts, parameter sections, and tool wiring, but there is no generic teardown hook after `run()`.
- `harnessiq/agents/instagram/agent.py` is a thin Instagram discovery harness. It binds a single `instagram.search_keyword` tool to a memory store plus an injected `InstagramSearchBackend`, refreshes parameter sections after each search, and exposes helper reads for persisted emails/leads/search history.
- `harnessiq/tools/instagram.py` is the deterministic runtime tool layer for Instagram discovery. It validates keyword/max-results input, guards against duplicate searches via durable memory, delegates execution to `InstagramSearchBackend.search_keyword()`, then persists the resulting search record and merged leads.
- `harnessiq/shared/instagram.py` is the domain contract: runtime constants, Google query builder, email regex extraction helpers, typed search/lead records, and the file-backed `InstagramMemoryStore`.
- `harnessiq/integrations/instagram_playwright.py` is the current browser execution layer. It builds the Google query URL, opens Playwright, opens Chromium, loads one search page, opens result tabs, extracts emails, and returns an `InstagramSearchExecution`.
- `harnessiq/providers/playwright/browser.py` is the shared browser helper layer. It currently exposes only short-lived contextmanager helpers (`playwright_runtime`, `chromium_context`) plus page utilities. It does not expose a reusable long-lived session abstraction.
- `harnessiq/cli/instagram/commands.py` prepares memory, sets `HARNESSIQ_INSTAGRAM_SESSION_DIR` to `memory/.../browser-data`, constructs the backend once per run, then passes that backend into `InstagramKeywordDiscoveryAgent.from_memory(...)`.
- Tests are split cleanly: `tests/test_instagram_agent.py` covers harness and memory behavior, while `tests/test_instagram_playwright.py` currently covers only URL normalization helpers. There is no test coverage for backend session reuse, browser lifecycle, or Google block-page detection.
- Relevant convention from adjacent code: `harnessiq/integrations/linkedin_playwright.py` manages a long-lived browser session object rather than reopening the browser for every tool call. That is the nearest existing pattern for persistent browser-backed agent execution.

### 1b: Task Cross-Reference

- “the agent should have already been using a persistent browser session” maps to the mismatch between `harnessiq/cli/instagram/commands.py` and `harnessiq/integrations/instagram_playwright.py`:
  - The CLI creates one backend object for the whole run and assigns a persistent browser-data directory.
  - The backend immediately defeats that design by opening and closing Playwright plus Chromium inside every `search_keyword()` call.
- “searching different searches into the browser repeatedly every few seconds” maps to the execution lifecycle inside `harnessiq/integrations/instagram_playwright.py` and the generic Playwright helper layer in `harnessiq/providers/playwright/browser.py`. The current implementation reuses neither the browser runtime nor the Google search page across keyword searches.
- “regex the emails and then store the results” is already mostly implemented correctly in `harnessiq/shared/instagram.py` and `harnessiq/tools/instagram.py`. The persistence and dedupe path exists; the main failure is upstream in browser execution.
- The observed runtime behavior from manual verification is that Google can serve `https://www.google.com/sorry/...` anti-bot pages. Today that failure mode is silently persisted as an empty search result instead of being surfaced as a concrete runtime blocker.
- Files directly touched by the change:
  - `harnessiq/providers/playwright/browser.py`
  - `harnessiq/integrations/instagram_playwright.py`
  - `harnessiq/agents/instagram/agent.py`
  - `tests/test_instagram_playwright.py`
  - `tests/test_instagram_agent.py`
- Possible secondary touch if needed:
  - `harnessiq/providers/playwright/__init__.py` if the shared provider layer exports change.

### 1c: Assumption & Risk Inventory

- Assumption: the intended persistent-session behavior is one backend instance per agent run, not one Chromium context per keyword. This is strongly implied by the CLI already assigning a stable `browser-data` directory and by the user’s request.
- Assumption: a small delay between searches belongs in the Playwright integration layer rather than in the LLM loop. This keeps the agent/tool contract simple and places browser-throttling next to browser execution.
- Assumption: surfacing Google anti-bot interstitials as explicit runtime errors is preferable to silently recording zero-result searches. Silent failure is currently misleading and makes debugging far harder.
- Risk: adding a persistent session without a teardown path can leak Playwright/Chromium processes. The fix must include deterministic cleanup on both successful and failing runs.
- Risk: changing shared Playwright helpers can affect adjacent integrations if done too broadly. The provider-layer addition should be additive and keep current helpers intact.
- Risk: browser-driven tests can become brittle if they depend on real Playwright. The new tests should use fakes/mocks around the session abstraction instead of requiring live browser automation.

Phase 1 complete
