# Ticket 8: Proxycurl Provider

## Title
Add `harnessiq/providers/proxycurl/` — full Proxycurl API client

## Intent
Implement a complete Proxycurl provider package. Proxycurl is a LinkedIn data API that allows scraping LinkedIn profiles, companies, job listings, and performing people/company lookups. It is directly relevant to the LinkedIn agent workflow in this codebase.

## Scope
**Creates:**
- `harnessiq/providers/proxycurl/__init__.py`
- `harnessiq/providers/proxycurl/api.py`
- `harnessiq/providers/proxycurl/client.py`
- `harnessiq/providers/proxycurl/requests.py`
- `harnessiq/providers/proxycurl/credentials.py`
- `tests/test_proxycurl_provider.py`

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/proxycurl/__init__.py` | Create: public exports |
| `harnessiq/providers/proxycurl/api.py` | Create: URL, headers |
| `harnessiq/providers/proxycurl/client.py` | Create: `ProxycurlClient` dataclass |
| `harnessiq/providers/proxycurl/requests.py` | Create: request builders |
| `harnessiq/providers/proxycurl/credentials.py` | Create: `ProxycurlCredentials` TypedDict |
| `tests/test_proxycurl_provider.py` | Create: unit tests |

## API Reference

**Base URL:** `https://nubela.co`
**Authentication:** `Authorization: Bearer {api_key}` header

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | /proxycurl/api/v2/linkedin | Scrape LinkedIn person profile (`url` required; optional `extra`, `github_profile_id`, `facebook_profile_id`, `twitter_profile_id`, `personal_contact_number`, `personal_email`, `inferred_salary`, `skills`, `use_cache`, `fallback_to_cache`) |
| GET | /proxycurl/api/linkedin/company | Scrape LinkedIn company profile (`url`; optional `categories`, `funding_data`, `exit_data`, `acquisitions`, `extra`, `use_cache`, `fallback_to_cache`) |
| GET | /proxycurl/api/linkedin/company/job | List job postings for a company (`linkedin_company_profile_url`, `keyword`, `type`, `experience`, `when`, `geo_id`) |
| GET | /proxycurl/api/v2/linkedin/company/resolve | Resolve company from name/domain (`company_name`, `company_domain`, `company_location`, `similarity_checks`) |
| GET | /proxycurl/api/linkedin/company/employees | List company employees (`linkedin_company_profile_url`, `country`, `enrich_profiles`, `role_search`, `page_size`, `employment_status`, `sort_by`, `resolve_numeric_id`) |
| GET | /proxycurl/api/linkedin/company/employees/count | Count employees for a company (`linkedin_company_profile_url`, `employment_status`) |
| POST | /proxycurl/api/v2/linkedin/company/employees/bulk-retrieve | Bulk retrieve employee profiles (`linkedin_company_profile_url`, `country`, `enrich_profiles`, `role_search`) |
| GET | /proxycurl/api/linkedin/person/resolve | Resolve person from name/company (`first_name`, `last_name`, `company_domain`, `location`, `title`, `twitter_profile_id`, `facebook_profile_id`, `linkedin_company_profile_url`, `similarity_checks`) |
| GET | /proxycurl/api/v2/linkedin/person/lookup/email | Find LinkedIn profile by email (`email`, `lookup_depth`, `enrich_profile`) |
| GET | /proxycurl/api/v2/linkedin/person/lookup/github | Find LinkedIn profile by GitHub username (`github_profile_id`, `enrich_profile`) |
| GET | /proxycurl/api/v2/linkedin/person/lookup/twitter | Find LinkedIn profile by Twitter handle (`twitter_profile_id`, `enrich_profile`) |
| GET | /proxycurl/api/v2/linkedin/google/search/person | Search people on Google (`first_name`, `last_name`, `keyword`, `geo_id`, `page_size`, `enrich_profiles`) |
| GET | /proxycurl/api/v2/linkedin/google/search/company | Search companies on Google (`keyword`, `page_size`, `enrich_profiles`) |
| GET | /proxycurl/api/v2/linkedin/google/search/job-listing | Search job listings on Google (`keyword`, `geo_id`, `page_size`) |
| GET | /proxycurl/api/v2/linkedin/job | Get job listing details (`url`) |
| GET | /proxycurl/api/v2/linkedin/school | Scrape LinkedIn school profile (`url`, `use_cache`, `fallback_to_cache`) |
| GET | /proxycurl/api/v2/linkedin/role/search | Find profiles by role at company (`role`, `linkedin_company_profile_url`, `page_size`, `enrich_profiles`) |
| GET | /proxycurl/api/v2/linkedin/company/update | Get company recent updates (`linkedin_company_profile_url`, `page_size`, `pagination_token`) |
| GET | /proxycurl/api/v2/linkedin/company/funding/list | List company funding rounds (`linkedin_company_profile_url`) |
| GET | /proxycurl/api/credits/balance | Get remaining API credit balance |

