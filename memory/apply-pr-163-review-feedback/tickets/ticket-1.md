Title: Refactor Instagram agent tooling and Playwright helpers for PR #163 review feedback

Intent:
Apply the owner comments on PR #163 without changing the Instagram feature's user-visible behavior. The goal is to align the new Instagram agent with the repository's intended architecture by moving tool definitions into the tools/toolset layer, moving reusable Playwright helpers into the provider layer, and centralizing shared constants.

Scope:
- Move the Instagram search tool definition/handler factory out of the agent module into `harnessiq/tools`.
- Register the Instagram tool in the toolset catalog and rewire the agent to consume it from there.
- Extract reusable Playwright helper functions/constants into a new `harnessiq/providers/playwright` package and rewire the Instagram backend to call them.
- Update tests affected by the refactor.
- Do not refactor the LinkedIn Playwright integration as part of this ticket.
- Do not change the CLI contract or the durable-memory file schema for the Instagram agent.

Relevant Files:
- `harnessiq/agents/instagram/agent.py`: replace inline tool construction with tool import/wiring from the tool layer.
- `harnessiq/shared/instagram.py`: host shared constants and any reusable Instagram-specific tool metadata.
- `harnessiq/tools/instagram.py`: define the Instagram registered tool factory.
- `harnessiq/tools/__init__.py`: export the Instagram tool factory.
- `harnessiq/toolset/catalog.py`: register the Instagram tool family in the built-in catalog.
- `harnessiq/providers/playwright/__init__.py`: provider package export surface.
- `harnessiq/providers/playwright/browser.py`: Playwright lifecycle/page helper functions.
- `harnessiq/providers/__init__.py`: export provider-layer Playwright helpers if appropriate.
- `harnessiq/integrations/instagram_playwright.py`: consume provider helpers and shared constants.
- `tests/test_instagram_agent.py`: verify the agent still executes the Instagram search tool correctly after the tool-layer move.
- `tests/test_instagram_playwright.py`: verify the extracted helper behavior and integration wiring.
- `tests/test_toolset_registry.py`: verify Instagram tool visibility through the built-in toolset catalog if necessary.

Approach:
Create a small Instagram tools factory that produces the existing `instagram.search_keyword` tool while accepting instance-bound dependencies (`InstagramMemoryStore`, `InstagramSearchBackend`, config) as explicit inputs. Register that family in the built-in toolset catalog so the definitions live in the canonical tools layer. In parallel, introduce a new `harnessiq/providers/playwright` helper package for Playwright import/bootstrap, browser/context creation, page readiness waiting, and resilient page text/title access. The Instagram integration remains domain-specific and owns Google query orchestration plus URL filtering, but delegates generic browser mechanics to the provider layer. Shared constants move to `harnessiq/shared/instagram.py`.

Assumptions:
- The agent may still own domain-specific orchestration logic; only tool definitions/registration and generic Playwright mechanics need to move.
- The Instagram tool does not need module-level singleton registration because its handler depends on runtime state from an agent instance.
- The toolset catalog can instantiate the Instagram family with a zero-argument factory that returns the static/stub-capable definitions if needed; the agent can also call the same factory with live dependencies.

Acceptance Criteria:
- [ ] `InstagramKeywordDiscoveryAgent` no longer defines its Instagram search tool inline.
- [ ] The Instagram search tool is created from the main tools layer and registered in the toolset catalog.
- [ ] Module-level Instagram Playwright constants move out of `harnessiq/integrations/instagram_playwright.py` into a shared module.
- [ ] Generic Playwright helpers used by the Instagram backend live under `harnessiq/providers/playwright/`.
- [ ] Instagram agent, CLI, and Playwright tests pass after the refactor.
- [ ] No user-visible CLI or memory-schema regression is introduced.

Verification Steps:
1. Run targeted static analysis/type-aware execution by importing the changed modules and running the focused test suite.
2. Run `python -m pytest tests/test_instagram_agent.py tests/test_instagram_cli.py tests/test_instagram_playwright.py tests/test_toolset_registry.py tests/test_sdk_package.py`.
3. Confirm the Instagram agent still executes `instagram.search_keyword`, persists leads, and exposes the same CLI outputs via tests.

Dependencies:
- None.

Drift Guard:
This ticket must stay narrowly focused on PR #163 review feedback. It must not refactor unrelated agents, overhaul the wider LinkedIn browser stack, redesign the toolset system, or change the Instagram feature's user-facing workflow beyond the architectural moves requested by the reviewer.
