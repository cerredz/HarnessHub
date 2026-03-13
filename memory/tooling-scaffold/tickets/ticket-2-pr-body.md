Add the first provider translation layer on top of the canonical tool registry.

## Scope

- add a shared provider formatting module
- add provider-specific helper packages for Anthropic, OpenAI, Grok, and Gemini
- translate canonical `ToolDefinition` objects into provider-ready request payload fragments
- add unit coverage for provider message validation and translation output

## Quality Pipeline Results

- Static analysis: Python syntax validated across `src/` and `tests/` with `py_compile`
- Type checking: no repository checker configured; all new provider code is annotated
- Unit tests: `python -m unittest tests.test_tools tests.test_providers -v`
- Integration/contract tests: no dedicated suite configured for this slice
- Smoke check: manual payload inspection passed for all four providers

## Post-Critique Changes

- provider request builders now reject inline `system` messages when a top-level `system_prompt` is supplied
- this removes duplicated system-instruction ambiguity before the agent runtime depends on the provider layer
