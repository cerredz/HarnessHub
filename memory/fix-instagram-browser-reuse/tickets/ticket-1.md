Title: Harden the Instagram Playwright browser context for reused CLI sessions

Intent: Keep the Instagram agent on one reused browser session/page per run while removing the browser fingerprints that caused Google to serve anti-bot interstitials instead of real search results.

Scope:
- Extend the shared Playwright session helper so integrations can pass explicit browser-context options.
- Update the Instagram Playwright backend to supply a normal Chrome user agent and a small set of realistic browser-context defaults.
- Preserve the existing run-scoped session reuse and deterministic search contract.
- Add regression coverage for the new hardening inputs.
- Do not redesign the Instagram agent loop or change the durable memory schema.

Relevant Files:
- `harnessiq/providers/playwright/browser.py`: accept integration-supplied context options and apply them to created browser contexts.
- `harnessiq/shared/instagram.py`: centralize Instagram browser hardening constants.
- `harnessiq/integrations/instagram_playwright.py`: pass hardened context options into the reusable Playwright session.
- `tests/test_instagram_playwright.py`: verify the hardened defaults and explicit overrides.

Approach: The root failure in live CLI reproduction was not session reuse; the backend already reused one session and one page. The actual issue was the browser fingerprint, especially `HeadlessChrome` in the user agent when headless mode was enabled. The fix therefore keeps the existing run-scoped session model and makes the session helper configurable so the Instagram integration can provide a realistic Chrome user agent, locale, timezone, color scheme, and accept-language header. The existing init-script hardening remains in place and is extended slightly to fill obvious browser-surface gaps.

Assumptions:
- A standard Chrome user agent and realistic browser-context metadata are sufficient to avoid the specific Google anti-bot response seen in the local CLI reproduction.
- Instagram should continue to own its own browser hardening policy instead of pushing those defaults onto every Playwright-backed integration.
- The existing `HARNESSIQ_INSTAGRAM_DISABLE_BROWSER_HARDENING` path should still disable both launch-arg/init-script hardening and the new context-option hardening.

Acceptance Criteria:
- [ ] The shared Playwright session helper accepts browser-context options without breaking existing integrations.
- [ ] The Instagram Playwright backend passes hardened context options by default.
- [ ] Instagram Playwright tests cover both the new default hardening and explicit override behavior.
- [ ] A live `harnessiq instagram run ... --max-cycles 2` probe no longer hits the Google sorry page in the reproduced headless scenario and persists real leads/emails.

Verification Steps:
- Static analysis: inspect changed files for style and API consistency.
- Type checking: run `python -m compileall harnessiq\providers\playwright\browser.py harnessiq\shared\instagram.py harnessiq\integrations\instagram_playwright.py tests\test_instagram_playwright.py`.
- Unit tests: run `python -m pytest tests\test_instagram_playwright.py tests\test_instagram_agent.py tests\test_instagram_cli.py tests\test_cli_runners.py -q`.
- Smoke verification: run `python -m harnessiq.cli instagram run --agent probe --memory-root memory\fix-instagram-browser-reuse\runtime --model-factory memory.fix_instagram_browser_reuse.cli_probe:create_two_search_model --search-backend-factory memory.fix_instagram_browser_reuse.cli_probe:create_logging_search_backend --max-cycles 2` with `HARNESSIQ_INSTAGRAM_HEADLESS=true`.

Dependencies: None

Drift Guard: This ticket must not broaden Playwright behavior for unrelated agents beyond making context options possible, and it must not redesign Instagram persistence or the agent loop in response to a browser-fingerprinting failure.
