# Ticket 5 — Build Snov.io tool operations in `harnessiq/tools/snovio/`

## Title
Build and register Snov.io MCP-style tool operations in `harnessiq/tools/snovio/`

## Intent
PR #55 feedback: the Snov.io provider was merged with only an API client. Agents cannot use it without a tool layer. This ticket builds the full MCP-style operations catalog and tool factory in `tools/snovio/` following the exact same pattern as the service provider tools.

## Scope
- Create `harnessiq/tools/snovio/__init__.py` and `harnessiq/tools/snovio/operations.py`
- Define `SnovioOperation` dataclass with fields: name, category, method, path_hint, required_path_params, payload_kind, payload_required, allow_query
- Build `_SNOVIO_CATALOG` covering all API endpoints exposed by `SnovioClient`
- Implement `build_snovio_request_tool_definition()`, `create_snovio_tools()`, `get_snovio_operation()`, `build_snovio_operation_catalog()`
- The `create_snovio_tools()` factory handles OAuth2 token exchange transparently (uses `SnovioClient.get_access_token()` before dispatching)
- Add `SNOVIO_REQUEST = "snovio.request"` to `harnessiq/shared/tools.py`
- Write unit tests in `tests/test_snovio_provider.py` covering: catalog completeness, tool definition schema, handler execution, error paths

## Relevant Files
- `harnessiq/tools/snovio/__init__.py` — **create**
- `harnessiq/tools/snovio/operations.py` — **create**
- `harnessiq/shared/tools.py` — **update**: add `SNOVIO_REQUEST`
- `tests/test_snovio_provider.py` — **update**: add tool tests

## Approach
Model the Snovio API as named operations following the `api.py` endpoints. Categories:
- Email Discovery: domain_search, get_emails_count, get_emails_from_names, get_email_info, verify_email, get_profile_emails, url_search
- Prospects: get_prospect, add_prospect, update_prospect, delete_prospect
- Prospect Lists: get_prospect_lists, get_list, add_to_list, delete_from_list
- Campaigns: get_all_campaigns, get_campaign, get_campaign_recipients, get_campaign_recipient_status, add_to_campaign, start_campaign, pause_campaign
- Account: get_user_info

The handler should: obtain access token via client, dispatch POST with JSON body or GET with query params as appropriate, return `{operation, method, path, response}`.

Tool description: "Execute authenticated Snov.io API operations for email discovery and outreach automation. Snov.io provides email finder, verifier, prospect management, list management, and drip campaign automation. Use domain_search and get_emails_from_names to find contact emails, verify_email to validate deliverability, add_prospect to build your prospect database, and campaign operations to automate outbound sequences."

## Acceptance Criteria
- [ ] `harnessiq/tools/snovio/operations.py` exists with full catalog (≥20 operations)
- [ ] `create_snovio_tools()` returns a `tuple[RegisteredTool, ...]`
- [ ] `SNOVIO_REQUEST` in `harnessiq/shared/tools.py`
- [ ] Tool handler correctly calls `SnovioClient` methods
- [ ] Tests cover catalog completeness, schema validation, handler execution with mocked client
- [ ] `pytest tests/test_snovio_provider.py -v` passes
- [ ] `mypy` clean

## Verification Steps
1. `python -c "from harnessiq.tools.snovio.operations import create_snovio_tools, build_snovio_operation_catalog; print(len(build_snovio_operation_catalog()), 'ops')"`
2. `pytest tests/test_snovio_provider.py -v`
3. `mypy harnessiq/tools/snovio/`

## Dependencies
Ticket 1 (shared credentials) should complete first, though can be implemented in parallel since the tool factory accepts a `SnovioClient` directly.

## Drift Guard
Do not modify `providers/snovio/` beyond what is needed to import credential types. Do not build OAuth2 refresh logic — use the existing `get_access_token()` pattern.
