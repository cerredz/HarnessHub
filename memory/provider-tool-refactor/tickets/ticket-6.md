# Ticket 6 — Build LeadIQ tool operations in `harnessiq/tools/leadiq/`

## Title
Build and register LeadIQ MCP-style tool operations in `harnessiq/tools/leadiq/`

## Intent
PR #56 feedback: LeadIQ provider merged with only an API client. Build the tool layer in `tools/leadiq/` so agents can discover, enrich, and track B2B contacts.

## Scope
- Create `harnessiq/tools/leadiq/__init__.py` and `harnessiq/tools/leadiq/operations.py`
- Model LeadIQ API endpoints as named operations from `providers/leadiq/api.py` and `client.py`
- Add `LEADIQ_REQUEST = "leadiq.request"` to `harnessiq/shared/tools.py`
- Extend `tests/test_leadiq_provider.py` with tool-layer tests

## Approach
Read `providers/leadiq/api.py` + `client.py` to enumerate all endpoints, group into categories (Contact Search, Enrichment, Tracking, etc.), build the MCP-style catalog following the same pattern as ticket 5. Tool description should explain LeadIQ as a B2B contact intelligence and prospecting platform.

## Acceptance Criteria
- [ ] `harnessiq/tools/leadiq/operations.py` with full catalog
- [ ] `create_leadiq_tools()` returns `tuple[RegisteredTool, ...]`
- [ ] `LEADIQ_REQUEST` in `harnessiq/shared/tools.py`
- [ ] Tests cover catalog completeness, tool schema, handler execution
- [ ] `pytest tests/test_leadiq_provider.py -v` passes
- [ ] `mypy` clean

## Dependencies
None (can run in parallel)

## Drift Guard
Only `tools/leadiq/` creation and `shared/tools.py`. Do not modify `providers/leadiq/`.
