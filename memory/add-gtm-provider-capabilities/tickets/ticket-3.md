# Ticket 3: Add Serper Provider and Tool Registration

## Title
Add the Serper provider family and register a conservative search tooling surface

## Issue URL
https://github.com/cerredz/HarnessHub/issues/173

## Intent
Serper is the documented public SERP API in the user-supplied GTM stack. This ticket adds a first-class `serper` provider family plus `serper.request` so agents can perform deterministic search lookups through the provider layer rather than raw HTTP calls.

## Scope
In scope:
- Add `harnessiq/providers/serper/` with credentials/auth helpers, client, operation catalog, and exports.
- Add `harnessiq/tools/serper/` with the MCP-style tool definition/factory.
- Register `serper.request` in shared tool constants and the toolset catalog.
- Add provider-level tests and any minimal package/export wiring required.

Out of scope:
- Exhaustive support for every possible Serper mode if the official public surface is broader than what can be grounded safely from docs.
- Any scraping logic outside Serper’s API.
- Serper-specific agents or CLI commands.

## Relevant Files
- `harnessiq/providers/serper/__init__.py`: create curated Serper exports.
- `harnessiq/providers/serper/api.py`: create base URL and auth/header helpers.
- `harnessiq/providers/serper/client.py`: create `SerperCredentials` and `SerperClient`.
- `harnessiq/providers/serper/operations.py`: create Serper operation catalog and request preparation helpers.
- `harnessiq/tools/serper/__init__.py`: create Serper tool exports.
- `harnessiq/tools/serper/operations.py`: create `serper.request` tool definition/factory.
- `harnessiq/shared/tools.py`: add `SERPER_REQUEST` constant/export.
- `harnessiq/toolset/catalog.py`: register the Serper provider family in metadata and factory dispatch.
- `tests/test_serper_provider.py`: create unit coverage.

## Approach
Implement Serper conservatively, using only operations that can be defended from the official public API surface.

- Define `SerperCredentials` as a frozen dataclass with API key, base URL, timeout, masking, and redacted serialization.
- Implement request auth through the documented API key header.
- Model a small, high-signal operation catalog for Google SERP use cases, likely:
  - `search`
  - `images`
  - `news`
  - `videos`
  - `shopping`
  - `maps`
- Represent all operations through the single `serper.request` tool with an `operation` enum and request `payload`.
- Keep path handling minimal if the Serper surface is endpoint-per-mode rather than resource-id based.

## Assumptions
- A conservative endpoint-per-mode Serper provider is acceptable per clarification.
- Serper auth is API-key based and stable for the public search API.
- The package namespace should be `serper` and the tool key should be `serper.request`.

## Acceptance Criteria
- [ ] `from harnessiq.providers.serper import SerperClient, SerperCredentials` works.
- [ ] `from harnessiq.tools.serper import create_serper_tools` works.
- [ ] `SERPER_REQUEST` is defined and exported from `harnessiq.shared.tools`.
- [ ] `serper.request` is listed by `ToolsetRegistry().list()`.
- [ ] Serper credentials reject blank API keys.
- [ ] The request-preparation layer validates required payloads and rejects unsupported operations.
- [ ] `create_serper_tools(...)` returns a registerable `RegisteredTool` tuple.
- [ ] `tests/test_serper_provider.py` passes.

## Verification Steps
1. `python -m pytest tests/test_serper_provider.py -v`
2. `python -m pytest tests/test_toolset_registry.py -v`
3. `python -c "from harnessiq.toolset import list_tools; print([e.key for e in list_tools() if e.family == 'serper'])"`
4. `python -c "from harnessiq.providers.serper import SerperCredentials; print(SerperCredentials(api_key='test').as_redacted_dict())"`

## Dependencies
None.

## Drift Guard
Do not overclaim Serper coverage. Keep the implementation limited to clearly supportable public search modes and the standard provider-backed MCP-style tool surface. Do not add scraping, crawling, or undocumented convenience behaviors.
