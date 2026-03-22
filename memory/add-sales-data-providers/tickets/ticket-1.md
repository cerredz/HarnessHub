# Ticket 1 — Apollo.io Provider + Tool + Registration

## Title
Add Apollo.io provider and tool to harnessiq

## Intent
Apollo.io is a full-stack B2B sales intelligence and engagement platform. This ticket adds the complete provider and tool layer for Apollo.io, enabling agents to search and enrich contacts and companies, manage CRM records, work with sequences, deals, and tasks.

## Scope
**In scope:**
- `harnessiq/providers/apollo/` — api.py, client.py, operations.py, __init__.py
- `harnessiq/tools/apollo/` — operations.py, __init__.py
- `harnessiq/shared/tools.py` — add `APOLLO_REQUEST` constant
- `harnessiq/toolset/catalog.py` — add ToolEntry + factory map entry
- `tests/test_apollo_provider.py`

**Out of scope:** OAuth 2.0 partner flow, webhook registration, user management beyond listing.

## Relevant Files
- `harnessiq/providers/apollo/__init__.py` — CREATE: exports credentials, client, key types
- `harnessiq/providers/apollo/api.py` — CREATE: DEFAULT_BASE_URL, build_headers(), url()
- `harnessiq/providers/apollo/client.py` — CREATE: ApolloCredentials, ApolloClient
- `harnessiq/providers/apollo/operations.py` — CREATE: full operation catalog + tool factory
- `harnessiq/tools/apollo/__init__.py` — CREATE: re-exports
- `harnessiq/tools/apollo/operations.py` — CREATE: tool factory with rich descriptions
- `harnessiq/shared/tools.py` — MODIFY: add APOLLO_REQUEST constant + __all__ entry
- `harnessiq/toolset/catalog.py` — MODIFY: add ToolEntry + PROVIDER_FACTORY_MAP entry
- `tests/test_apollo_provider.py` — CREATE: unit tests

## Approach
Follow the exa provider pattern exactly. Apollo.io uses `X-Api-Key: <key>` header auth. Base URL is `https://api.apollo.io/api/v1`. Operations modeled as `ApolloOperation` dataclass with `name`, `category`, `method`, `path_hint`, `required_path_params`, `payload_kind`, `payload_required`, `allow_query`.

**Operation catalog (grouped by category):**

*People (contacts in Apollo DB):*
- `search_people` — POST `/mixed_people/api_search`
- `enrich_person` — POST `/people/match`
- `bulk_enrich_people` — POST `/people/bulk_match`

*Contacts (CRM records):*
- `search_contacts` — POST `/contacts/search`
- `create_contact` — POST `/contacts`
- `update_contact` — PATCH `/contacts/{contact_id}`

*Organizations (Apollo DB):*
- `search_organizations` — POST `/mixed_companies/search`
- `enrich_organization` — GET `/organizations/enrich`

*Accounts (CRM records):*
- `search_accounts` — POST `/accounts/search`
- `bulk_create_accounts` — POST `/accounts/bulk_create`
- `update_account` — PATCH `/accounts/{account_id}`

*Sequences:*
- `search_sequences` — POST `/emailer_campaigns/search`
- `add_contacts_to_sequence` — POST `/emailer_campaigns/{sequence_id}/add_contact_ids`
- `remove_contacts_from_sequence` — POST `/emailer_campaigns/remove_or_stop_contact_ids`

*Email Accounts:*
- `list_email_accounts` — GET `/email_accounts`

*Deals / Opportunities:*
- `search_deals` — GET `/opportunities/search`
- `create_deal` — POST `/opportunities`
- `update_deal` — PATCH `/opportunities/{opportunity_id}`

*Tasks:*
- `search_tasks` — POST `/tasks/search`
- `bulk_create_tasks` — POST `/tasks/bulk_create`

*Calls:*
- `search_calls` — POST `/phone_calls/search`
- `create_call` — POST `/phone_calls`
- `update_call` — PUT `/phone_calls/{call_id}`

*Admin:*
- `list_users` — GET `/users/search`
- `get_api_usage` — POST `/usage_stats/api_usage_stats`

Tool key: `apollo.request`. Tool name: `apollo_request`.

## Assumptions
- Apollo.io API key is a static string (not OAuth tokens)
- `X-Api-Key` header name confirmed from Apollo docs
- Content-Type is always `application/json`
- `enrich_organization` uses GET with query params (not JSON body)
- `search_deals` uses GET with query params

## Acceptance Criteria
- [ ] `ApolloCredentials(api_key)` validates blank key raises ValueError
- [ ] `ApolloCredentials.masked_api_key()` redacts correctly
- [ ] `ApolloCredentials.as_redacted_dict()` contains no raw API key
- [ ] `build_headers()` returns `{"X-Api-Key": api_key, "Content-Type": "application/json"}`
- [ ] All 26 operations present in `build_apollo_operation_catalog()`
- [ ] `get_apollo_operation("invalid")` raises ValueError with available list
- [ ] `_build_prepared_request` raises ValueError for missing required path params
- [ ] `_build_prepared_request` raises ValueError when payload given to non-payload operation
- [ ] `_build_prepared_request` raises ValueError when payload missing from required-payload operation
- [ ] `create_apollo_tools(credentials=creds)` returns tuple of 1 RegisteredTool with key `apollo.request`
- [ ] Handler executes and returns `{operation, method, path, response}` dict
- [ ] `APOLLO_REQUEST` constant exported from `shared/tools.py`
- [ ] `ToolEntry(key="apollo.request", family="apollo")` present in `PROVIDER_ENTRIES`
- [ ] `"apollo"` entry present in `PROVIDER_FACTORY_MAP`
- [ ] All tests pass

## Verification Steps
1. `python -m pytest tests/test_apollo_provider.py -v`
2. `python -c "from harnessiq.providers.apollo import ApolloCredentials, ApolloClient; print('OK')"`
3. `python -c "from harnessiq.tools.apollo import create_apollo_tools; print('OK')"`
4. `python -c "from harnessiq.toolset import list_tools; entries = [e for e in list_tools() if e.family == 'apollo']; print(entries)"`
5. `python -c "from harnessiq.shared.tools import APOLLO_REQUEST; print(APOLLO_REQUEST)"`

## Dependencies
None.

## Drift Guard
This ticket must not touch any existing provider, any LLM provider, the agent runtime, or the CLI. It adds one new provider and registers it. Nothing else changes.
