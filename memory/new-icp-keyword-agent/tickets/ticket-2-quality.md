Stage 1 — Static Analysis:
- No configured linter in this environment. Reviewed the new agent and Playwright backend for consistency with existing agent/integration patterns.

Stage 2 — Type Checking:
- No configured type checker in this environment. Added annotations on the new agent constructor, `from_memory`, tool handler, and Playwright backend helpers.

Stage 3 — Unit Tests:
- Verified with:
  - `python -m unittest tests.test_instagram_agent`

Stage 4 — Integration & Contract Tests:
- Verified with:
  - `python -m unittest tests.test_instagram_playwright`
  - `python -m compileall harnessiq\\shared\\instagram.py harnessiq\\agents\\instagram harnessiq\\cli\\instagram harnessiq\\integrations\\instagram_playwright.py`

Stage 5 — Smoke & Manual Verification:
- Confirmed the agent injects parameter sections in the requested order: ICP Profiles, Recent Searches, Recent Search Results.
- Confirmed search-state mutations refresh parameter sections before the next model turn.
- Confirmed the Playwright backend explicitly waits for `domcontentloaded`, `load`, and then `networkidle` with fallback tolerance.
