# Ticket 4: Instantly Provider

## Title
Add `harnessiq/providers/instantly/` with full API v2 operation catalog, client, and credential model

## Intent
Instantly (instantly.ai) is a cold email outreach and sales automation platform with a comprehensive V2 REST API. Its 29 resource categories cover the full lifecycle of outbound campaigns: account setup, lead management, campaign execution, analytics, inbox placement testing, and workspace administration. This ticket adds the Instantly provider with Bearer-token authentication, an operation catalog spanning all documented V2 resources, and an MCP-style tool factory.

## Scope
**Creates:**
- `harnessiq/providers/instantly/__init__.py`
- `harnessiq/providers/instantly/api.py`
- `harnessiq/providers/instantly/client.py`
- `harnessiq/providers/instantly/operations.py`
- `tests/test_instantly_provider.py`

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/instantly/__init__.py` | Create: curated exports |
| `harnessiq/providers/instantly/api.py` | Create: DEFAULT_BASE_URL, build_headers(), URL builders |
| `harnessiq/providers/instantly/client.py` | Create: InstantlyCredentials, InstantlyClient |
| `harnessiq/providers/instantly/operations.py` | Create: full V2 operation catalog, tool definition, factory |
| `tests/test_instantly_provider.py` | Create: unit tests |

## Approach

**Authentication:** Bearer token. Header: `Authorization: Bearer <api_key>`.

**Base URL:** `https://api.instantly.ai/api/v2`

**InstantlyCredentials (frozen dataclass):**
```
api_key: str
base_url: str = DEFAULT_BASE_URL
timeout_seconds: float = 60.0
```
`__post_init__`: validate non-blank. `masked_api_key()` + `as_redacted_dict()`.

**Operation catalog** — all 29 V2 resource categories:

| Category | Operations |
|---|---|
| Account | list, get, create, update, delete, test-vitals, warmup-analytics |
| Account Campaign Mapping | list, create, delete |
| Analytics | get-campaign-summary, get-campaign-step-summary, get-account-summary |
| API Key | list, create, update, delete |
| Audit Log | list |
| Background Job | get |
| Block List Entry | list, create, delete |
| Campaign | list, get, create, update, delete, launch, pause, activate-lead-subscriptions |
| Campaign Subsequence | list, get, create, update, delete |
| CRM Actions | list, create |
| Custom Tag | list, create, update, delete |
| Custom Tag Mapping | list, create, delete |
| DFY Email Account Order | get, create |
| Email | list, get, list-replies, mark-as-read, reply |
| Email Verification | verify |
| Inbox Placement Analytics | get |
| Inbox Placement Reports | get-blacklist, get-spam-filters |
| Inbox Placement Test | list, get, create |
| Lead | list, get, create, update, delete, move, set-interest, get-emails, verify-email |
| Lead Label | list, create, update, delete |
| Lead List | list, get, create, update, delete |
| OAuth | connect-google, connect-microsoft |
| SuperSearch Enrichment | enrich |
| Webhook | list, get, create, update, delete |
| Webhook Event | list, get |
| Workspace | get, update |
| Workspace Billing | get-plan, get-usage, get-add-ons |
| Workspace Group Member | list, add, remove |
| Workspace Member | list, invite, update, remove |

URL patterns follow `/api/v2/{resource}` and `/api/v2/{resource}/{id}` with standard REST conventions. Plural resource names in paths (e.g., `/api/v2/accounts`, `/api/v2/campaigns/{id}`).

**Tool definition:** `INSTANTLY_REQUEST` key. MCP-style with `operation` enum, `path_params`, `query`, `payload`.

## Assumptions
- Ticket 1 is merged.
- API V2 endpoints follow the resource names documented at `developer.instantly.ai`. Path structure inferred from standard REST conventions where not explicitly documented.
- OAuth operations (`connect-google`, `connect-microsoft`) accept a pre-obtained access token in the payload; the OAuth flow itself is handled by the caller.
- Rate limits are handled by the caller; the client does not implement automatic retry.

## Acceptance Criteria
- [ ] `from harnessiq.providers.instantly import InstantlyCredentials, InstantlyClient, create_instantly_tools` works
- [ ] `InstantlyCredentials(api_key="").` raises `ValueError`
- [ ] `build_headers(api_key)` returns `{"Authorization": "Bearer <key>"}`
- [ ] `build_instantly_operation_catalog()` returns operations for all 29 resource categories
- [ ] `prepare_request("list_campaigns")` builds `GET https://api.instantly.ai/api/v2/campaigns`
- [ ] `prepare_request("get_lead", path_params={"lead_id": "x"})` builds correct URL
- [ ] `create_instantly_tools(credentials=...)` returns registerable tuple
- [ ] All new and existing tests pass

## Verification Steps
1. `python -m pytest tests/test_instantly_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -m py_compile harnessiq/providers/instantly/*.py`
4. `python -c "from harnessiq.providers.instantly import InstantlyCredentials; print(InstantlyCredentials(api_key='k').as_redacted_dict())"`

## Dependencies
- Ticket 1

## Drift Guard
This ticket must not implement OAuth token exchange or email sending outside the operation catalog pattern. No special-casing of async background jobs — callers poll the `get_background_job` operation. No changes to any existing file outside the `instantly/` subfolder and its test file.
