# Ticket 9 — Build ZoomInfo tool operations in `harnessiq/tools/zoominfo/`

## Title
Build and register ZoomInfo MCP-style tool operations in `harnessiq/tools/zoominfo/`

## Intent
PR #59 feedback: ZoomInfo provider merged with only an API client. Build the tool layer.

## Scope
- Create `harnessiq/tools/zoominfo/__init__.py` and `operations.py`
- Model ZoomInfo API endpoints from `providers/zoominfo/api.py` + `client.py`
- Add `ZOOMINFO_REQUEST = "zoominfo.request"` to `harnessiq/shared/tools.py`
- Extend `tests/test_zoominfo_provider.py` with tool-layer tests

## Approach
ZoomInfo uses JWT auth (two-step). The tool handler must authenticate first then dispatch. Operations: search_contacts, search_companies, search_intent, search_news, search_scoops, enrich_contact, enrich_company, enrich_ip, bulk_enrich_contacts, bulk_enrich_companies, lookup_output_fields, get_usage. Tool description: ZoomInfo is a B2B intelligence platform providing verified company and contact data, intent signals, and technographic insights.

## Acceptance Criteria
- [ ] Full catalog in `tools/zoominfo/operations.py`
- [ ] `create_zoominfo_tools()` handles JWT auth transparently
- [ ] `ZOOMINFO_REQUEST` in shared
- [ ] Tests pass, mypy clean

## Dependencies
None

## Drift Guard
Only zoominfo tool layer. JWT auth logic stays in `providers/zoominfo/client.py`.
