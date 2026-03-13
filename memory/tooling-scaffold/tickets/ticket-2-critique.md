# Ticket 2 Self-Critique

## Findings

1. The first provider implementation allowed inline `system` messages in `messages` even though `system_prompt` is already a separate request input.
- Risk: a future agent could encode system instructions twice, producing ambiguous provider payloads.
- Improvement made: `normalize_messages()` now supports `allow_system=False`, and provider request builders reject inline system messages when a top-level system prompt is expected.

## Re-Verification

- Re-ran the Python syntax validation command across `src/` and `tests/`
- Re-ran `python -m unittest tests.test_tools tests.test_providers -v`
- Re-ran a manual OpenAI payload smoke check
- Result: all checks passed after the critique change
