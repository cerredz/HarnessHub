## Issue 389 Self-Critique

### Finding
- `BaseAgent` already captured the last dynamic tool-selection result internally, but it exposed no stable read path. That would have pushed later debug logging, harness diagnostics, and follow-on selector work toward private-state access.

### Improvement Applied
- Added a read-only `last_tool_selection_result` property on `BaseAgent`.
- Extended `tests/test_agents_base.py` to assert that the property stays `None` on the static path and reflects the selected tool subset on the enabled dynamic path.

### Regression Check
- Re-ran:
  - `python -m compileall harnessiq`
  - `python scripts/sync_repo_docs.py --check`
  - `pytest`
- Result: all commands passed after the refinement.
