## Self-Critique

### Finding 1

The brainstorm tool handler was updated to accept string presets (`small`, `medium`, `large`), but the tool schema still advertised `count` as integer-only. That would leave inspection metadata and validation hints out of sync with actual behavior.

### Improvement Applied

- Updated `harnessiq/tools/reasoning/injectable.py` so the `count` schema accepts either an integer or one of the supported preset strings.
- Clarified the schema description to document the preset path explicitly.

### Re-Verification

- `python -m pytest -q tests/test_reasoning_tools.py tests/test_agents_base.py::BaseAgentTests::test_run_resets_context_when_prune_progress_interval_is_reached`
  - Result: `119 passed in 0.50s`
- `python -m pytest -q`
  - Result: `1243 passed, 1 warning in 12.58s`
