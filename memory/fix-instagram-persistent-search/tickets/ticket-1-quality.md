Stage 1 — Static Analysis

- No project linter is configured in this environment. Reviewed the changed files manually against existing repository style and kept the provider-layer change additive.

Stage 2 — Type Checking

- Ran:
  - `python -m compileall harnessiq\providers\playwright\browser.py harnessiq\providers\playwright\__init__.py harnessiq\providers\__init__.py harnessiq\integrations\instagram_playwright.py harnessiq\agents\instagram\agent.py harnessiq\agents\base\agent.py tests\test_instagram_playwright.py tests\test_instagram_agent.py`
- Result: passed.

Stage 3 — Unit Tests

- Ran:
  - `python -m unittest tests.test_instagram_playwright`
  - `python -m unittest tests.test_instagram_agent`
  - `python -m unittest tests.test_instagram_playwright tests.test_instagram_agent`
- Result: all passed.

Stage 4 — Integration & Contract Tests

- No separate live-browser integration suite is configured for the Instagram backend. Relied on deterministic lifecycle tests around the new reusable session object, backend close behavior, and agent cleanup behavior.

Stage 5 — Smoke & Manual Verification

- Ran:
  - `python -m harnessiq.cli instagram --help`
  - inline Python smoke script that instantiated `PlaywrightInstagramSearchBackend(search_interval_seconds=0)` and executed `search_keyword(keyword='ai educator', max_results=1)` against the real environment.
- Observed:
  - CLI help rendered successfully, confirming the Instagram command import path works on the updated main-based worktree.
  - The live backend no longer silently recorded an empty search when Google served an anti-bot page. It raised:
    - `RuntimeError`
    - `Google blocked Instagram discovery search for keyword 'ai educator' with a sorry interstitial at 'https://www.google.com/sorry/...'.`
- Confirmation:
  - The run-scoped browser/session lifecycle is active and the Google-block failure mode is now explicit instead of being misreported as a zero-result search.
