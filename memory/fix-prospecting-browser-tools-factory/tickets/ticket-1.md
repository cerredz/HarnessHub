Title: Fix the Google Maps browser-tool factory name collision

Intent: Restore the `prospecting run` startup path by ensuring the Google Maps Playwright integration binds the shared browser tool definitions instead of recursively resolving its own CLI factory name.

Scope:
- Update the Google Maps Playwright integration so `PlaywrightGoogleMapsSession.build_tools()` calls the shared browser-tool binder through an unambiguous symbol.
- Add regression coverage that executes `session.build_tools()`.
- Verify the user’s existing `python -m harnessiq.cli prospecting run ...` command starts without the reported `TypeError`.
- Do not change the public factory import path, prospecting agent prompts, or durable-memory semantics.

Relevant Files:
- `harnessiq/integrations/google_maps_playwright.py`: alias the shared browser factory import and use that alias inside `build_tools()`.
- `tests/test_google_maps_playwright.py`: add a regression test for `session.build_tools()`.
- `memory/fix-prospecting-browser-tools-factory/tickets/ticket-1-quality.md`: record verification results.
- `memory/fix-prospecting-browser-tools-factory/tickets/ticket-1-critique.md`: record post-implementation critique and improvements.

Approach: Keep the exported module-level `create_browser_tools()` function intact for CLI compatibility, but disambiguate the imported shared binder with an alias so `build_tools()` cannot accidentally resolve the module’s own zero-argument factory. Cover the failure mode by constructing a session with a fake page and asserting that all canonical browser tools bind successfully.

Assumptions:
- `harnessiq.tools.browser.create_browser_tools(handlers=...)` remains the canonical binding helper.
- The existing traceback is caused by Python global name resolution in `harnessiq.integrations.google_maps_playwright`.
- The user’s command should continue to reference `harnessiq.integrations.google_maps_playwright:create_browser_tools`.

Acceptance Criteria:
- [ ] `PlaywrightGoogleMapsSession.build_tools()` returns the shared browser tool set without raising `TypeError`.
- [ ] The Google Maps Playwright tests cover the regression.
- [ ] Relevant targeted tests pass.
- [ ] The user’s exact prospecting command no longer fails with `create_browser_tools() got an unexpected keyword argument 'handlers'`.

Verification Steps:
- Run `python -m pytest tests/test_google_maps_playwright.py tests/test_prospecting_tools.py tests/test_prospecting_cli.py -q`.
- Run the user’s exact `python -m harnessiq.cli prospecting run ...` command and confirm startup proceeds beyond the prior traceback.

Dependencies: None.

Drift Guard: This ticket must not redesign the browser tool abstraction, rename the CLI factory import path, or broaden into unrelated Playwright/prospecting behavior changes unless a new runtime failure discovered during verification makes that strictly necessary to satisfy the user’s command.
