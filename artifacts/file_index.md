This artifact tracks the meaningful repository layout and the current architecture of the codebase. Update it whenever a new top-level or otherwise meaningful structural folder is added.

Top-level directories:

- `artifacts/`: repository-level documentation artifacts such as this index
- `memory/`: planning, verification, critique, and other workflow artifacts produced during repository work
- `src/`: the production Python package for HarnessHub
- `tests/`: unit tests for the currently merged source modules

Source layout:

- `src/agents/`: provider-agnostic agent runtime primitives plus concrete agent harnesses
- `src/shared/`: shared types, configs, and constants; definitions that need to be reused across modules should live here in domain-specific files
- `src/tools/`: the tool runtime layer, including built-in tool handlers and registry/execution behavior
- `src/providers/`: provider translation helpers and provider-specific request builders
- `src/providers/anthropic/`: Anthropic request and tool-translation helpers
- `src/providers/openai/`: OpenAI request and tool-translation helpers
- `src/providers/grok/`: Grok request and tool-translation helpers
- `src/providers/gemini/`: Gemini request and tool-translation helpers

Tests:

- `tests/test_agents_base.py`: coverage for the generic agent loop, transcript handling, and context resets
- `tests/test_linkedin_agent.py`: coverage for the LinkedIn-specific harness, memory files, and durable state tools
- `tests/test_tools.py`: coverage for tool definitions, registry behavior, validation, and execution
- `tests/test_providers.py`: coverage for provider message normalization and request translation across all supported providers

Current memory artifacts:

- `memory/refactor-types-constants/`: planning, ticket, quality, critique, and PR-body artifacts for the shared definitions refactor
