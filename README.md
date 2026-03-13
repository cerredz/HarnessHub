# HarnessHub

HarnessHub is a Python repository for building handcrafted LLM harnesses.

The current scaffold focuses on the three primitives that the rest of the repository will build on:

- canonical tools that can be referenced by stable string keys
- provider-specific request translators for Anthropic, OpenAI, Grok, and Gemini
- an abstract runtime-capable base agent that binds model config, tool access, and provider formatting

## Current Layout

- `src/tools/`: canonical tool schemas, built-in tool definitions, and deterministic registry helpers
- `src/providers/`: small pure functions that translate canonical requests into provider-ready payloads
- `src/agents/`: abstract runtime-facing agent primitives
- `tests/`: unit coverage for the tool registry, provider translators, and base agent behavior

## Verification

Run the current test suite with:

```bash
python -m unittest discover -s tests -v
```
