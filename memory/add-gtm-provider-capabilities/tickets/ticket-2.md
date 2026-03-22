# Ticket 2: Add InboxApp Provider and Tool Registration

## Title
Add the InboxApp provider family and register its tooling surface

## Issue URL
https://github.com/cerredz/HarnessHub/issues/172

## Intent
InboxApp appears in the user-supplied GTM stack as a "superhuman for X" product and exposes documented public API endpoints. This ticket adds an `inboxapp` provider family and `inboxapp.request` tool so the SDK can access InboxApp capabilities through the standard provider-backed tool layer.

## Scope
In scope:
- Add `harnessiq/providers/inboxapp/` with credentials/auth helpers, client, operation catalog, and exports.
- Add `harnessiq/tools/inboxapp/` with the MCP-style tool definition/factory.
- Register `inboxapp.request` in shared tool constants and the toolset catalog.
- Add provider-level tests and any minimal package/export wiring required.

Out of scope:
- Any social-channel-specific agent harnesses.
- Webhook consumer implementations.
- Undocumented or private InboxApp endpoints.

## Relevant Files
- `harnessiq/providers/inboxapp/__init__.py`: create curated InboxApp exports.
- `harnessiq/providers/inboxapp/api.py`: create base URL and bearer auth helpers.
- `harnessiq/providers/inboxapp/client.py`: create `InboxAppCredentials` and `InboxAppClient`.
- `harnessiq/providers/inboxapp/operations.py`: create InboxApp operation catalog and request preparation helpers.
- `harnessiq/tools/inboxapp/__init__.py`: create InboxApp tool exports.
- `harnessiq/tools/inboxapp/operations.py`: create `inboxapp.request` tool definition/factory.
- `harnessiq/shared/tools.py`: add `INBOXAPP_REQUEST` constant/export.
- `harnessiq/toolset/catalog.py`: register the InboxApp provider family in metadata and factory dispatch.
- `tests/test_inboxapp_provider.py`: create unit coverage.

## Approach
Follow the existing provider/tool convention with a single MCP-style request tool.

- Implement `InboxAppCredentials` as a frozen dataclass with bearer token auth.
- Use the public API docs to define a conservative but useful operation set around core CRM-style and messaging surfaces, such as:
  - list statuses
  - get status
  - list prospects
  - get prospect
  - list threads
  - get thread
  - create status
  - update status
- Build request preparation around explicit method/path metadata and optional `path_params`, `query`, and `payload`.
- Register `inboxapp.request` so the toolset catalog exposes the new family.

Namespace choice is fixed by clarification: code and public tool family use `inboxapp`, not generic `inbox`.

## Assumptions
- InboxApp uses bearer-token authentication for the documented API reference.
- A conservative operation set based on the clearly documented endpoint reference is enough for initial registration.
- `inboxapp` is the correct package and tool namespace.

## Acceptance Criteria
- [ ] `from harnessiq.providers.inboxapp import InboxAppClient, InboxAppCredentials` works.
- [ ] `from harnessiq.tools.inboxapp import create_inboxapp_tools` works.
- [ ] `INBOXAPP_REQUEST` is defined and exported from `harnessiq.shared.tools`.
- [ ] `inboxapp.request` is listed by `ToolsetRegistry().list()`.
- [ ] InboxApp credentials reject blank API keys.
- [ ] The request-preparation layer validates required path parameters and payload requirements.
- [ ] `create_inboxapp_tools(...)` returns a registerable `RegisteredTool` tuple.
- [ ] `tests/test_inboxapp_provider.py` passes.

## Verification Steps
1. `python -m pytest tests/test_inboxapp_provider.py -v`
2. `python -m pytest tests/test_toolset_registry.py -v`
3. `python -c "from harnessiq.toolset import list_tools; print([e.key for e in list_tools() if e.family == 'inboxapp'])"`
4. `python -c "from harnessiq.providers.inboxapp import InboxAppCredentials; print(InboxAppCredentials(api_key='test').as_redacted_dict())"`

## Dependencies
None.

## Drift Guard
Do not introduce a generic `inbox` namespace. Do not build social-network-specific workflow logic into this ticket. Keep the provider limited to documented public endpoints and the standard provider-backed tool surface.
