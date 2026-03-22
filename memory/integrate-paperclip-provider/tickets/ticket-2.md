Title: Register Paperclip in the tool and toolset layers

Intent:
Expose the Paperclip provider through Harnessiq’s reusable `*.request` tool pattern so agents and callers can invoke Paperclip functionality through the standard provider-backed tooling surface.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/167

Scope:
- Add the `paperclip.request` MCP-style tool factory under `harnessiq.tools.paperclip`.
- Register the Paperclip tool key constant and public exports.
- Register the provider in the static toolset catalog and lazy factory map.
- Add tests covering tool registration, tool execution, and toolset metadata visibility.
- Do not add Paperclip-specific agent behavior or bespoke higher-level tools in this ticket.

Relevant Files:
- `harnessiq/tools/paperclip/__init__.py`: public tool exports for the Paperclip family.
- `harnessiq/tools/paperclip/operations.py`: `paperclip.request` tool definition and handler.
- `harnessiq/shared/tools.py`: provider tool key constant export.
- `harnessiq/tools/__init__.py`: public tool-layer export surface.
- `harnessiq/toolset/catalog.py`: static provider metadata and lazy factory registration.
- `harnessiq/providers/__init__.py`: provider-level public export wiring if needed.
- `tests/test_toolset_registry.py`: toolset catalog visibility assertions.
- `tests/test_paperclip_provider.py`: tool execution assertions for the provider-backed request tool.

Approach:
Follow the established `create_<provider>_tools()` pattern used across Exa, Creatify, and Google Drive. Build a single `RegisteredTool` whose schema exposes `operation`, `path_params`, `query`, `payload`, and optional `run_id`. The handler delegates to `PaperclipClient.prepare_request()` and the shared request executor. Update the static tool catalog with the new `paperclip.request` entry and provider factory mapping, then extend tests to assert the new family is visible and credential-gated.

Assumptions:
- Ticket 1’s provider package exists and is the only dependency this ticket needs.
- `paperclip.request` is the correct public key format given existing provider conventions.
- The public descriptions should explicitly frame Paperclip as an orchestration/control-plane API rather than an LLM provider.

Acceptance Criteria:
- [ ] `create_paperclip_tools()` returns a registerable `RegisteredTool` tuple.
- [ ] The tool definition key is `paperclip.request`.
- [ ] The tool supports the curated operation subset and forwards optional run-id headers.
- [ ] `harnessiq.toolset.list_tools()` includes a credential-gated `paperclip.request` entry in the `paperclip` family.
- [ ] `get_tool("paperclip.request")` and `get_family("paperclip")` require credentials and resolve correctly when credentials are provided.
- [ ] Registration and toolset tests pass without regressing existing provider families.

Verification Steps:
- Run `tests/test_paperclip_provider.py`.
- Run `tests/test_toolset_registry.py`.
- Smoke-check direct imports from `harnessiq.tools.paperclip` and toolset resolution for the new family.

Dependencies:
- Ticket 1

Drift Guard:
This ticket must stay inside the reusable provider-backed tooling layer. It must not add Paperclip-specific business logic, agent harness behavior, or ad hoc convenience wrappers beyond the standard `paperclip.request` tool surface.
