# Ticket 9: Coresignal Provider

## Title
Add `harnessiq/providers/coresignal/` — full Coresignal API client

## Intent
Implement a complete Coresignal provider package. Coresignal provides professional network data (LinkedIn-equivalent data for people, companies, and job postings) via a REST API with JWT Bearer token authentication. Coverage includes member profiles, company profiles, job listings, school data, employee lists, and historical employee count data.

## Scope
**Creates:**
- `harnessiq/providers/coresignal/__init__.py`
- `harnessiq/providers/coresignal/api.py`
- `harnessiq/providers/coresignal/client.py`
- `harnessiq/providers/coresignal/requests.py`
- `harnessiq/providers/coresignal/credentials.py`
- `tests/test_coresignal_provider.py`

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/coresignal/__init__.py` | Create: public exports |
| `harnessiq/providers/coresignal/api.py` | Create: URL, headers |
| `harnessiq/providers/coresignal/client.py` | Create: `CoresignalClient` dataclass |
| `harnessiq/providers/coresignal/requests.py` | Create: request builders |
| `harnessiq/providers/coresignal/credentials.py` | Create: `CoresignalCredentials` TypedDict |
| `tests/test_coresignal_provider.py` | Create: unit tests |

## API Reference

**Base URL:** `https://api.coresignal.com`
**Authentication:** `Authorization: Bearer {api_key}` header

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| POST | /cdapi/v1/linkedin/member/collect | Collect member profile by LinkedIn URL or shorthand ID |
| POST | /cdapi/v1/linkedin/member/multi_collect | Collect multiple member profiles in one request |
| GET | /cdapi/v1/linkedin/member/search/filter | Filter/search members (query string: `name`, `title`, `company`, `location`, `skills`, `industry`, `limit`, `offset`, `sort_by`, `order`) |
| GET | /cdapi/v1/linkedin/member/{id} | Get member by Coresignal ID |
| GET | /cdapi/v1/linkedin/member/experience | Get experience records for a member (`member_id`) |
| GET | /cdapi/v1/linkedin/member/education | Get education records for a member (`member_id`) |
| GET | /cdapi/v1/linkedin/member/skills | Get skills for a member (`member_id`) |
| POST | /cdapi/v1/linkedin/company/collect | Collect company profile by LinkedIn URL |
| POST | /cdapi/v1/linkedin/company/multi_collect | Collect multiple company profiles |
| GET | /cdapi/v1/linkedin/company/search/filter | Filter/search companies (`name`, `website`, `industry`, `location`, `employee_count_min`, `employee_count_max`, `limit`, `offset`) |
| GET | /cdapi/v1/linkedin/company/{id} | Get company by Coresignal ID |
| GET | /cdapi/v1/linkedin/company/employees | List company employees (`company_id`, `limit`, `offset`, `title_keyword`) |
| GET | /cdapi/v1/linkedin/company/employee_count/collect | Get historical employee count for a company (`company_id`, `date_from`, `date_to`) |
| GET | /cdapi/v1/linkedin/company/updates | Get company posts/updates (`company_id`, `limit`, `offset`) |
| POST | /cdapi/v1/linkedin/job/collect | Collect a job posting by URL or ID |
| GET | /cdapi/v1/linkedin/job/search/filter | Search job postings (`title`, `company`, `location`, `seniority`, `employment_type`, `posted_date`, `limit`, `offset`) |
| GET | /cdapi/v1/linkedin/job/{id} | Get job posting by Coresignal ID |
| POST | /cdapi/v1/linkedin/school/collect | Collect school profile by LinkedIn URL |
| GET | /cdapi/v1/linkedin/school/search/filter | Search schools (`name`, `location`, `limit`, `offset`) |
| GET | /cdapi/v1/linkedin/school/{id} | Get school by Coresignal ID |

## Approach

**`credentials.py`:**
```python
class CoresignalCredentials(ProviderCredentialConfig):
    api_key: str
```

