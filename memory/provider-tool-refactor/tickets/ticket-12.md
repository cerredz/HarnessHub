# Ticket 12 — Build Coresignal tool operations in `harnessiq/tools/coresignal/`

## Title
Build and register Coresignal MCP-style tool operations in `harnessiq/tools/coresignal/`

## Intent
PR #62 feedback: Coresignal provider merged with only an API client. Build the tool layer.

## Scope
- Create `harnessiq/tools/coresignal/__init__.py` and `operations.py`
- Add `CORESIGNAL_REQUEST = "coresignal.request"` to `harnessiq/shared/tools.py`
- Extend `tests/test_coresignal_provider.py` with tool-layer tests

## Approach
Build catalog from `providers/coresignal/api.py` + `client.py`. Coresignal provides fresh employee, company, and job data. Tool description: "Coresignal provides real-time professional network data including employee profiles, company records, and job postings for prospecting and market research."

## Acceptance Criteria
- [ ] Full catalog in `tools/coresignal/operations.py`
- [ ] `create_coresignal_tools()` working
- [ ] `CORESIGNAL_REQUEST` in shared
- [ ] Tests pass, mypy clean

## Dependencies
None

## Drift Guard
Only coresignal tool layer.
