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
- `harnessiq/cli/linkedin/`: LinkedIn-specific CLI commands for agent memory management and execution
- `harnessiq/shared/`: shared types, configs, and constants; definitions that need to be reused across modules should live here in domain-specific files
- `harnessiq/tools/`: the tool runtime layer, including built-in tool handlers, reusable transformation/control tools, prompt generation, filesystem access helpers, external service integrations such as Resend, and registry/execution behavior
- `harnessiq/providers/`: provider translation helpers and provider-specific request builders
- `harnessiq/config/`: credential loader and base credential configuration types; `CredentialLoader` resolves named environment variables from a repo-local `.env` file
- `harnessiq/providers/anthropic/`: Anthropic request and tool-translation helpers
- `harnessiq/providers/openai/`: OpenAI request and tool-translation helpers
- `harnessiq/providers/grok/`: Grok request and tool-translation helpers
- `harnessiq/providers/gemini/`: Gemini request and tool-translation helpers
- `harnessiq/providers/snovio/`: Snov.io email-finding and outreach API client
- `harnessiq/providers/leadiq/`: LeadIQ lead-intelligence API client (GraphQL)
- `harnessiq/providers/salesforge/`: Salesforge AI sales-engagement API client
- `harnessiq/providers/phantombuster/`: PhantomBuster web-automation API client
- `harnessiq/providers/zoominfo/`: ZoomInfo B2B-intelligence API client (JWT auth)
- `harnessiq/providers/peopledatalabs/`: People Data Labs people and company data-enrichment API client
- `harnessiq/providers/proxycurl/`: Proxycurl LinkedIn data API client
- `harnessiq/providers/coresignal/`: Coresignal professional network data API client

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
- `tests/test_config_loader.py`: coverage for the CredentialLoader and HTTP transport hostname inference
- `tests/test_snovio_provider.py`: coverage for the Snov.io provider client and request builders
- `tests/test_leadiq_provider.py`: coverage for the LeadIQ provider client and GraphQL request builders
- `tests/test_salesforge_provider.py`: coverage for the Salesforge provider client and request builders
- `tests/test_phantombuster_provider.py`: coverage for the PhantomBuster provider client and request builders
- `tests/test_zoominfo_provider.py`: coverage for the ZoomInfo provider client and request builders
- `tests/test_peopledatalabs_provider.py`: coverage for the People Data Labs provider client and request builders
- `tests/test_proxycurl_provider.py`: coverage for the Proxycurl provider client and request builders
- `tests/test_coresignal_provider.py`: coverage for the Coresignal provider client and request builders

Current memory artifacts:

- `memory/refactor-types-constants/`: planning, ticket, quality, critique, and PR-body artifacts for the shared definitions refactor
- `memory/linkedin-agent-harness/`: internalization, tickets, and verification artifacts for the LinkedIn harness work
- `memory/add-context-compaction-tools/`: internalization, tickets, and verification artifacts for the context-window compaction work
- `memory/add-generalizable-tools/`: internalization, brainstorming, ticket, and verification artifacts for the general-purpose tool expansion
- `memory/add-system-prompt-terminal-tools/`: internalization, clarification, ticket, and verification artifacts for prompt and filesystem tool expansion
- `memory/email-agent-resend-mcp/`: internalization, ticket, quality, and critique artifacts for the Resend-backed email agent base work
- `memory/shared-definition-consolidation/`: internalization and ticket plan artifacts for the shared-definition cleanup
- `memory/add-data-providers/`: internalization, ticket, quality, and critique artifacts for the data-service provider expansion (Snov.io, LeadIQ, Salesforge, PhantomBuster, ZoomInfo, People Data Labs, Proxycurl, Coresignal)
