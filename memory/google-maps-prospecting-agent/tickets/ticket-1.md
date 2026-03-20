Title: Add public browser and prospecting shared tools

Issue URL: https://github.com/cerredz/HarnessHub/issues/192

Intent:
Create the reusable public tool surface required by the Google Maps prospecting harness without hard-coding prospecting logic inside the agent class. This ticket establishes the shared browser tool family and the shared prospecting tool factories/constants so the new harness can compose them cleanly and future agents can reuse them.

Scope:
- Add a public browser tool family with canonical tool definitions for browser navigation and extraction flows needed by the prospecting agent.
- Add public shared tool factories/constants for `EVALUATE_COMPANY` and `SEARCH_OR_SUMMARIZE`.
- Export the new tools/constants from the public `harnessiq.tools` and `harnessiq.shared.tools` surfaces.
- Update tool registry/catalog tests and any built-in ordering expectations that are intentionally affected.
- Do not implement the prospecting agent class, CLI commands, or memory store in this ticket.

Relevant Files:
- `harnessiq/shared/tools.py`: add public tool key constants and exports.
- `harnessiq/tools/browser.py` or `harnessiq/tools/browser/__init__.py`: add browser tool definitions/factory.
- `harnessiq/tools/eval/evaluate_company.py`: add shared evaluation tool factory.
- `harnessiq/tools/search/search_or_summarize.py`: add shared search-or-summarize tool factory.
- `harnessiq/tools/__init__.py`: export new public factories/constants.
- `harnessiq/tools/builtin.py`: include built-in tool families only if the final design supports dependency-free registration.
- `harnessiq/toolset/catalog.py`: add catalog metadata if the tools belong in the public tool catalog.
- `tests/test_tools.py`: cover constants/registry/export behavior.
- `tests/test_toolset_registry.py`: cover catalog lookup if applicable.

Approach:
Define these tools as public shared factories that return `RegisteredTool` instances while allowing dependency injection through closures where runtime services are needed. The browser family should expose canonical reusable `ToolDefinition` objects and factory helpers rather than baking Playwright directly into the tool module. `EVALUATE_COMPANY` and `SEARCH_OR_SUMMARIZE` should accept injected handlers or model-backed runners so the agent can supply deterministic sub-call behavior while the public key/schema stay shared and stable.

Assumptions:
- Public shared tools do not have to be dependency-free built-ins if they require injected runtime services.
- The repo’s public tool surface is primarily `harnessiq.shared.tools`, `harnessiq.tools`, and optionally `harnessiq.toolset`.
- Browser tools can be public even if their concrete Playwright handlers are created by an integration module.

Acceptance Criteria:
- [ ] Public key constants exist for the new browser/prospecting tools.
- [ ] `harnessiq.tools` exports the new tool factories/definitions needed by the prospecting agent.
- [ ] Browser tool definitions are reusable and not hard-coded to LinkedIn.
- [ ] `EVALUATE_COMPANY` and `SEARCH_OR_SUMMARIZE` have stable schemas and deterministic handlers/factory contracts.
- [ ] Tests cover the new public tool surface and pass.

Verification Steps:
- Run targeted tool and registry tests for new constants/exports.
- Run any catalog/toolset tests impacted by new public tool entries.
- Manually verify the new factories can be imported from `harnessiq.tools`.

Dependencies:
- None.

Drift Guard:
This ticket must not implement the prospecting harness itself, the CLI flow, or any sink/memory architecture rewrite. Keep the focus on defining the reusable public tool surface and the minimal support needed for later tickets to consume it.
