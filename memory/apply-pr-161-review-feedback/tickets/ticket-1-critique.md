Self-critique findings:

- The first implementation pass validated the happy path for the new `create_leads_tools(...)` seam but did not directly test the failure boundary now owned by that module.
- That left the unsupported-platform error path indirectly covered only through prior agent behavior rather than through the new tool-factory entrypoint itself.

Post-critique improvement applied:

- Added `test_create_leads_tools_rejects_unknown_platform_without_override` to `tests/test_leads_tools.py`.
- Re-ran the full targeted leads suite after the added coverage:
  - `python -m pytest tests/test_leads_shared.py tests/test_leads_tools.py tests/test_leads_agent.py tests/test_leads_cli.py`
  - Result: `30 passed`
