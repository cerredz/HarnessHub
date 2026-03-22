# Ticket 11 — Build Proxycurl tool operations in `harnessiq/tools/proxycurl/`

## Title
Build and register Proxycurl MCP-style tool operations in `harnessiq/tools/proxycurl/` (deprecated provider)

## Intent
PR #61 feedback: Proxycurl provider merged with only an API client. Build the tool layer for consistency. Note: Proxycurl service was deprecated/shut down Jan 2025 — the description must include a clear deprecation warning.

## Scope
- Create `harnessiq/tools/proxycurl/__init__.py` and `operations.py`
- Add `PROXYCURL_REQUEST = "proxycurl.request"` to `harnessiq/shared/tools.py`
- Extend `tests/test_proxycurl_provider.py` with tool-layer tests

## Approach
Build catalog from `providers/proxycurl/api.py` + `client.py`. Tool description must include: "⚠️ DEPRECATED: Proxycurl shut down in January 2025. This tool will return errors in production." Operations cover LinkedIn profile enrichment, company enrichment, job search, employee listing.

## Acceptance Criteria
- [ ] Full catalog in `tools/proxycurl/operations.py`
- [ ] `create_proxycurl_tools()` working
- [ ] Deprecation warning in tool description
- [ ] `PROXYCURL_REQUEST` in shared
- [ ] Tests pass, mypy clean

## Dependencies
None

## Drift Guard
Only proxycurl tool layer.
