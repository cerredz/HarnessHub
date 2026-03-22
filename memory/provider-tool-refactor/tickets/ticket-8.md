# Ticket 8 — Build PhantomBuster tool operations in `harnessiq/tools/phantombuster/`

## Title
Build and register PhantomBuster MCP-style tool operations in `harnessiq/tools/phantombuster/`

## Intent
PR #58 feedback: PhantomBuster provider merged with only an API client. Build the tool layer.

## Scope
- Create `harnessiq/tools/phantombuster/__init__.py` and `operations.py`
- Model PhantomBuster API endpoints from `providers/phantombuster/api.py` + `client.py`
- Add `PHANTOMBUSTER_REQUEST = "phantombuster.request"` to `harnessiq/shared/tools.py`
- Extend `tests/test_phantombuster_provider.py` with tool-layer tests

## Approach
Read providers/phantombuster to enumerate endpoints, categorize (Agents/Phantoms, Outputs, Launches, etc.), build MCP-style catalog. Tool description: PhantomBuster is an automation platform for web scraping and lead generation across social networks.

## Acceptance Criteria
- [ ] Full catalog in `tools/phantombuster/operations.py`
- [ ] `create_phantombuster_tools()` working
- [ ] `PHANTOMBUSTER_REQUEST` in shared
- [ ] Tests pass, mypy clean

## Dependencies
None

## Drift Guard
Only phantombuster tool layer.
