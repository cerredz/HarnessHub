# Ticket 1: Add Attio Provider and Tool Registration

## Title
Add the Attio provider family and register its tooling surface

## Issue URL
https://github.com/cerredz/HarnessHub/issues/171

## Intent
Attio is a heavyweight CRM in the user-supplied GTM stack and exposes a documented public REST API. This ticket adds a first-class `attio` provider family plus a single MCP-style `attio.request` tool so agents can interact with Attio through the established provider-backed tooling layer instead of ad hoc HTTP calls.

## Scope
In scope:
- Add `harnessiq/providers/attio/` with credentials/auth helpers, client, operation catalog, and exports.
- Add `harnessiq/tools/attio/` with the MCP-style tool definition/factory.
- Register `attio.request` in the shared tool constants and toolset catalog.
- Add provider-level tests and any minimal package/export wiring required.

Out of scope:
- Attio-specific agents or CLI commands.
- Full coverage of every Attio endpoint if the public API surface is much larger than a reasonable first provider cut.
- Any undocumented or private Attio endpoints.

## Relevant Files
- `harnessiq/providers/attio/__init__.py`: create curated Attio exports.
- `harnessiq/providers/attio/api.py`: create base URL and auth/header helpers.
- `harnessiq/providers/attio/client.py`: create `AttioCredentials` and `AttioClient`.
- `harnessiq/providers/attio/operations.py`: create Attio operation catalog and request preparation helpers.
- `harnessiq/tools/attio/__init__.py`: create Attio tool exports.
- `harnessiq/tools/attio/operations.py`: create `attio.request` tool definition/factory.
- `harnessiq/shared/tools.py`: add `ATTIO_REQUEST` constant/export.
- `harnessiq/toolset/catalog.py`: register the Attio provider family in metadata and factory dispatch.
- `tests/test_attio_provider.py`: create unit coverage.

## Approach
Use the existing provider pattern seen in `instantly`, `exa`, and `lemlist`:

- Define a frozen credentials dataclass with API key, base URL, timeout, masking, and redacted serialization helpers.
- Implement Attio auth with a bearer token header against the documented public REST API.
- Model Attio as a single request tool keyed `attio.request`.
- Start with a conservative but useful public operation set focused on documented CRM record/object access, such as:
  - list objects
  - list attributes for an object
  - list records
  - get record
  - create record
  - update record
  - delete record
- Use declarative operation metadata with path params, query, and payload validation.
- Register the family through `shared/tools.py` and `toolset/catalog.py` so `ToolsetRegistry` can resolve it.

This follows the repo convention of reaching third-party platforms only through provider-backed tools.

## Assumptions
- Attio bearer-token authentication is stable for the relevant public endpoints.
- A conservative object/record-centric operation set is sufficient for initial provider registration.
- The package namespace should be `attio` and the tool key should be `attio.request`.

## Acceptance Criteria
- [ ] `from harnessiq.providers.attio import AttioClient, AttioCredentials` works.
- [ ] `from harnessiq.tools.attio import create_attio_tools` works.
- [ ] `ATTIO_REQUEST` is defined and exported from `harnessiq.shared.tools`.
- [ ] `attio.request` is listed by `ToolsetRegistry().list()`.
- [ ] Attio credentials reject blank API keys.
- [ ] The request-preparation layer validates required path parameters and payload requirements.
- [ ] `create_attio_tools(...)` returns a registerable `RegisteredTool` tuple.
- [ ] `tests/test_attio_provider.py` passes.

## Verification Steps
1. `python -m pytest tests/test_attio_provider.py -v`
2. `python -m pytest tests/test_toolset_registry.py -v`
3. `python -c "from harnessiq.toolset import list_tools; print([e.key for e in list_tools() if e.family == 'attio'])"`
4. `python -c "from harnessiq.providers.attio import AttioCredentials; print(AttioCredentials(api_key='test').as_redacted_dict())"`

## Dependencies
None.

## Drift Guard
Do not add Attio-specific business logic outside the provider/tool layer. Do not guess undocumented endpoints or mutate existing agent behavior. Keep the initial Attio surface conservative and directly grounded in the documented public REST API.
