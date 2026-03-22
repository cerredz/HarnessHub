Title: Reuse one Instagram Playwright session across repeated keyword searches

Intent: Make the Instagram discovery path behave like a persistent browser-driven agent run instead of a sequence of isolated one-off searches. The goal is to keep the browser session and search page alive across keyword searches, preserve the existing email-regex and durable-memory flow, and surface concrete Google blocking failures when the browser never reaches real results.

Scope:
- Add a reusable Playwright browser-session abstraction in the shared provider layer without breaking current short-lived helper functions.
- Update the Instagram Playwright backend to lazily start once, reuse one search page across multiple `search_keyword()` calls, and expose deterministic shutdown.
- Update the Instagram agent lifecycle so any closeable backend is shut down after a run completes or errors.
- Add regression tests for session reuse, cleanup, and explicit Google-block detection.
- Do not add a new top-level package, change the durable Instagram memory schema, or redesign the CLI contract beyond what is needed to preserve the current run path.

Relevant Files:
- `harnessiq/providers/playwright/browser.py`: add a reusable managed browser session abstraction.
- `harnessiq/providers/playwright/__init__.py`: export the new session abstraction if needed.
- `harnessiq/integrations/instagram_playwright.py`: reuse the session/page across searches, add throttling/block detection, expose close().
- `harnessiq/agents/instagram/agent.py`: close the backend after runs.
- `tests/test_instagram_playwright.py`: add backend lifecycle regression coverage.
- `tests/test_instagram_agent.py`: add harness cleanup regression coverage.

Approach: Introduce a narrow, additive session object in the provider layer that owns Playwright startup, Chromium context creation, page access, and teardown. Refactor the Instagram backend to hold one session object and one reusable Google search page for the lifetime of the backend instance, while continuing to open short-lived detail tabs per candidate result. Add explicit detection for Google anti-bot interstitial pages so the backend fails loudly instead of persisting misleading empty searches. Keep cleanup deterministic by closing the backend from the Instagram agent’s run lifecycle.

Assumptions:
- A backend instance is intended to live for the duration of a single agent run.
- The CLI’s current `HARNESSIQ_INSTAGRAM_SESSION_DIR` behavior should continue to control persistent browser storage on disk.
- The durable lead/search persistence contract in `harnessiq/shared/instagram.py` remains correct and should not change.

Acceptance Criteria:
- [ ] Repeated `search_keyword()` calls on one `PlaywrightInstagramSearchBackend` instance reuse a single Playwright/Chromium session instead of relaunching the browser each time.
- [ ] The backend keeps a reusable Google search page alive across searches while still opening and closing detail tabs per candidate result.
- [ ] The Instagram agent closes any closeable backend after `run()` completes or raises.
- [ ] Google anti-bot / interstitial pages are surfaced as explicit runtime errors instead of silently returning empty result sets.
- [ ] Regression tests cover session reuse and backend cleanup.

Verification Steps:
- Static analysis: inspect changed files for style and repository convention compliance.
- Type checking: run `python -m compileall` on changed Python modules.
- Unit tests: run `python -m unittest tests.test_instagram_playwright tests.test_instagram_agent`.
- Integration tests: no separate live-browser integration suite is configured; rely on deterministic mocked lifecycle tests for the new session behavior.
- Smoke verification: run a targeted local Instagram CLI execution path if feasible and record whether the environment reaches Google results or the explicit block-page error.

Dependencies: None

Drift Guard: This ticket must not redesign the Instagram memory schema, add new public product surfaces unrelated to Instagram search lifecycle, or make broad changes to unrelated browser integrations. The change is specifically about making the existing Instagram agent and Playwright layers cooperate around one persistent run-scoped browser session.