**`api.py`:**
- `DEFAULT_BASE_URL = "https://api.coresignal.com"`
- `build_headers(api_key)` → `{"Authorization": f"Bearer {api_key}"}`
- URL builders:
  - `member_collect_url()`, `member_multi_collect_url()`, `member_search_url()`, `member_url(member_id)`, `member_experience_url()`, `member_education_url()`, `member_skills_url()`
  - `company_collect_url()`, `company_multi_collect_url()`, `company_search_url()`, `company_url(company_id)`, `company_employees_url()`, `company_employee_count_url()`, `company_updates_url()`
  - `job_collect_url()`, `job_search_url()`, `job_url(job_id)`
  - `school_collect_url()`, `school_search_url()`, `school_url(school_id)`

**`requests.py`:**

Collect (POST) builders:
```python
def build_collect_member_request(
    linkedin_url: str | None = None,
    *,
    member_id: str | None = None,
) -> dict[str, object]: ...

def build_multi_collect_members_request(
    urls: list[str],
) -> dict[str, object]: ...
```

Search (GET query params) builders:
```python
def build_member_search_params(
    *,
    name: str | None = None,
    title: str | None = None,
    company: str | None = None,
    location: str | None = None,
    skills: str | None = None,
    industry: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    sort_by: str | None = None,
    order: str | None = None,
) -> dict[str, object]: ...

def build_company_search_params(
    *,
    name: str | None = None,
    website: str | None = None,
    industry: str | None = None,
    location: str | None = None,
    employee_count_min: int | None = None,
    employee_count_max: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, object]: ...

def build_job_search_params(
    *,
    title: str | None = None,
    company: str | None = None,
    location: str | None = None,
    seniority: str | None = None,
    employment_type: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, object]: ...
```

**`client.py`:**
```python
@dataclass(frozen=True, slots=True)
class CoresignalClient:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json
```
Methods:
- Member: `collect_member(linkedin_url, ...)`, `multi_collect_members(urls)`, `search_members(...)`, `get_member(member_id)`, `get_member_experience(member_id)`, `get_member_education(member_id)`, `get_member_skills(member_id)`
- Company: `collect_company(linkedin_url, ...)`, `multi_collect_companies(urls)`, `search_companies(...)`, `get_company(company_id)`, `get_company_employees(company_id, ...)`, `get_company_employee_count(company_id, ...)`, `get_company_updates(company_id, ...)`
- Job: `collect_job(url, ...)`, `search_jobs(...)`, `get_job(job_id)`
- School: `collect_school(linkedin_url)`, `search_schools(...)`, `get_school(school_id)`

## Assumptions
- Collect endpoints are POST with a JSON body containing the LinkedIn URL.
- Search endpoints are GET with query parameters.
- Single-entity get endpoints (`/member/{id}`, etc.) are GET with no additional params.
- The API key is passed as a Bearer token (JWT or opaque API key — same header format).

## Acceptance Criteria
- [ ] `from harnessiq.providers.coresignal import CoresignalClient, CoresignalCredentials` works
- [ ] `build_collect_member_request("https://linkedin.com/in/alice")` returns `{"linkedin_url": "..."}`
- [ ] `build_member_search_params(name="Alice", limit=10)` returns correct query params
- [ ] `build_company_search_params(employee_count_min=50, employee_count_max=500)` includes both count fields
- [ ] `build_headers(api_key)` returns `Authorization: Bearer {api_key}`
- [ ] Optional fields omitted when `None`
- [ ] All existing tests remain green

## Verification Steps
1. `python -m pytest tests/test_coresignal_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -c "from harnessiq.providers.coresignal import CoresignalClient; print('ok')"`
4. `python -m py_compile harnessiq/providers/coresignal/*.py`

## Dependencies
- Ticket 1

## Drift Guard
Must not touch agent modules, other providers, or existing test files.
