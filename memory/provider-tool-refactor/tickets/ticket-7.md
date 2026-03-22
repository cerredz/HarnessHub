# Ticket 7 — Build Salesforge tool operations in `harnessiq/tools/salesforge/`

## Title
Build and register Salesforge MCP-style tool operations in `harnessiq/tools/salesforge/`

## Intent
PR #57 feedback: Salesforge provider merged with only an API client. Build the tool layer.

## Scope
- Create `harnessiq/tools/salesforge/__init__.py` and `operations.py`
- Model Salesforge API endpoints from `providers/salesforge/api.py` + `client.py`
- Add `SALESFORGE_REQUEST = "salesforge.request"` to `harnessiq/shared/tools.py`
- Extend `tests/test_salesforge_provider.py` with tool-layer tests

## Approach
Read providers/salesforge to enumerate all endpoints, categorize (Workspaces, Campaigns, Prospects, Analytics, etc.), build MCP-style catalog. Tool description: Salesforge is an AI-powered sales email outreach platform for managing multi-mailbox campaigns.

## Acceptance Criteria
- [ ] Full catalog in `tools/salesforge/operations.py`
- [ ] `create_salesforge_tools()` working
- [ ] `SALESFORGE_REQUEST` in shared
- [ ] Tests pass, mypy clean

## Dependencies
None

## Drift Guard
Only salesforge tool layer. Do not modify provider.
