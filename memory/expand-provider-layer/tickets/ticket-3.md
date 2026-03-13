Title: Expand the Anthropic provider with Messages, server tools, MCP, and token counting helpers
Issue URL: https://github.com/cerredz/HarnessHub/issues/11
Intent: Turn the Anthropic provider into a real client layer that can build and execute Messages API requests while covering Anthropic’s custom tool flow, server-side tools, MCP connectors, and token counting surface in a neat provider-specific module layout.
Scope:
- Reorganize the Anthropic provider package into focused modules for client calls, request builders/content blocks, and tool/server-tool helpers.
- Add real request-executing helpers for message creation, token counting, and a core adjacent endpoint if it fits cleanly.
- Add builder helpers for custom tools, tool choice, thinking/request options, server-side tools such as web search/text editor/bash/computer use where documented, and MCP server configuration.
- Preserve the existing Anthropic `build_request()` compatibility entry point.
- Do not modify the OpenAI, Grok, or Gemini provider packages in this ticket except for imports required by merged shared code.
Relevant Files:
- `src/providers/anthropic/api.py`: add Anthropic endpoint, version/beta header, and URL builders.
- `src/providers/anthropic/client.py`: add an `AnthropicClient` with real API-call helpers such as message creation, token counting, and model listing if documented cleanly.
- `src/providers/anthropic/messages.py`: add payload/content builders for messages, multimodal blocks, request options, and token-count requests.
- `src/providers/anthropic/tools.py`: add reusable builders for custom tools, tool choice, web search, text editor, bash, computer use, and MCP servers.
- `src/providers/anthropic/helpers.py`: keep compatibility wrappers and delegate to the new module layout.
- `src/providers/anthropic/__init__.py`: export the expanded Anthropic helper surface.
- `tests/test_anthropic_provider.py`: add Anthropic-specific request builder and client-call coverage.
Approach: Keep Anthropic’s provider surface idiomatic rather than forcing it into OpenAI-style request names. Use small pure builders for content blocks, tool declarations, and request options, then expose a thin `AnthropicClient` that centralizes authentication/version headers and delegates network execution through the shared transport. Preserve the current compatibility helper by mapping it onto the new message request builder.
Assumptions:
- Anthropic’s Messages API and token counting endpoint are the core client surfaces to support here.
- Anthropic server-side tool helpers should be explicit functions because their payload shapes and semantics differ from custom function tools.
- Anthropic MCP support should be modeled as request configuration rather than a separate network workflow.
Acceptance Criteria:
- [ ] The Anthropic package is reorganized into focused modules with a thin compatibility `helpers.py`.
- [ ] `AnthropicClient` can execute message creation and token counting requests through the shared transport using injected request executors in tests.
- [ ] Anthropic helper functions cover custom tools, tool choice, documented server tools, MCP server configuration, and core request options.
- [ ] Existing Anthropic `build_request()` behavior remains available and covered by tests.
- [ ] Anthropic-specific unit tests pass without live network calls.
Verification Steps:
- Run `python -m unittest tests.test_anthropic_provider`.
- Run the full test suite with `python -m unittest`.
- Perform a smoke check that injects a fake transport into `AnthropicClient` and verifies version headers, endpoint path, and tool/server-tool payload assembly.
- Manually inspect public exports from `src/providers/anthropic/__init__.py` to confirm the intended helper surface is reachable.
Dependencies: Ticket 1.
Drift Guard: This ticket must preserve Anthropic’s provider-specific semantics instead of flattening them into OpenAI-compatible abstractions. It must not introduce live computer-use automation or local MCP runtime management beyond request/configuration helpers.
