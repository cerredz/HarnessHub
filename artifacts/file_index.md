This artifact tracks the meaningful repository layout and the current architecture of the codebase. Update it whenever a new top-level or otherwise meaningful structural folder is added.

Top-level directories:

- `artifacts/`: repository-level documentation artifacts such as this index
- `memory/`: planning, verification, critique, and other workflow artifacts produced during repository work
- `src/`: the production Python package for HarnessHub
- `tests/`: unit tests for the currently merged source modules

Source layout:

- `src/agents/`: provider-agnostic agent runtime primitives plus concrete agent harnesses
- `src/shared/`: shared types, configs, and constants; definitions that need to be reused across modules should live here in domain-specific files
- `src/tools/`: the tool runtime layer, including built-in tool handlers, reusable transformation/control tools, prompt generation, filesystem access helpers, and registry/execution behavior
- `src/providers/`: provider translation helpers and provider-specific request builders
- `src/providers/anthropic/`: Anthropic request and tool-translation helpers
- `src/providers/openai/`: OpenAI request and tool-translation helpers
- `src/providers/grok/`: Grok request and tool-translation helpers
- `src/providers/gemini/`: Gemini request and tool-translation helpers

Tests:

- `tests/test_agents_base.py`: coverage for the generic agent loop, transcript handling, context resets, and structured pause behavior
- `tests/test_linkedin_agent.py`: coverage for the LinkedIn-specific harness, memory files, and durable state tools
- `tests/test_tools.py`: coverage for tool definitions, registry behavior, validation, and built-in key ordering
- `tests/test_general_tools.py`: coverage for the reusable text, record, and control-flow tool family
- `tests/test_prompt_filesystem_tools.py`: coverage for system-prompt generation and non-destructive filesystem tools
- `tests/test_providers.py`: coverage for provider message normalization and request translation across all supported providers

Current memory artifacts:

- `memory/refactor-types-constants/`: planning, ticket, quality, critique, and PR-body artifacts for the shared definitions refactor
- `memory/add-generalizable-tools/`: internalization, brainstorming, ticket, and verification artifacts for the general-purpose tool expansion
- `memory/add-system-prompt-terminal-tools/`: internalization, clarification, ticket, and verification artifacts for prompt and filesystem tool expansion
