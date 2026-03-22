# Ticket 3 — Expandi Provider + Tool + Registration

## Title
Add Expandi provider and tool to harnessiq

## Intent
Expandi is a LinkedIn outreach automation platform. This ticket adds the complete provider and tool layer, enabling agents to manage LinkedIn campaigns, add/pause/resume prospects, send messages and connection requests, and configure webhooks.

## Scope
**In scope:**
- `harnessiq/providers/expandi/` — api.py, client.py, operations.py, __init__.py
- `harnessiq/tools/expandi/` — operations.py, __init__.py
- `harnessiq/shared/tools.py` — add `EXPANDI_REQUEST` constant
- `harnessiq/toolset/catalog.py` — add ToolEntry + factory map entry
- `tests/test_expandi_provider.py`

**Out of scope:** Auth login endpoints, CRM connector callbacks, AI content generation endpoints, Smartlead reload (internal).

## Relevant Files
- `harnessiq/providers/expandi/__init__.py` — CREATE
- `harnessiq/providers/expandi/api.py` — CREATE: DEFAULT_BASE_URL, build_headers(), url()
- `harnessiq/providers/expandi/client.py` — CREATE: ExpandiCredentials (api_key + api_secret), ExpandiClient
- `harnessiq/providers/expandi/operations.py` — CREATE: catalog + tool factory
- `harnessiq/tools/expandi/__init__.py` — CREATE
- `harnessiq/tools/expandi/operations.py` — CREATE: tool factory with rich descriptions
- `harnessiq/shared/tools.py` — MODIFY
- `harnessiq/toolset/catalog.py` — MODIFY
- `tests/test_expandi_provider.py` — CREATE

## Approach
Expandi uses a **dual-credential** pattern: `api_key` and `api_secret`, both required. Model similarly to `CreatifyCredentials(api_id, api_key)` but rename fields semantically.

**Credential design:**
```python
@dataclass(frozen=True, slots=True)
class ExpandiCredentials:
    api_key: str
    api_secret: str
    base_url: str = "https://api.liaufa.com/api/v1"
    timeout_seconds: float = 60.0
```

**Auth pattern:** Query params `?key=<api_key>&secret=<api_secret>` appended to every request URL. `build_headers()` returns only `{"Content-Type": "application/json"}`. Auth params are injected via `join_url(base, path, query={"key": creds.api_key, "secret": creds.api_secret, **caller_query})`.

**Operation catalog:**

*Campaigns:*
- `list_campaigns` — GET `/open-api/campaigns/`
- `add_prospect_to_campaign` — POST `/open-api/campaign-instance/{campaign_id}/assign/` (payload: profile_link, optional placeholders)
- `add_multiple_prospects_to_campaign` — POST `/open-api/campaign-instance/{campaign_id}/assign_multiple/` (payload: array of profile_link objects)
- `pause_campaign_contact` — GET `/open-api/campaign-contact/{contact_id}/pause/`
- `resume_campaign_contact` — GET `/open-api/campaign-contact/{contact_id}/resume/`

*v2 Campaign Contacts:*
- `create_campaign_contact_v2` — POST `/open-api/v2/li_accounts/campaign_instances/{campaign_id}/create_contact/`
- `update_campaign_contact_v2` — PATCH `/open-api/v2/li_accounts/campaign_instances/{campaign_id}/update_contact/`
- `delete_campaign_contact_v2` — DELETE `/open-api/v2/li_accounts/campaign_instances/{campaign_id}/delete_contact/`

*LinkedIn Accounts:*
- `list_linkedin_accounts` — GET `/open-api/fetch_li_accounts/`
- `list_linkedin_accounts_v2` — GET `/open-api/v2/li_accounts/`
- `send_connection_request` — POST `/open-api/v2/li_accounts/{account_id}/actions/connection_request/`
- `send_message` — POST `/open-api/v2/li_accounts/{account_id}/actions/message/`
- `send_email` — POST `/open-api/v2/li_accounts/{account_id}/actions/email/`
- `check_action_status` — POST `/open-api/v2/li_accounts/actions/{action_id}/check_action_status/`

*Messaging:*
- `fetch_messages` — GET `/open-api/fetch_messages/`
- `fetch_messages_for_contact` — GET `/open-api/fetch_messages_contact/`
- `send_message_to_contact` — POST `/open-api/send_message_to_contact`
- `reply_to_message` — POST `/open-api/reply/`

*Webhook Management:*
- `enable_messaging_webhook` — POST `/open-api/li_accounts/messaging/webhooks/enable`
- `disable_messaging_webhook` — POST `/open-api/li_accounts/messaging/webhooks/disable`

*Miscellaneous:*
- `add_to_blacklist` — POST `/open-api/blacklist/`
- `fetch_contacts` — GET `/open-api/fetch_contacts/`

Tool key: `expandi.request`. Tool name: `expandi_request`.

**masked_credentials pattern:** Since there are two secrets, `ExpandiCredentials` will expose `masked_api_key()` (masks `api_key`) and `masked_api_secret()` (masks `api_secret`). `as_redacted_dict()` returns both masked values.

## Assumptions
- Auth via query params is consistent across all endpoints (both v1 and v2)
- v2 header-based auth is documented as alternative; query param approach works for all endpoints
- The tool handles all operations through a single `expandi.request` tool, consistent with the project pattern
- `campaign_id`, `contact_id`, `account_id`, `action_id` are all path params

## Acceptance Criteria
- [ ] `ExpandiCredentials(api_key, api_secret)` validates blank key AND blank secret
- [ ] `ExpandiCredentials.masked_api_key()` and `.masked_api_secret()` both redact correctly
- [ ] `ExpandiCredentials.as_redacted_dict()` contains no raw credentials
- [ ] `build_headers()` returns only Content-Type header (no auth in headers)
- [ ] Auth params (key, secret) appear in constructed request URLs as query params
- [ ] All 22 operations present in catalog
- [ ] Path param validation works for `campaign_id`, `contact_id`, `account_id`, `action_id`
- [ ] `create_expandi_tools(credentials=creds)` returns 1 RegisteredTool keyed `expandi.request`
- [ ] `EXPANDI_REQUEST` exported from `shared/tools.py`
- [ ] ToolEntry and factory map entry present in catalog
- [ ] All tests pass

## Verification Steps
1. `python -m pytest tests/test_expandi_provider.py -v`
2. `python -c "from harnessiq.providers.expandi import ExpandiCredentials; c = ExpandiCredentials('k','s'); print(c.as_redacted_dict())"`
3. `python -c "from harnessiq.toolset import list_tools; entries = [e for e in list_tools() if e.family == 'expandi']; print(entries)"`

## Dependencies
None.

## Drift Guard
Must not touch existing providers or shared infrastructure. The dual-credential pattern (key+secret) is self-contained within the expandi module.
