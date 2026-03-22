# Ticket 4 — Smartlead Provider + Tool + Registration

## Title
Add Smartlead provider and tool to harnessiq

## Intent
Smartlead is a cold email outreach platform with email warm-up, campaign sequencing, and multi-inbox management. This ticket adds the complete provider and tool layer, enabling agents to manage campaigns, email accounts, leads, analytics, webhooks, and client accounts.

## Scope
**In scope:**
- `harnessiq/providers/smartlead/` — api.py, client.py, operations.py, __init__.py
- `harnessiq/tools/smartlead/` — operations.py, __init__.py
- `harnessiq/shared/tools.py` — add `SMARTLEAD_REQUEST` constant
- `harnessiq/toolset/catalog.py` — add ToolEntry + factory map entry
- `tests/test_smartlead_provider.py`

**Out of scope:** Smartlead partner/reseller admin endpoints, internal diagnostic endpoints.

## Relevant Files
- `harnessiq/providers/smartlead/__init__.py` — CREATE
- `harnessiq/providers/smartlead/api.py` — CREATE: DEFAULT_BASE_URL, build_headers(), url()
- `harnessiq/providers/smartlead/client.py` — CREATE: SmartleadCredentials, SmartleadClient
- `harnessiq/providers/smartlead/operations.py` — CREATE: catalog + tool factory
- `harnessiq/tools/smartlead/__init__.py` — CREATE
- `harnessiq/tools/smartlead/operations.py` — CREATE: tool factory with rich descriptions
- `harnessiq/shared/tools.py` — MODIFY
- `harnessiq/toolset/catalog.py` — MODIFY
- `tests/test_smartlead_provider.py` — CREATE

## Approach
Smartlead uses a single `api_key` query parameter for auth. Like Instantly and Salesforge. Base URL: `https://server.smartlead.ai/api/v1`.

**Credential design:**
```python
@dataclass(frozen=True, slots=True)
class SmartleadCredentials:
    api_key: str
    base_url: str = "https://server.smartlead.ai/api/v1"
    timeout_seconds: float = 60.0
```

**Auth pattern:** `api_key` injected into every URL as query param via `join_url(base, path, query={"api_key": key, **caller_query})`. `build_headers()` returns only `{"Content-Type": "application/json"}`.

**Operation catalog:**

*Campaigns:*
- `list_campaigns` — GET `/campaigns/`
- `get_campaign` — GET `/campaigns/{campaign_id}`
- `create_campaign` — POST `/campaigns/create`
- `update_campaign_status` — PATCH `/campaigns/{campaign_id}/status`
- `update_campaign_schedule` — POST `/campaigns/{campaign_id}/schedule`
- `update_campaign_settings` — PATCH `/campaigns/{campaign_id}/settings`
- `delete_campaign` — DELETE `/campaigns/{campaign_id}`

*Sequences:*
- `get_campaign_sequences` — GET `/campaigns/{campaign_id}/sequences`
- `create_campaign_sequences` — POST `/campaigns/{campaign_id}/sequences`

*Email Accounts:*
- `list_email_accounts` — GET `/email-accounts/`
- `get_email_account` — GET `/email-accounts/{email_account_id}/`
- `save_email_account` — POST `/email-accounts/save`
- `update_email_account` — POST `/email-accounts/{email_account_id}`
- `update_email_account_warmup` — POST `/email-accounts/{email_account_id}/warmup`
- `get_email_account_warmup_stats` — GET `/email-accounts/{email_account_id}/warmup-stats`
- `list_campaign_email_accounts` — GET `/campaigns/{campaign_id}/email-accounts`
- `add_email_account_to_campaign` — POST `/campaigns/{campaign_id}/email-accounts`
- `remove_email_account_from_campaign` — DELETE `/campaigns/{campaign_id}/email-accounts`

