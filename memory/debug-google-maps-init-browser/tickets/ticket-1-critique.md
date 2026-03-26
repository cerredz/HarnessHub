## Self-Critique Findings

1. The first implementation exported `_GOOGLE_MAPS_BOOTSTRAP_URL` through `__all__`, which made a private implementation constant look like supported public API surface. That is unnecessary for the tests and slightly weakens module boundaries.
2. The initial CLI regression test validated lifecycle calls and JSON output but did not assert the operator-facing prompt text. Because this command is intentionally interactive, preserving those prompts is part of the real contract.

## Improvements Implemented

- Removed `_GOOGLE_MAPS_BOOTSTRAP_URL` from `__all__` so the integration only exposes its intended public API.
- Strengthened `tests/test_prospecting_cli.py` to assert that the init-browser command still prints the session path line and the Google Maps prompt text while emitting the saved-session payload.
