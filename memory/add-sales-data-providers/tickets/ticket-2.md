# Ticket 2 — ZeroBounce Provider + Tool + Registration

## Title
Add ZeroBounce provider and tool to harnessiq

## Intent
ZeroBounce is an email validation and intelligence platform. This ticket adds the complete provider and tool layer, enabling agents to validate emails (real-time and bulk), score emails with AI, find email addresses, check activity data, and manage account filters.

## Scope
**In scope:**
- `harnessiq/providers/zerobounce/` — api.py, client.py, operations.py, __init__.py
- `harnessiq/tools/zerobounce/` — operations.py, __init__.py
- `harnessiq/shared/tools.py` — add `ZEROBOUNCE_REQUEST` constant
- `harnessiq/toolset/catalog.py` — add ToolEntry + factory map entry
- `tests/test_zerobounce_provider.py`

**Out of scope:** S3 integration endpoints, sandbox mode configuration, deprecated v1 endpoints.

## Relevant Files
- `harnessiq/providers/zerobounce/__init__.py` — CREATE
- `harnessiq/providers/zerobounce/api.py` — CREATE: DEFAULT_BASE_URL, DEFAULT_BULK_BASE_URL, build_headers(), url()
- `harnessiq/providers/zerobounce/client.py` — CREATE: ZeroBounceCredentials (with base_url + bulk_base_url), ZeroBounceClient
- `harnessiq/providers/zerobounce/operations.py` — CREATE: catalog + tool factory
- `harnessiq/tools/zerobounce/__init__.py` — CREATE
- `harnessiq/tools/zerobounce/operations.py` — CREATE: tool factory with rich descriptions
- `harnessiq/shared/tools.py` — MODIFY
- `harnessiq/toolset/catalog.py` — MODIFY
- `tests/test_zerobounce_provider.py` — CREATE

## Approach
Follow the exa provider pattern. ZeroBounce has a unique dual-base-URL architecture:
- Standard operations: `https://api.zerobounce.net/v2/`
- Bulk file operations: `https://bulkapi.zerobounce.net/v2/`

**Credential design:**
```python
@dataclass(frozen=True, slots=True)
class ZeroBounceCredentials:
    api_key: str
    base_url: str = "https://api.zerobounce.net"
    bulk_base_url: str = "https://bulkapi.zerobounce.net"
    timeout_seconds: float = 60.0
```

**Auth pattern:** `api_key` as query parameter (`?api_key=<key>`). No Authorization header. `build_headers()` returns only `{"Content-Type": "application/json"}`. The `api_key` is injected into the URL via `join_url(base, path, query={"api_key": key, **other_query})`.

**ZeroBounceOperation** adds a `use_bulk_base: bool = False` field. `_build_prepared_request` selects `credentials.bulk_base_url` when `op.use_bulk_base` is True.

**Operation catalog:**

*Account:*
- `get_credits` — GET `/v2/getcredits` (standard base)
- `get_api_usage` — GET `/v2/getapiusage` (standard base, query: start_date, end_date)

*Email Validation (real-time):*
- `validate_email` — GET `/v2/validate` (standard base, query: email, ip_address optional)
- `validate_batch` — POST `/v2/validatebatch` (standard base, payload: email_batch array)

*Email Validation (bulk file):*
- `bulk_send_file` — POST `/v2/sendfile` (BULK base, multipart payload)
- `bulk_file_status` — GET `/v2/filestatus` (BULK base, query: file_id)
- `bulk_get_file` — GET `/v2/getfile` (BULK base, query: file_id)
- `bulk_delete_file` — GET `/v2/deletefile` (BULK base, query: file_id)

*AI Scoring:*
- `score_email` — GET `/v2/scoring` (standard base, query: email)
- `bulk_scoring_send_file` — POST `/v2/scoring/sendfile` (BULK base)
- `bulk_scoring_file_status` — GET `/v2/scoring/filestatus` (BULK base, query: file_id)
- `bulk_scoring_get_file` — GET `/v2/scoring/getfile` (BULK base, query: file_id)
- `bulk_scoring_delete_file` — GET `/v2/scoring/deletefile` (BULK base, query: file_id)

*Email Finder:*
- `find_email` — GET `/v2/guessformat` (standard base, query: domain, first_name, last_name)
- `bulk_finder_send_file` — POST `/v2/email-finder/sendfile` (BULK base)
- `bulk_finder_file_status` — GET `/v2/email-finder/filestatus` (BULK base, query: file_id)
- `bulk_finder_get_file` — GET `/v2/email-finder/getfile` (BULK base, query: file_id)
- `bulk_finder_delete_file` — GET `/v2/email-finder/deletefile` (BULK base, query: file_id)

*Activity Data:*
- `get_activity_data` — GET `/v2/activity` (standard base, query: email)

*Filters (allowlist/blocklist):*
- `list_filters` — GET `/v2/filters/list` (standard base)
- `add_filter` — POST `/v2/filters/add` (standard base, payload: rule, target, value)
- `delete_filter` — POST `/v2/filters/delete` (standard base, payload: rule, target, value)

Tool key: `zerobounce.request`. Tool name: `zerobounce_request`.

## Assumptions
- `api_key` query param injection is cleanly handled via `join_url(base, path, query={"api_key": key, **caller_query})`
- Bulk file upload (multipart) is documented but our tool treats payload as JSON — callers handle multipart externally or use the JSON endpoints where possible
- Filter endpoints accept JSON payload (our layer sends JSON; ZeroBounce also accepts JSON on these endpoints)

## Acceptance Criteria
- [ ] `ZeroBounceCredentials(api_key)` validates blank key
- [ ] `ZeroBounceCredentials.bulk_base_url` defaults to `https://bulkapi.zerobounce.net`
- [ ] All 24 operations present in catalog
- [ ] Bulk operations route to `bulk_base_url`, others to `base_url`
- [ ] `api_key` appears in constructed URLs (via query param injection), not in headers
- [ ] `create_zerobounce_tools(credentials=creds)` returns 1 RegisteredTool keyed `zerobounce.request`
- [ ] `ZEROBOUNCE_REQUEST` exported from `shared/tools.py`
- [ ] ToolEntry and factory map entry present in catalog
- [ ] All tests pass

## Verification Steps
1. `python -m pytest tests/test_zerobounce_provider.py -v`
2. `python -c "from harnessiq.providers.zerobounce import ZeroBounceCredentials; print('OK')"`
3. `python -c "from harnessiq.toolset import get_family; print(get_family('zerobounce', credentials=None))"` (should raise missing credentials error)

## Dependencies
None.

## Drift Guard
This ticket must not touch any existing provider. The dual-base-URL pattern is contained entirely within the zerobounce module. No changes to the HTTP transport layer.
