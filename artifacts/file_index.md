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
- `harnessiq/config/`: repo-local credential config models and `.env` loader/store helpers
- `harnessiq/shared/`: shared types, configs, and constants; definitions that need to be reused across modules should live here in domain-specific files
- `harnessiq/tools/`: the tool runtime layer, including built-in tool handlers, reusable transformation/control tools, prompt generation, filesystem access helpers, external service integrations such as Resend, and registry/execution behavior; also contains MCP-style tool factories for all registered data and service providers
- `harnessiq/tools/creatify/`: MCP-style tool factory for Creatify AI video creation
- `harnessiq/tools/arcads/`: MCP-style tool factory for Arcads AI advertising video creation
- `harnessiq/tools/instantly/`: MCP-style tool factory for Instantly cold email platform
- `harnessiq/tools/outreach/`: MCP-style tool factory for Outreach sales engagement platform
- `harnessiq/tools/lemlist/`: MCP-style tool factory for Lemlist B2B outreach platform
- `harnessiq/tools/exa/`: MCP-style tool factory for Exa neural search engine
- `harnessiq/tools/snovio/`: MCP-style tool factory for Snov.io email intelligence (OAuth2 auth handled transparently)
- `harnessiq/tools/leadiq/`: MCP-style tool factory for LeadIQ contact intelligence (GraphQL API)
- `harnessiq/tools/salesforge/`: MCP-style tool factory for Salesforge cold email automation
- `harnessiq/tools/phantombuster/`: MCP-style tool factory for PhantomBuster browser automation
- `harnessiq/tools/zoominfo/`: MCP-style tool factory for ZoomInfo B2B intelligence (JWT auth handled transparently)
- `harnessiq/tools/peopledatalabs/`: MCP-style tool factory for People Data Labs data enrichment
- `harnessiq/tools/proxycurl/`: MCP-style tool factory for Proxycurl (deprecated — shut down Jan 2025)
- `harnessiq/tools/coresignal/`: MCP-style tool factory for Coresignal professional data
- `harnessiq/tools/reasoning/`: 50 reasoning lens tools for agent cognitive scaffolding — includes step-by-step, tree-of-thoughts, first-principles, red-teaming, pre-mortem, and 45 others across 8 cognitive categories (core logical, analytical, perspective, creative, systems, temporal, evaluative, scientific)
- `harnessiq/providers/`: provider translation helpers and provider-specific request builders
- `harnessiq/config/`: credential loader and base credential configuration types; `CredentialLoader` resolves named environment variables from a repo-local `.env` file
- `harnessiq/config/`: credential-config layer; `.env`-backed `CredentialLoader` and `ProviderCredentialConfig` base type for all provider credential models
- `harnessiq/providers/`: provider-specific request builders, HTTP clients, and operation catalogs; covers both AI LLM providers and external-service API providers
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
- `harnessiq/providers/creatify/`: Creatify AI video creation API — credentials, client, and full operation catalog
- `harnessiq/providers/arcads/`: Arcads AI video ad API — credentials, client, and operation catalog
- `harnessiq/providers/instantly/`: Instantly.ai cold email API v2 — credentials, client, and full operation catalog
- `harnessiq/providers/outreach/`: Outreach.io sales engagement API — credentials, OAuth client, and core operation catalog
- `harnessiq/providers/lemlist/`: Lemlist outreach API — credentials, client, and full operation catalog
- `harnessiq/providers/exa/`: Exa neural search API — credentials, client, and full operation catalog

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
- `tests/test_snovio_provider.py`: coverage for Snov.io request builders, client, operation catalog, and tool factory (OAuth2 token exchange)
- `tests/test_leadiq_provider.py`: coverage for LeadIQ operation catalog and tool factory (GraphQL dispatch)
- `tests/test_salesforge_provider.py`: coverage for Salesforge operation catalog and tool factory
- `tests/test_phantombuster_provider.py`: coverage for PhantomBuster operation catalog and tool factory
- `tests/test_zoominfo_provider.py`: coverage for ZoomInfo operation catalog and tool factory (JWT auth)
- `tests/test_peopledatalabs_provider.py`: coverage for People Data Labs operation catalog and tool factory
- `tests/test_proxycurl_provider.py`: coverage for Proxycurl operation catalog and tool factory (deprecated provider)
- `tests/test_coresignal_provider.py`: coverage for Coresignal operation catalog and tool factory
- `tests/test_config_loader.py`: coverage for CredentialLoader `.env` parsing, error cases, and HTTP transport hostname mapping for all six new providers
- `tests/test_creatify_provider.py`: coverage for Creatify credentials, client, operation catalog, and tool factory
- `tests/test_arcads_provider.py`: coverage for Arcads credentials (Basic Auth), client, operation catalog, and tool factory
- `tests/test_instantly_provider.py`: coverage for Instantly credentials, client, V2 operation catalog, and tool factory
- `tests/test_outreach_provider.py`: coverage for Outreach credentials (OAuth Bearer), client, core operation catalog, and tool factory
- `tests/test_lemlist_provider.py`: coverage for Lemlist credentials (Basic Auth), client, operation catalog, and tool factory
- `tests/test_exa_provider.py`: coverage for Exa credentials, client, search operation catalog, and tool factory
- `tests/test_credentials_config.py`: coverage for persisted agent credential bindings and repo-local `.env` resolution
- `tests/test_reasoning_tools.py`: coverage for all 50 reasoning lens tool handlers, registry execution, argument validation, and prompt output shape

Current memory artifacts:

- `memory/refactor-types-constants/`: planning, ticket, quality, critique, and PR-body artifacts for the shared definitions refactor
- `memory/linkedin-agent-harness/`: internalization, tickets, and verification artifacts for the LinkedIn harness work
- `memory/add-context-compaction-tools/`: internalization, tickets, and verification artifacts for the context-window compaction work
- `memory/add-generalizable-tools/`: internalization, brainstorming, ticket, and verification artifacts for the general-purpose tool expansion
- `memory/add-system-prompt-terminal-tools/`: internalization, clarification, ticket, and verification artifacts for prompt and filesystem tool expansion
- `memory/email-agent-resend-mcp/`: internalization, ticket, quality, and critique artifacts for the Resend-backed email agent base work
- `memory/shared-definition-consolidation/`: internalization and ticket plan artifacts for the shared-definition cleanup
- `memory/add-data-providers/`: internalization, ticket, quality, and critique artifacts for the data-service provider expansion (Snov.io, LeadIQ, Salesforge, PhantomBuster, ZoomInfo, People Data Labs, Proxycurl, Coresignal)
- `memory/add-service-providers/`: internalization, clarifications, and ticket artifacts for adding Creatify, Arcads, Instantly, Outreach, Lemlist, and Exa providers plus the config layer
- `memory/add-reasoning-tools/`: internalization, tickets, quality, and critique artifacts for the 50 reasoning lens tool expansion
