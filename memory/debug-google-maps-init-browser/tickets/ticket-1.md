Title: Open Google Maps during prospecting browser session bootstrap
Issue URL: https://github.com/cerredz/HarnessHub/issues/275
PR URL: https://github.com/cerredz/HarnessHub/pull/277

Intent:
Restore a usable operator bootstrap flow for the Google Maps prospecting agent so `harnessiq prospecting init-browser` opens directly into Google Maps and lets the user authenticate or inspect the session without landing on a blank page.

Scope:
- Update the Google Maps Playwright session startup path so browser initialization navigates to a deterministic Google Maps entry URL.
- Preserve persistent-session behavior and existing browser tool bindings.
- Add regression tests for startup navigation and any related CLI bootstrap behavior.
- Do not change prospecting agent search logic, durable memory schema, or listing extraction behavior.

Relevant Files:
- `harnessiq/integrations/google_maps_playwright.py`: add deterministic startup navigation and any small startup helpers/constants needed by the session wrapper.
- `tests/test_google_maps_playwright.py`: add regression coverage that session startup navigates to Google Maps and still preserves existing browser tool behavior.
- `tests/test_prospecting_cli.py`: add or adjust CLI-level coverage if needed to assert the init-browser path constructs the session correctly.

Approach:
Align the Google Maps session bootstrap with the adjacent LinkedIn browser bootstrap pattern: session startup should own the first navigation instead of leaving the initial page at the browser default. The most coherent implementation is to introduce a Google Maps bootstrap URL constant in the integration module and navigate the first live page to that URL during `PlaywrightGoogleMapsSession.start()`, using the existing page-ready wait helper so timing stays consistent with other navigation operations. Tests should mock the browser/page objects and assert that startup invokes `goto(...)` with the expected URL.

Assumptions:
- The blank-screen defect is caused by missing startup navigation rather than a broken local Playwright installation.
- Opening Google Maps on startup is the intended product behavior for `prospecting init-browser`.
- Reusing the first page in a persistent context is acceptable and consistent with the current session model.
- No changes are required to the durable memory layout or session directory semantics.

Acceptance Criteria:
- [ ] `harnessiq prospecting init-browser` opens a Playwright-backed browser session on a Google Maps URL instead of leaving the first tab blank.
- [ ] The persistent session directory behavior remains intact for future prospecting runs.
- [ ] Automated tests fail if startup navigation to Google Maps is removed or regresses.
- [ ] Existing Google Maps browser tool tests continue to pass after the change.

Verification Steps:
1. Run targeted static analysis / syntax checks on the modified files.
2. Run targeted unit tests for `tests/test_google_maps_playwright.py` and `tests/test_prospecting_cli.py`.
3. Manually invoke `harnessiq prospecting init-browser --agent nj-dentists` and confirm the browser opens on Google Maps rather than `about:blank`.
4. Confirm the browser-data directory still persists under the agent memory path.

Dependencies:
- None.

Drift Guard:
This ticket must stay focused on browser bootstrap reliability for the prospecting harness. It must not expand into Google Maps extraction heuristics, prompt changes, prospect qualification logic, model-provider changes, or general Playwright refactors outside what is strictly necessary to make initialization deterministic and testable.