## Approach

**`credentials.py`:**
```python
class ProxycurlCredentials(ProviderCredentialConfig):
    api_key: str
```

**`api.py`:**
- `DEFAULT_BASE_URL = "https://nubela.co"`
- `build_headers(api_key)` → `{"Authorization": f"Bearer {api_key}"}`
- URL builder per endpoint (all GET params, no path params except bulk which is POST)

**`requests.py`:** All endpoints use GET with query parameters. Builder functions return `dict[str, object]` for query param dicts via `omit_none_values()`. The bulk-retrieve endpoint returns a POST body dict.

Key builders:
```python
def build_person_profile_params(
    linkedin_profile_url: str,
    *,
    extra: str | None = None,         # "include" or "exclude"
    inferred_salary: str | None = None,
    skills: str | None = None,
    personal_contact_number: str | None = None,
    personal_email: str | None = None,
    use_cache: str | None = None,      # "if-present" or "if-recent"
    fallback_to_cache: str | None = None,
) -> dict[str, object]: ...

def build_company_profile_params(
    linkedin_company_profile_url: str,
    *,
    categories: str | None = None,
    funding_data: str | None = None,
    exit_data: str | None = None,
    acquisitions: str | None = None,
    extra: str | None = None,
    use_cache: str | None = None,
    fallback_to_cache: str | None = None,
) -> dict[str, object]: ...
```

**`client.py`:**
```python
@dataclass(frozen=True, slots=True)
class ProxycurlClient:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json
```
Methods: `get_person_profile(url, ...)`, `get_company_profile(url, ...)`, `get_company_jobs(linkedin_url, ...)`, `resolve_company(...)`, `get_company_employees(linkedin_url, ...)`, `count_company_employees(linkedin_url, ...)`, `bulk_retrieve_employees(linkedin_url, ...)`, `resolve_person(...)`, `find_person_by_email(email, ...)`, `find_person_by_github(github_id, ...)`, `find_person_by_twitter(twitter_id, ...)`, `search_persons(...)`, `search_companies(keyword, ...)`, `search_jobs(keyword, ...)`, `get_job_listing(url)`, `get_school_profile(url, ...)`, `search_by_role(role, linkedin_url, ...)`, `get_company_updates(linkedin_url, ...)`, `get_company_funding(linkedin_url)`, `get_credit_balance()`

## Assumptions
- All endpoints use GET with query params except `bulk-retrieve` which uses POST.
- `use_cache` accepts `"if-present"` (use any cached result) or `"if-recent"` (use if < 29 days old).
- Credit balance returns remaining credits for the API key.

## Acceptance Criteria
- [ ] `from harnessiq.providers.proxycurl import ProxycurlClient, ProxycurlCredentials` works
- [ ] `build_person_profile_params("https://linkedin.com/in/alice")` returns `{"linkedin_profile_url": "..."}`
- [ ] `build_company_profile_params("https://linkedin.com/company/acme", funding_data="include")` includes `funding_data`
- [ ] `build_headers(api_key)` returns `Authorization: Bearer {api_key}`
- [ ] Optional params omitted when `None`
- [ ] All existing tests remain green

## Verification Steps
1. `python -m pytest tests/test_proxycurl_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -c "from harnessiq.providers.proxycurl import ProxycurlClient; print('ok')"`
4. `python -m py_compile harnessiq/providers/proxycurl/*.py`

## Dependencies
- Ticket 1

## Drift Guard
Must not touch agent modules, other providers, or existing test files.
