# Ticket 7: People Data Labs Provider

## Title
Add `harnessiq/providers/peopledatalabs/` — full People Data Labs API client

## Intent
Implement a complete People Data Labs (PDL) provider package. PDL is a people and company data enrichment platform with one of the largest professional databases. The API covers person enrichment, bulk person enrichment, person search, company enrichment, bulk company enrichment, company search, IP enrichment, and data normalization endpoints.

## Scope
**Creates:**
- `harnessiq/providers/peopledatalabs/__init__.py`
- `harnessiq/providers/peopledatalabs/api.py`
- `harnessiq/providers/peopledatalabs/client.py`
- `harnessiq/providers/peopledatalabs/requests.py`
- `harnessiq/providers/peopledatalabs/credentials.py`
- `tests/test_peopledatalabs_provider.py`

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/peopledatalabs/__init__.py` | Create: public exports |
| `harnessiq/providers/peopledatalabs/api.py` | Create: URL, headers |
| `harnessiq/providers/peopledatalabs/client.py` | Create: `PeopleDataLabsClient` dataclass |
| `harnessiq/providers/peopledatalabs/requests.py` | Create: request builders |
| `harnessiq/providers/peopledatalabs/credentials.py` | Create: `PeopleDataLabsCredentials` TypedDict |
| `tests/test_peopledatalabs_provider.py` | Create: unit tests |

## API Reference

**Base URL:** `https://api.peopledatalabs.com`
**Authentication:** `X-Api-Key: {api_key}` header

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | /v5/person/enrich | Enrich a person (email, name, LinkedIn, phone, location params) |
| POST | /v5/person/bulk | Bulk enrich up to 100 persons per request |
| GET | /v5/person/search | SQL-style person search (`sql` or `query` param) |
| POST | /v5/person/identify | Identify a person from partial info |
| GET | /v5/person/retrieve/{id} | Retrieve person by PDL ID |
| POST | /v5/person/retrieve/bulk | Bulk retrieve persons by PDL IDs |
| GET | /v5/company/enrich | Enrich a company (name, website, profile, ticker, etc.) |
| POST | /v5/company/bulk | Bulk enrich up to 100 companies |
| GET | /v5/company/search | SQL-style company search |
| POST | /v5/company/cleaner | Clean/normalize raw company data |
| GET | /v5/company/retrieve/{id} | Retrieve company by PDL ID |
| POST | /v5/ip/enrich | Enrich an IP address |
| GET | /v5/autocomplete | Autocomplete for field values (`field`, `text`, `size`) |
| GET | /v5/skill/enrich | Normalize a skill string to PDL taxonomy |
| GET | /v5/location/enrich | Normalize a location string |
| GET | /v5/school/enrich | Normalize a school name |
| GET | /v5/job_title/enrich | Normalize a job title string |
| GET | /v5/phone/enrich | Enrich/normalize a phone number |
| POST | /v5/changelog | Retrieve changelog records for a person/company |

**Person enrich params (key):** `email`, `phone`, `name`, `first_name`, `last_name`, `company`, `title`, `location`, `linkedin_url`, `profile`, `pretty` (bool for pretty-print), `min_likelihood`, `required` (field mask)

**Bulk enrich request shape:**
```json
{
  "requests": [
    {"params": {"email": "a@b.com"}, "metadata": {"custom_id": "001"}},
    {"params": {"linkedin_url": "https://linkedin.com/in/alice"}}
  ],
  "required": "emails",
  "pretty": false
}
```

## Approach

**`credentials.py`:**
```python
class PeopleDataLabsCredentials(ProviderCredentialConfig):
    api_key: str
```

**`api.py`:**
- `DEFAULT_BASE_URL = "https://api.peopledatalabs.com"`
- `build_headers(api_key)` → `{"X-Api-Key": api_key}`
- URL builders per endpoint: `person_enrich_url()`, `person_bulk_url()`, `person_search_url()`, `person_identify_url()`, `person_retrieve_url(person_id)`, `person_retrieve_bulk_url()`, `company_enrich_url()`, `company_bulk_url()`, `company_search_url()`, `company_cleaner_url()`, `company_retrieve_url(company_id)`, `ip_enrich_url()`, `autocomplete_url()`, `skill_enrich_url()`, `location_enrich_url()`, `school_enrich_url()`, `job_title_enrich_url()`, `phone_enrich_url()`, `changelog_url()`

**`requests.py`:**

Person enrich (GET params):
```python
def build_person_enrich_params(
    *,
    email: str | None = None,
    phone: str | None = None,
    name: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    company: str | None = None,
    title: str | None = None,
    location: str | None = None,
    linkedin_url: str | None = None,
    profile: str | None = None,
    min_likelihood: int | None = None,
    required: str | None = None,
    pretty: bool | None = None,
) -> dict[str, object]: ...
```

Bulk enrich (POST body):
```python
def build_person_bulk_request(
    requests: list[dict[str, object]],
    *,
    required: str | None = None,
    pretty: bool | None = None,
) -> dict[str, object]: ...
```

Search (GET params):
```python
def build_person_search_params(
    *,
    sql: str | None = None,
    query: dict | None = None,
    size: int | None = None,
    from_: int | None = None,
    scroll_token: str | None = None,
    pretty: bool | None = None,
) -> dict[str, object]: ...
```

Company enrich, bulk, search builders follow the same pattern.

Normalization endpoints (skill, location, school, job_title, phone) all accept a `name` (or `phone`) param plus optional `pretty`.

**`client.py`:**
```python
@dataclass(frozen=True, slots=True)
class PeopleDataLabsClient:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json
```
Methods: `enrich_person(...)`, `bulk_enrich_persons(...)`, `search_persons(...)`, `identify_person(...)`, `retrieve_person(person_id)`, `retrieve_persons_bulk(ids)`, `enrich_company(...)`, `bulk_enrich_companies(...)`, `search_companies(...)`, `clean_company(...)`, `retrieve_company(company_id)`, `enrich_ip(ip_address, ...)`, `autocomplete(field, text, ...)`, `enrich_skill(name)`, `enrich_location(location)`, `enrich_school(name)`, `enrich_job_title(job_title)`, `enrich_phone(phone)`, `get_changelog(...)`

## Assumptions
- Enrich endpoints use GET with query parameters; bulk and write endpoints use POST with JSON body.
- `from_` parameter maps to `from` query param (renamed to avoid Python keyword conflict).
- `required` is a field mask string (e.g. `"emails OR phone_numbers"`).

## Acceptance Criteria
- [ ] `from harnessiq.providers.peopledatalabs import PeopleDataLabsClient, PeopleDataLabsCredentials` works
- [ ] `build_person_enrich_params(email="a@b.com", min_likelihood=5)` returns correct GET params
- [ ] `build_person_bulk_request([{"params": {"email": "a@b.com"}}])` returns correct body
- [ ] `build_person_search_params(sql="SELECT * FROM person WHERE ...")` includes `sql` key
- [ ] `build_headers(api_key)` returns `X-Api-Key` header
- [ ] All optional fields omitted when `None`
- [ ] All existing tests remain green

## Verification Steps
1. `python -m pytest tests/test_peopledatalabs_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -c "from harnessiq.providers.peopledatalabs import PeopleDataLabsClient; print('ok')"`
4. `python -m py_compile harnessiq/providers/peopledatalabs/*.py`

## Dependencies
- Ticket 1

## Drift Guard
Must not touch agent modules, other providers, or existing test files.