*Leads:*
- `list_campaign_leads` — GET `/campaigns/{campaign_id}/leads`
- `add_leads_to_campaign` — POST `/campaigns/{campaign_id}/leads`
- `fetch_lead_by_email` — GET `/leads/`
- `fetch_lead_categories` — GET `/leads/fetch-categories`
- `fetch_global_leads` — GET `/leads/global-leads`
- `get_lead_campaigns` — GET `/leads/{lead_id}/campaigns`
- `update_lead` — POST `/campaigns/{campaign_id}/leads/{lead_id}`
- `pause_lead` — POST `/campaigns/{campaign_id}/leads/{lead_id}/pause`
- `resume_lead` — POST `/campaigns/{campaign_id}/leads/{lead_id}/resume`
- `delete_lead` — DELETE `/campaigns/{campaign_id}/leads/{lead_id}`
- `unsubscribe_lead_from_campaign` — POST `/campaigns/{campaign_id}/leads/{lead_id}/unsubscribe`
- `unsubscribe_lead_globally` — POST `/leads/{lead_id}/unsubscribe`
- `add_domain_to_block_list` — POST `/leads/add-domain-block-list`

*Master Inbox:*
- `get_message_history` — GET `/campaigns/{campaign_id}/leads/{lead_id}/message-history`
- `reply_to_lead` — POST `/email-campaigns/send-email-thread`
- `forward_reply` — POST `/email-campaigns/forward-reply-email`

*Analytics:*
- `get_campaign_analytics` — GET `/campaigns/{campaign_id}/analytics`
- `get_campaign_analytics_by_date` — GET `/campaigns/{campaign_id}/analytics-by-date`
- `get_campaign_statistics` — GET `/campaigns/{campaign_id}/statistics`
- `get_campaign_lead_stats` — GET `/campaigns/{campaign_id}/lead-stats`
- `get_account_analytics` — GET `/analytics/overview`

*Webhooks:*
- `list_campaign_webhooks` — GET `/campaigns/{campaign_id}/webhooks`
- `save_campaign_webhook` — POST `/campaigns/{campaign_id}/webhooks`
- `delete_campaign_webhook` — DELETE `/campaigns/{campaign_id}/webhooks`

*Client Management:*
- `list_clients` — GET `/client/`
- `save_client` — POST `/client/save`
- `list_client_api_keys` — GET `/client/api-key`
- `create_client_api_key` — POST `/client/api-key`
- `delete_client_api_key` — DELETE `/client/api-key/{key_id}`
- `reset_client_api_key` — PUT `/client/api-key/reset/{key_id}`

Tool key: `smartlead.request`. Tool name: `smartlead_request`.

## Assumptions
- `api_key` query param is consistent across all Smartlead endpoints
- Content-Type is always `application/json`
- Path params: `campaign_id`, `email_account_id`, `lead_id`, `key_id`

## Acceptance Criteria
- [ ] `SmartleadCredentials(api_key)` validates blank key
- [ ] `masked_api_key()` and `as_redacted_dict()` work correctly
- [ ] All 46 operations present in catalog
- [ ] `api_key` appears in request URLs as query param
- [ ] All path param groups validated (campaign_id, email_account_id, lead_id, key_id)
- [ ] `create_smartlead_tools(credentials=creds)` returns 1 RegisteredTool keyed `smartlead.request`
- [ ] `SMARTLEAD_REQUEST` exported from `shared/tools.py`
- [ ] ToolEntry and factory map entry present in catalog
- [ ] All tests pass

## Verification Steps
1. `python -m pytest tests/test_smartlead_provider.py -v`
2. `python -c "from harnessiq.providers.smartlead import SmartleadCredentials, SmartleadClient; print('OK')"`
3. `python -c "from harnessiq.toolset import list_tools; print([e for e in list_tools() if e.family == 'smartlead'])"`

## Dependencies
None.

## Drift Guard
Must not touch existing providers. The `api_key`-as-query-param pattern already exists in the codebase (instantly, salesforge) — do not refactor those; simply follow the same pattern independently.
