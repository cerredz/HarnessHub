# Ticket 10 — Build PeopleDataLabs tool operations in `harnessiq/tools/peopledatalabs/`

## Title
Build and register People Data Labs MCP-style tool operations in `harnessiq/tools/peopledatalabs/`

## Intent
PR #60 feedback: PDL provider merged with only an API client. Build the tool layer.

## Scope
- Create `harnessiq/tools/peopledatalabs/__init__.py` and `operations.py`
- Add `PEOPLEDATALABS_REQUEST = "peopledatalabs.request"` to `harnessiq/shared/tools.py`
- Extend `tests/test_peopledatalabs_provider.py` with tool-layer tests

## Approach
PDL provides person enrichment, company enrichment, bulk enrichment, and search endpoints. Build catalog from `providers/peopledatalabs/api.py` + `client.py`. Tool description: PDL is a data enrichment API providing person and company data at scale including emails, phones, job history, and firmographics.

## Acceptance Criteria
- [ ] Full catalog in `tools/peopledatalabs/operations.py`
- [ ] `create_peopledatalabs_tools()` working
- [ ] `PEOPLEDATALABS_REQUEST` in shared
- [ ] Tests pass, mypy clean

## Dependencies
None

## Drift Guard
Only peopledatalabs tool layer.
