# Ticket 3: LeadIQ Provider

## Title
Add `harnessiq/providers/leadiq/` — full LeadIQ API client

## Intent
Implement a complete LeadIQ provider package. LeadIQ is a lead intelligence platform with a GraphQL API. The client wraps the single GraphQL endpoint with typed Python methods for each supported operation, hiding the GraphQL query-string layer from callers.

## Scope
**Creates:**
- `harnessiq/providers/leadiq/__init__.py`
- `harnessiq/providers/leadiq/api.py`
- `harnessiq/providers/leadiq/client.py`
- `harnessiq/providers/leadiq/requests.py`
- `harnessiq/providers/leadiq/credentials.py`
- `tests/test_leadiq_provider.py`

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/leadiq/__init__.py` | Create: public exports |
| `harnessiq/providers/leadiq/api.py` | Create: URL, headers |
| `harnessiq/providers/leadiq/client.py` | Create: `LeadIQClient` dataclass |
| `harnessiq/providers/leadiq/requests.py` | Create: GraphQL request builders |
| `harnessiq/providers/leadiq/credentials.py` | Create: `LeadIQCredentials` TypedDict |
| `tests/test_leadiq_provider.py` | Create: unit tests |

## API Reference

**Base URL:** `https://api.leadiq.com`
**Authentication:** `X-Api-Key: {api_key}` header

**Endpoint:** `POST /graphql` — single GraphQL endpoint for all operations.

**Operations (each becomes a typed builder function + client method):**

| Operation | Type | Description |
|---|---|---|
| `searchContacts` | Query | Search contacts by filter (name, email, company, title, location) |
| `searchCompanies` | Query | Search companies by filter (name, domain, industry, size) |
| `findPersonByLinkedIn` | Query | Look up a person by LinkedIn URL |
| `enrichContact` | Mutation | Enrich a contact to reveal email/phone |
| `captureLeads` | Mutation | Capture a batch of leads into the system |
| `getCaptures` | Query | List previously captured leads |
| `getContactDetails` | Query | Get full contact details by ID |
| `getCaptureStatus` | Query | Get enrichment/capture status by ID |
| `getTeamActivity` | Query | Get recent team activity |
| `getTags` | Query | List tags in the workspace |
| `addTagToContact` | Mutation | Apply a tag to a contact |
| `removeTagFromContact` | Mutation | Remove a tag from a contact |

**GraphQL request shape:**
```json
{
  "query": "query SearchContacts($filter: ContactFilter!) { searchContacts(filter: $filter) { ... } }",
  "variables": { "filter": { ... } }
}
```

## Approach

**`credentials.py`:**
```python
class LeadIQCredentials(ProviderCredentialConfig):
    api_key: str
```

**`api.py`:**
- `DEFAULT_BASE_URL = "https://api.leadiq.com"`
- `build_headers(api_key)` → `{"X-Api-Key": api_key, "Content-Type": "application/json"}`
- `graphql_url(base_url)` → `{base_url}/graphql`

**`requests.py`:** Each builder returns a `dict` with `"query"` (GraphQL query string) and `"variables"` keys. Use Python triple-quoted strings for the query documents. All variables use `omit_none_values()` before passing.

Example:
```python
def build_search_contacts_request(
    *,
    name: str | None = None,
    email: str | None = None,
    company: str | None = None,
    title: str | None = None,
    location: str | None = None,
    page: int | None = None,
    per_page: int | None = None,
) -> dict[str, object]:
    filter_vars = omit_none_values({
        "name": name, "email": email, "company": company,
        "title": title, "location": location,
    })
    return {
        "query": _SEARCH_CONTACTS_QUERY,
        "variables": omit_none_values({"filter": filter_vars, "page": page, "perPage": per_page}),
    }
```

**`client.py`:**
```python
@dataclass(frozen=True, slots=True)
class LeadIQClient:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json
```
Methods: `search_contacts(...)`, `search_companies(...)`, `find_person_by_linkedin(linkedin_url)`, `enrich_contact(contact_id)`, `capture_leads(contacts)`, `get_captures(...)`, `get_contact_details(contact_id)`, `get_capture_status(capture_id)`, `get_team_activity(...)`, `get_tags()`, `add_tag_to_contact(contact_id, tag)`, `remove_tag_from_contact(contact_id, tag)`

## Assumptions
- LeadIQ uses a single `/graphql` endpoint for all operations.
- GraphQL query documents are defined as module-level string constants in `requests.py`.
- The `variables` dict uses camelCase keys (matching the GraphQL schema).
- Response parsing is left to callers (raw JSON dict returned).

## Acceptance Criteria
- [ ] `from harnessiq.providers.leadiq import LeadIQClient, LeadIQCredentials` works
- [ ] `build_search_contacts_request(name="Alice")` returns a dict with `"query"` and `"variables"` keys
- [ ] `build_enrich_contact_request(contact_id="123")` produces correct mutation payload
- [ ] `build_headers(api_key)` includes `X-Api-Key` header
- [ ] All optional fields omitted when `None`
- [ ] Tests assert on query string content and variable shape
- [ ] All existing tests remain green

## Verification Steps
1. `python -m pytest tests/test_leadiq_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -c "from harnessiq.providers.leadiq import LeadIQClient; print('ok')"`
4. `python -m py_compile harnessiq/providers/leadiq/*.py`

## Dependencies
- Ticket 1

## Drift Guard
Must not implement REST endpoint emulation, response parsing logic, or any agent/tool wiring.
