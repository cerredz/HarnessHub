Stage 1 — Static Analysis

- No project linter is configured.
- Manually reviewed:
  - `harnessiq/providers/playwright/browser.py`
  - `harnessiq/shared/instagram.py`
  - `harnessiq/integrations/instagram_playwright.py`
  - `tests/test_instagram_playwright.py`
- Result: kept the provider-layer change additive and scoped the new hardening policy to Instagram.

Stage 2 — Type Checking

- Ran:
  - `python -m compileall harnessiq\providers\playwright\browser.py harnessiq\shared\instagram.py harnessiq\integrations\instagram_playwright.py tests\test_instagram_playwright.py`
- Result: passed.

Stage 3 — Unit Tests

- Ran:
  - `python -m pytest tests\test_instagram_playwright.py tests\test_instagram_agent.py tests\test_instagram_cli.py tests\test_cli_runners.py -q`
- Result: `53 passed in 4.01s`.

Stage 4 — Integration & Contract Tests

- No separate browser integration suite exists in the repo.
- Relied on targeted regression tests plus live CLI smoke verification against the real Playwright backend.

Stage 5 — Smoke & Manual Verification

- Reproduced the pre-fix behavior with the CLI probe:
  - one reused session/page was already in use,
  - but both searches hit Google’s `sorry` interstitial in headless mode.
- Verified the root fingerprint issue separately:
  - default headless Chromium exposed `HeadlessChrome/...` in `navigator.userAgent`.
- Re-ran the CLI probe after the fix:
  - command:
    - `python -m harnessiq.cli instagram run --agent probe --memory-root memory\fix-instagram-browser-reuse\runtime --model-factory memory.fix_instagram_browser_reuse.cli_probe:create_two_search_model --search-backend-factory memory.fix_instagram_browser_reuse.cli_probe:create_logging_search_backend --max-cycles 2`
  - environment:
    - `HARNESSIQ_INSTAGRAM_HEADLESS=true`
  - observed result:
    - CLI returned `email_count: 7`
    - backend log showed one reused session id and one reused page id across both searches
    - lead persistence succeeded for both `ai educator` and `stem creator`

Confirmation:

- The Instagram backend now keeps one reused browser session/page and can successfully load real search results in the reproduced headless CLI path.
