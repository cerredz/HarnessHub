# Ticket 5 — Lusha Provider + Tool + Registration

## Title
Add Lusha provider and tool to harnessiq

## Intent
Lusha is a B2B contact and company intelligence platform with person/company enrichment, prospecting search, AI-powered lookalikes, signals (job changes, hiring surges), and webhook subscriptions. This ticket adds the complete provider and tool layer.

## Scope
**In scope:**
- `harnessiq/providers/lusha/` — api.py, client.py, operations.py, __init__.py
- `harnessiq/tools/lusha/` — operations.py, __init__.py
- `harnessiq/shared/tools.py` — add `LUSHA_REQUEST` constant
- `harnessiq/toolset/catalog.py` — add ToolEntry + factory map entry
- `tests/test_lusha_provider.py`

**Out of scope:** Lusha Chrome Extension API, deprecated v1 bulk person endpoint, DNC-specific plan-locked features.

## Relevant Files
- `harnessiq/providers/lusha/__init__.py` — CREATE
- `harnessiq/providers/lusha/api.py` — CREATE: DEFAULT_BASE_URL, build_headers(), url()
- `harnessiq/providers/lusha/client.py` — CREATE: LushaCredentials, LushaClient
- `harnessiq/providers/lusha/operations.py` — CREATE: catalog + tool factory
- `harnessiq/tools/lusha/__init__.py` — CREATE
- `harnessiq/tools/lusha/operations.py` — CREATE: tool factory with rich descriptions
- `harnessiq/shared/tools.py` — MODIFY
- `harnessiq/toolset/catalog.py` — MODIFY
- `tests/test_lusha_provider.py` — CREATE

## Approach
Lusha uses `api_key` as a **request header** (not query param). Base URL: `https://api.lusha.com`.

**Credential design:**
```python
@dataclass(frozen=True, slots=True)
class LushaCredentials:
    api_key: str
    base_url: str = "https://api.lusha.com"
    timeout_seconds: float = 60.0
```

**Auth pattern:** `build_headers()` returns `{"api_key": api_key, "Content-Type": "application/json"}`.

**Operation catalog:**

*Person Enrichment:*
- `enrich_person` — GET `/v2/person` (query: firstName, lastName, companyName/companyDomain, or email or linkedinUrl)
- `bulk_enrich_persons` — POST `/v2/person` (payload: array of up to 100 person objects)

*Company Enrichment:*
- `enrich_company` — GET `/v2/company` (query: domain or company name)
- `bulk_enrich_companies` — POST `/bulk/company/v2` (payload: array of up to 100 company objects)

*Prospecting — Contact Search & Enrich:*
- `search_contacts` — POST `/prospecting/contact/search` (payload: include/exclude filters, excludeDnc)
- `enrich_contacts` — POST `/prospecting/contact/enrich` (payload: array of contact IDs, up to 100)

*Prospecting — Company Search & Enrich:*
- `search_companies` — POST `/prospecting/company/search` (payload: include/exclude filters)
- `enrich_companies` — POST `/prospecting/company/enrich` (payload: array of company IDs, up to 100)

*Contact Filters (lookup values):*
- `get_contact_departments` — GET `/prospecting/filters/contacts/departments`
- `get_contact_seniority_levels` — GET `/prospecting/filters/contacts/seniority`
- `get_contact_data_points` — GET `/prospecting/filters/contacts/existing_data_points`
- `get_all_countries` — GET `/prospecting/filters/contacts/all_countries`
- `search_contact_locations` — POST `/prospecting/filters/contacts/locations`

*Company Filters (lookup values):*
- `search_company_names` — POST `/prospecting/filters/companies/names`
- `get_industry_labels` — GET `/prospecting/filters/companies/industries_labels`
- `get_company_sizes` — GET `/prospecting/filters/companies/sizes`
- `get_company_revenues` — GET `/prospecting/filters/companies/revenues`
- `search_company_locations` — POST `/prospecting/filters/companies/locations`
- `get_sic_codes` — GET `/prospecting/filters/companies/sics`
- `get_naics_codes` — GET `/prospecting/filters/companies/naics`
- `get_intent_topics` — GET `/prospecting/filters/companies/intent_topics`
- `search_technologies` — POST `/prospecting/filters/companies/technologies`

*Signals:*
- `get_signal_filters` — GET `/api/signals/filters/{object_type}` (path param: object_type = "contact" or "company")
- `get_contact_signals` — POST `/api/signals/contacts` (payload: contact IDs)
- `search_contact_signals` — POST `/api/signals/contacts/search`
- `get_company_signals` — POST `/api/signals/companies` (payload: company IDs)
- `search_company_signals` — POST `/api/signals/companies/search`

*Lookalikes:*
- `find_similar_contacts` — POST `/v3/lookalike/contacts`
- `find_similar_companies` — POST `/v3/lookalike/companies`

*Webhooks / Subscriptions:*
- `create_subscriptions` — POST `/api/subscriptions`
- `list_subscriptions` — GET `/api/subscriptions`
- `get_subscription` — GET `/api/subscriptions/{subscription_id}`
- `update_subscription` — PATCH `/api/subscriptions/{subscription_id}`
- `delete_subscriptions` — POST `/api/subscriptions/delete`
- `test_subscription` — POST `/api/subscriptions/{subscription_id}/test`
- `get_webhook_audit_logs` — GET `/api/audit-logs`
- `get_webhook_audit_stats` — GET `/api/audit-logs/stats`
- `get_webhook_secret` — GET `/api/account/secret`
- `regenerate_webhook_secret` — POST `/api/account/secret/regenerate`

*Account:*
- `get_account_usage` — GET `/account/usage`

Tool key: `lusha.request`. Tool name: `lusha_request`.

## Assumptions
- Header name is lowercase `api_key` (case-sensitive per Lusha docs)
- `bulk_enrich_companies` path is `/bulk/company/v2` (not `/v2/bulk/company`) — confirmed from docs
- Signals API path prefix is `/api/signals/` (not `/v2/signals/`)
- Webhooks/Subscriptions path prefix is `/api/subscriptions/` (not `/v2/subscriptions/`)

## Acceptance Criteria
- [ ] `LushaCredentials(api_key)` validates blank key
- [ ] `build_headers()` returns `{"api_key": <key>, "Content-Type": "application/json"}`
- [ ] All 39 operations present in catalog
- [ ] Operations with path params (`object_type`, `subscription_id`) validate correctly
- [ ] `create_lusha_tools(credentials=creds)` returns 1 RegisteredTool keyed `lusha.request`
- [ ] `LUSHA_REQUEST` exported from `shared/tools.py`
- [ ] ToolEntry and factory map entry present in catalog
- [ ] All tests pass

## Verification Steps
1. `python -m pytest tests/test_lusha_provider.py -v`
2. `python -c "from harnessiq.providers.lusha import LushaCredentials; c = LushaCredentials('key'); print(c.masked_api_key())"`
3. `python -c "from harnessiq.toolset import list_tools; print([e for e in list_tools() if e.family == 'lusha'])"`

## Dependencies
None.

## Drift Guard
Must not touch existing providers. The header-based `api_key` pattern is new (existing providers use `x-api-key` or `X-Api-Key` with different cases). Lusha uses the lowercase `api_key` header — this is not a mistake and must not be normalized.
