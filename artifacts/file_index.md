This artifact tracks the meaningful directory layout of the repository so the current architecture is easy to scan.

Top-level directories:

- `artifacts/`: repository-level documentation artifacts such as this index
- `memory/`: implementation planning, quality results, critique notes, and PR-body artifacts created during repository work
- `src/`: the Python source package for HarnessHub primitives
- `tests/`: unit tests for the currently merged source modules

Source layout:

- `src/tools/`: canonical tool schemas, public tool keys, built-in example tools, and deterministic registry/execution helpers
- `src/providers/`: shared provider-formatting utilities plus provider-specific payload builders
- `src/providers/anthropic/`: Anthropic request and tool-translation helpers
- `src/providers/openai/`: OpenAI request and tool-translation helpers
- `src/providers/grok/`: Grok request and tool-translation helpers
- `src/providers/gemini/`: Gemini request and tool-translation helpers

Tests:

- `tests/test_tools.py`: coverage for tool definitions, registry behavior, validation, and execution
- `tests/test_providers.py`: coverage for provider message normalization and request translation across all supported providers

Tracked memory artifacts:

- `memory/tooling-scaffold/tickets/`: ticket-level quality reports, critique notes, and PR-body artifacts for the merged scaffolding work
