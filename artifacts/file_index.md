This artifact tracks the meaningful repository layout and the current architecture of the codebase. Update it whenever a new top-level or otherwise meaningful structural folder is added.

Top-level directories:

- `artifacts/`: repository-level documentation artifacts such as this index
- `docs/`: SDK usage examples and lightweight package documentation
- `harnessiq/`: the production Python SDK package for Harnessiq
- `memory/`: planning, verification, critique, and other workflow artifacts produced during repository work
- `tests/`: unit tests for the currently merged source modules

Source layout:

- `harnessiq/agents/`: provider-agnostic agent runtime primitives plus concrete agent harnesses
- `harnessiq/cli/`: package-native command-line entrypoints and root command dispatch
- `harnessiq/cli/config/`: SDK-wide credential binding commands backed by the config store
- `harnessiq/cli/linkedin/`: LinkedIn-specific CLI commands for agent memory management and execution
- `harnessiq/config/`: repo-local credential config models and `.env` loader/store helpers
- `harnessiq/shared/`: shared types, configs, and constants; definitions that need to be reused across modules should live here in domain-specific files
- `harnessiq/tools/`: the tool runtime layer, including built-in tool handlers, reusable transformation/control tools, prompt generation, filesystem access helpers, external service integrations such as Resend, and registry/execution behavior
- `harnessiq/providers/`: provider translation helpers and provider-specific request builders
- `harnessiq/providers/anthropic/`: Anthropic request and tool-translation helpers
- `harnessiq/providers/openai/`: OpenAI request and tool-translation helpers
- `harnessiq/providers/grok/`: Grok request and tool-translation helpers
- `harnessiq/providers/gemini/`: Gemini request and tool-translation helpers

Tests:
- `tests/test_agents_base.py`: coverage for the generic agent loop, transcript handling, context resets, and structured pause behavior
- `tests/test_email_agent.py`: coverage for the abstract email-capable harness, masked Resend credentials, and Resend tool integration through the agent loop
- `tests/test_linkedin_agent.py`: coverage for the LinkedIn-specific harness, memory files, and durable state tools
- `tests/test_tools.py`: coverage for tool definitions, registry behavior, validation, execution, and built-in key ordering
- `tests/test_context_compaction_tools.py`: coverage for the context-window compaction tool family
- `tests/test_general_tools.py`: coverage for the reusable text, record, and control-flow tool family
- `tests/test_prompt_filesystem_tools.py`: coverage for system-prompt generation and non-destructive filesystem tools
- `tests/test_resend_tools.py`: coverage for the Resend operation catalog, MCP-style request tool, and Resend-specific transport/header behavior
- `tests/test_provider_base.py`: coverage for shared provider helpers and HTTP transport
- `tests/test_providers.py`: coverage for provider message normalization and request translation across all supported providers
- `tests/test_anthropic_provider.py`: coverage for Anthropic request, tool, and client helpers
- `tests/test_grok_provider.py`: coverage for Grok request, tool, and client helpers
- `tests/test_openai_provider.py`: coverage for OpenAI request, tool, and client helpers
- `tests/test_gemini_provider.py`: coverage for Gemini content, tool, and client helpers
- `tests/test_credentials_config.py`: coverage for persisted agent credential bindings and repo-local `.env` resolution
- `tests/test_config_cli.py`: coverage for CLI creation, rendering, and `.env` resolution of credential bindings

Current memory artifacts:

- `memory/refactor-types-constants/`: planning, ticket, quality, critique, and PR-body artifacts for the shared definitions refactor
- `memory/linkedin-agent-harness/`: internalization, tickets, and verification artifacts for the LinkedIn harness work
- `memory/add-context-compaction-tools/`: internalization, tickets, and verification artifacts for the context-window compaction work
- `memory/add-generalizable-tools/`: internalization, brainstorming, ticket, and verification artifacts for the general-purpose tool expansion
- `memory/add-system-prompt-terminal-tools/`: internalization, clarification, ticket, and verification artifacts for prompt and filesystem tool expansion
- `memory/email-agent-resend-mcp/`: internalization, ticket, quality, and critique artifacts for the Resend-backed email agent base work
- `memory/shared-definition-consolidation/`: internalization and ticket plan artifacts for the shared-definition cleanup
