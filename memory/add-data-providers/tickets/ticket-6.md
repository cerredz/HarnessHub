# Ticket 6: ZoomInfo Provider

## Title
Add `harnessiq/providers/zoominfo/` — full ZoomInfo API client

## Intent
Implement a complete ZoomInfo provider package. ZoomInfo is a B2B intelligence platform. Its API requires a two-step authentication (username+password → JWT via POST /authenticate) then uses the JWT as a Bearer token for all subsequent calls. The client covers contact search, company search, contact enrichment, company enrichment, intent data, bulk lookups, and IP enrichment.

## Scope
**Creates:**
- `harnessiq/providers/zoominfo/__init__.py`
- `harnessiq/providers/zoominfo/api.py`
- `harnessiq/providers/zoominfo/client.py`
- `harnessiq/providers/zoominfo/requests.py`
- `harnessiq/providers/zoominfo/credentials.py`
- `tests/test_zoominfo_provider.py`

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/zoominfo/__init__.py` | Create: public exports |
| `harnessiq/providers/zoominfo/api.py` | Create: URL, headers |
| `harnessiq/providers/zoominfo/client.py` | Create: `ZoomInfoClient` dataclass |
| `harnessiq/providers/zoominfo/requests.py` | Create: request builders |
| `harnessiq/providers/zoominfo/credentials.py` | Create: `ZoomInfoCredentials` TypedDict |
| `tests/test_zoominfo_provider.py` | Create: unit tests |

## API Reference

**Base URL:** `https://api.zoominfo.com`
**Authentication:**
- Step 1: `POST /authenticate` with `{"username": ..., "password": ...}` → returns `{"jwt": "..."}`
- Step 2: All other requests use `Authorization: Bearer {jwt}` header

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| POST | /authenticate | Exchange credentials for JWT |
| POST | /search/contact | Search contacts (name, title, company, location, etc.) |
| POST | /search/company | Search companies (name, industry, employee range, revenue, etc.) |
| POST | /search/intent | Search intent data (topics, companies showing buying intent) |
| POST | /search/news | Search news/technographic signals |
| POST | /search/scoop | Search business scoops/triggers |
| POST | /enrich/contact | Enrich a contact by name/email/LinkedIn |
| POST | /enrich/company | Enrich a company by name/website/domain |
| POST | /enrich/ip | Identify company from an IP address |
| POST | /bulk/contact | Bulk contact enrichment (batch of inputs) |
| POST | /bulk/company | Bulk company enrichment (batch of inputs) |
| POST | /lookup/outputfields | Get available output fields for a given entity type |
| GET | /usage | Get API usage/quota stats for the authenticated user |

**Search request shape (contacts example):**
```json
{
  "outputFields": ["id", "firstName", "lastName", "email", "phone", "companyName", "jobTitle"],
  "matchFilter": {
    "firstName": "Alice",
    "lastName": "Smith",
    "companyName": "Acme Corp",
    "personHasMobilePhone": true
  },
  "rpp": 25,
  "page": 1
}
```

## Approach

**`credentials.py`:**
```python
class ZoomInfoCredentials(ProviderCredentialConfig):
    username: str
    password: str
```

**`api.py`:**
- `DEFAULT_BASE_URL = "https://api.zoominfo.com"`
- `build_headers(jwt_token)` → `{"Authorization": f"Bearer {jwt_token}"}`
- `build_auth_headers()` → `{}` (no auth header for the authenticate endpoint itself)
- URL builders: `authenticate_url()`, `search_contact_url()`, `search_company_url()`, `search_intent_url()`, `search_news_url()`, `search_scoop_url()`, `enrich_contact_url()`, `enrich_company_url()`, `enrich_ip_url()`, `bulk_contact_url()`, `bulk_company_url()`, `lookup_outputfields_url()`, `usage_url()`

**`requests.py`:**
- `build_authenticate_request(username, password)` — `{"username": ..., "password": ...}`
- `build_search_contact_request(*, output_fields, match_filter, rpp, page)` — search body
- `build_search_company_request(*, output_fields, match_filter, rpp, page)`
- `build_search_intent_request(*, company_ids, topics, date_range, ...)`
- `build_enrich_contact_request(*, match_input, output_fields)` — `match_input` is a list of match criteria
- `build_enrich_company_request(*, match_input, output_fields)`
- `build_enrich_ip_request(ip_address, *, output_fields)`
- `build_bulk_contact_request(match_inputs, *, output_fields)`
- `build_bulk_company_request(match_inputs, *, output_fields)`
- `build_lookup_outputfields_request(entity_type)` — `"contact"` or `"company"`

**`client.py`:**
```python
@dataclass(frozen=True, slots=True)
class ZoomInfoClient:
    username: str
    password: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json
```
Methods: `authenticate()` (returns JWT string), `search_contacts(jwt, ...)`, `search_companies(jwt, ...)`, `search_intent(jwt, ...)`, `search_news(jwt, ...)`, `search_scoop(jwt, ...)`, `enrich_contact(jwt, ...)`, `enrich_company(jwt, ...)`, `enrich_ip(jwt, ip)`, `bulk_contacts(jwt, ...)`, `bulk_companies(jwt, ...)`, `lookup_output_fields(jwt, entity_type)`, `get_usage(jwt)`

## Assumptions
- JWT is short-lived and callers are responsible for re-authenticating when it expires.
- `ZoomInfoClient` stores credentials for `authenticate()`; callers pass the JWT to other methods.
- The `/authenticate` endpoint does not require an Authorization header.
- `outputFields` is always a list of strings; the caller specifies which fields to retrieve.

## Acceptance Criteria
- [ ] `from harnessiq.providers.zoominfo import ZoomInfoClient, ZoomInfoCredentials` works
- [ ] `build_authenticate_request("user", "pass")` returns `{"username": "user", "password": "pass"}`
- [ ] `build_search_contact_request(output_fields=["id","email"], match_filter={"firstName":"Alice"})` returns correct shape
- [ ] `build_enrich_ip_request("1.2.3.4", output_fields=["companyName"])` includes both fields
- [ ] `build_headers(jwt)` returns `{"Authorization": "Bearer {jwt}"}`
- [ ] All existing tests remain green

## Verification Steps
1. `python -m pytest tests/test_zoominfo_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -c "from harnessiq.providers.zoominfo import ZoomInfoClient; print('ok')"`
4. `python -m py_compile harnessiq/providers/zoominfo/*.py`

## Dependencies
- Ticket 1

## Drift Guard
Must not touch agent modules, other providers, or existing test files.
