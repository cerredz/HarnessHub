# Ticket 6: Lemlist Provider

## Title
Add `harnessiq/providers/lemlist/` with full API operation catalog, client, and credential model

## Intent
Lemlist (lemlist.com) is a cold email and multi-channel outreach automation platform. Its API covers the full outreach lifecycle: campaigns, sequences, leads, companies, contacts, inbox messages, enrichment, scheduling, and team management. Authentication uses HTTP Basic Auth with an empty username and the API key as the password — a pattern distinct from other providers in this SDK. This ticket adds the Lemlist provider with the complete documented operation catalog and MCP-style tool factory.

## Scope
**Creates:**
- `harnessiq/providers/lemlist/__init__.py`
- `harnessiq/providers/lemlist/api.py`
- `harnessiq/providers/lemlist/client.py`
- `harnessiq/providers/lemlist/operations.py`
- `tests/test_lemlist_provider.py`

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/lemlist/__init__.py` | Create: curated exports |
| `harnessiq/providers/lemlist/api.py` | Create: DEFAULT_BASE_URL, build_headers(), URL builders |
| `harnessiq/providers/lemlist/client.py` | Create: LemlistCredentials, LemlistClient |
| `harnessiq/providers/lemlist/operations.py` | Create: operation catalog, tool definition, factory |
| `tests/test_lemlist_provider.py` | Create: unit tests |

## Approach

**Authentication:** HTTP Basic Auth. Username is always empty; password is the API key. Header: `Authorization: Basic <base64(:api_key)>`. Encoding: `base64.b64encode(f":{api_key}".encode()).decode()`.

**Base URL:** `https://api.lemlist.com/api`

**LemlistCredentials (frozen dataclass):**
```
api_key: str
base_url: str = DEFAULT_BASE_URL
timeout_seconds: float = 60.0
```
`__post_init__`: validate non-blank. `masked_api_key()` + `as_redacted_dict()`.

**Operation catalog** — all 19 documented resource categories:

| Category | Operations |
|---|---|
| Activities | list-by-campaign (GET /activities?campaignId=...), list-by-lead (GET /activities?leadId=...) |
| Campaigns | list (GET /campaigns), get (GET /campaigns/{campaignId}), create (POST /campaigns), update (PATCH /campaigns/{campaignId}), delete (DELETE /campaigns/{campaignId}), get-settings (GET /campaigns/{campaignId}/settings), update-settings (PATCH /campaigns/{campaignId}/settings), list-reports (GET /campaigns/{campaignId}/reports) |
| Companies | list (GET /companies), get (GET /companies/{companyId}), create (POST /companies), update (PATCH /companies/{companyId}), delete (DELETE /companies/{companyId}), add-note (POST /companies/{companyId}/notes) |
| Contacts | list (GET /contacts), get (GET /contacts/{contactId}) |
| CRM | get-filters (GET /crm/filters), list-users (GET /crm/users) |
| Email Accounts | list (GET /emailAccounts), get (GET /emailAccounts/{accountId}), update (PATCH /emailAccounts/{accountId}) |
| Enrichment | enrich-email (POST /enrichment/email), enrich-contact (POST /enrichment/contact) |
| Inbox | list-messages (GET /inbox), get-message (GET /inbox/{messageId}), send-reply (POST /inbox/{messageId}/reply), create-draft (POST /inbox/{messageId}/draft), mark-as-done (PUT /inbox/{messageId}/done) |
| Leads | list-by-campaign (GET /campaigns/{campaignId}/leads), get (GET /leads/{leadId}), add-to-campaign (POST /campaigns/{campaignId}/leads/{leadId}), remove-from-campaign (DELETE /campaigns/{campaignId}/leads/{leadId}), update-variable (PATCH /leads/{leadId}), delete (DELETE /leads/{leadId}), unsubscribe (POST /leads/{leadId}/unsubscribe), mark-as-interested (PUT /leads/{leadId}/interested) |
| Lemwarm | get-settings (GET /lemwarm/settings), update-settings (PATCH /lemwarm/settings) |
| People Database | search-people (GET /people-database/search), search-companies (GET /people-database/companies/search) |
| Schedules | list (GET /schedules), get (GET /schedules/{scheduleId}), create (POST /schedules), update (PATCH /schedules/{scheduleId}), delete (DELETE /schedules/{scheduleId}) |
| Sequences | list-steps (GET /campaigns/{campaignId}/sequences), add-step (POST /campaigns/{campaignId}/sequences), update-step (PATCH /campaigns/{campaignId}/sequences/{stepId}), delete-step (DELETE /campaigns/{campaignId}/sequences/{stepId}) |
| Tasks | list (GET /tasks), create (POST /tasks), complete (PUT /tasks/{taskId}/complete), delete (DELETE /tasks/{taskId}) |
| Team | get-info (GET /team), get-credits (GET /team/credits) |
| Unsubscribes | list (GET /unsubscribes), add (POST /unsubscribes), delete (DELETE /unsubscribes/{email}) |
| Users | get-me (GET /users/me), get-channel-status (GET /users/me/channels) |
| Watchlist | list (GET /watchlist), add (POST /watchlist), remove (DELETE /watchlist/{watchlistId}) |
| Webhooks | list (GET /webhooks), get (GET /webhooks/{hookId}), create (POST /webhooks), update (PATCH /webhooks/{hookId}), delete (DELETE /webhooks/{hookId}) |

**Tool definition:** `LEMLIST_REQUEST` key. MCP-style with `operation` enum, `path_params`, `query`, `payload`.

**Rate limiting note:** Lemlist enforces 20 requests per 2 seconds. This is documented in `as_redacted_dict()` as a note; no client-side throttling is implemented.

## Assumptions
- Ticket 1 is merged.
- Basic Auth with empty username is a stable lemlist API contract as documented.
- Path structures follow `developer.lemlist.com` documentation conventions.
- The People Database endpoints accept query parameters for filtering rather than a POST body.

## Acceptance Criteria
- [ ] `from harnessiq.providers.lemlist import LemlistCredentials, LemlistClient, create_lemlist_tools` works
- [ ] `LemlistCredentials(api_key="")` raises `ValueError`
- [ ] `build_headers(api_key)` produces `Authorization: Basic <base64(:api_key)>`
- [ ] `build_lemlist_operation_catalog()` covers all 19 resource categories
- [ ] `prepare_request("list_campaigns")` builds `GET https://api.lemlist.com/api/campaigns`
- [ ] `prepare_request("add_lead_to_campaign", path_params={"campaignId": "c1", "leadId": "l1"})` builds correct POST URL
- [ ] `create_lemlist_tools(credentials=...)` returns registerable tuple
- [ ] All new and existing tests pass

## Verification Steps
1. `python -m pytest tests/test_lemlist_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -m py_compile harnessiq/providers/lemlist/*.py`
4. `python -c "from harnessiq.providers.lemlist import LemlistCredentials; print(LemlistCredentials(api_key='k').as_redacted_dict())"`

## Dependencies
- Ticket 1

## Drift Guard
This ticket must not touch any existing provider or agent. No client-side rate-limit throttling. No webhook signature verification. No external libraries for Base64 encoding — use stdlib `base64`.
