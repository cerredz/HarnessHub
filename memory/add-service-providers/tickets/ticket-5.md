# Ticket 5: Outreach Provider

## Title
Add `harnessiq/providers/outreach/` with core API operation catalog, OAuth client, and credential model

## Intent
Outreach (outreach.io) is an enterprise sales engagement platform with a JSON:API-compliant REST API. Its resource model is extensive (50+ types in the schema); this ticket covers the primary sales workflow resources: Prospects, Accounts, Sequences, Sequence States, Opportunities, Tasks, Calls, Mailboxes, Templates, Users, and Webhooks. Outreach uses OAuth 2.0 Bearer tokens — the credential model accepts a pre-obtained access token, leaving the OAuth exchange to the caller. The provider implements the standard operation-catalog pattern with JSON:API-aware URL building.

## Scope
**Creates:**
- `harnessiq/providers/outreach/__init__.py`
- `harnessiq/providers/outreach/api.py`
- `harnessiq/providers/outreach/client.py`
- `harnessiq/providers/outreach/operations.py`
- `tests/test_outreach_provider.py`

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/outreach/__init__.py` | Create: curated exports |
| `harnessiq/providers/outreach/api.py` | Create: DEFAULT_BASE_URL, build_headers(), URL builders |
| `harnessiq/providers/outreach/client.py` | Create: OutreachCredentials, OutreachClient |
| `harnessiq/providers/outreach/operations.py` | Create: operation catalog for core resources, tool definition, factory |
| `tests/test_outreach_provider.py` | Create: unit tests |

## Approach

**Authentication:** OAuth 2.0 Bearer token. Header: `Authorization: Bearer <access_token>`. The credential model holds a pre-obtained token; OAuth exchange is outside this provider's scope.

**Base URL:** `https://api.outreach.io/api/v2`

**OutreachCredentials (frozen dataclass):**
```
access_token: str
base_url: str = DEFAULT_BASE_URL
timeout_seconds: float = 60.0
```
`__post_init__`: validate non-blank. `as_redacted_dict()` masks the token.

**JSON:API conventions:** Outreach follows JSON:API 1.0. Request bodies are wrapped: `{"data": {"type": "<resource>", "attributes": {...}}}`. Response bodies have `{"data": {...}, "meta": {...}}`. The operation catalog passes payloads through as-is (the caller constructs the `data` wrapper), or `prepare_request()` can optionally wrap a plain attributes dict. The chosen approach: pass-through (caller sends the full JSON:API envelope) to avoid hiding the protocol.

**URL patterns:**
- Collection: `/api/v2/{resources}` (plural lowercase)
- Item: `/api/v2/{resources}/{id}`
- Relationships: `/api/v2/{resources}/{id}/relationships/{rel}` (not in scope for this ticket)

**Operation catalog** — core resources:

| Resource | Operations |
|---|---|
| Prospects | list (GET, supports filter/sort/page), get (GET /{id}), create (POST), update (PATCH /{id}), delete (DELETE /{id}) |
| Accounts | list, get, create, update, delete |
| Sequences | list, get, create, update, delete |
| Sequence States | list, get, create (enroll prospect), update, delete (unenroll) |
| Sequence Steps | list, get, create, update, delete |
| Opportunities | list, get, create, update, delete |
| Tasks | list, get, create, update, delete |
| Calls | list, get, create, update |
| Mailboxes | list, get |
| Templates | list, get, create, update, delete |
| Users | list, get |
| Webhooks | list, get, create, update, delete |

Query parameter support: `filter[{attr}]`, `sort`, `page[size]`, `page[number]`, `include` — all passed through via `query` param in the operation call. No special encoding needed beyond standard URL encoding (handled by `join_url`).

**Tool definition:** `OUTREACH_REQUEST` key. MCP-style with `operation` enum, `path_params`, `query`, `payload`.

## Assumptions
- Ticket 1 is merged.
- The caller is responsible for obtaining and refreshing the OAuth access token. `OutreachCredentials` stores the current token only.
- JSON:API envelope wrapping is the caller's responsibility. The client passes `payload` as the request body verbatim.
- Rate limit (10,000 req/hour) is enforced server-side; no client-side rate limiting.
- The `include` query parameter for related resources is supported as a plain query parameter, not special-cased.

## Acceptance Criteria
- [ ] `from harnessiq.providers.outreach import OutreachCredentials, OutreachClient, create_outreach_tools` works
- [ ] `OutreachCredentials(access_token="")` raises `ValueError`
- [ ] `build_headers(token)` returns `{"Authorization": "Bearer <token>"}`
- [ ] `build_outreach_operation_catalog()` covers all 12 resource groups (60 operations minimum)
- [ ] `prepare_request("list_prospects", query={"filter[name]": "Smith"})` builds correct URL with query string
- [ ] `prepare_request("update_prospect", path_params={"id": "123"}, payload={...})` builds PATCH URL
- [ ] `create_outreach_tools(credentials=...)` returns registerable tuple
- [ ] All new and existing tests pass

## Verification Steps
1. `python -m pytest tests/test_outreach_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -m py_compile harnessiq/providers/outreach/*.py`
4. `python -c "from harnessiq.providers.outreach import OutreachCredentials; print(OutreachCredentials(access_token='tok').as_redacted_dict())"`

## Dependencies
- Ticket 1

## Drift Guard
This ticket covers only the 12 core resource groups listed above. It must not implement OAuth token exchange, webhook signature verification, bulk API endpoints, custom object management, or streaming. No changes to existing files outside the `outreach/` subfolder and its test file.
