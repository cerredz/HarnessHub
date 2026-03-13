Title: Expand the Grok provider with xAI chat, search, collections, and MCP helpers
Issue URL: https://github.com/cerredz/HarnessHub/issues/10
Intent: Build a real xAI/Grok provider client on top of the shared transport so the repository can model xAI’s OpenAI-compatible chat flows plus xAI-specific built-in tool capabilities such as web/X search, code execution, collections search, and remote MCP.
Scope:
- Reorganize the Grok provider package into focused modules for client calls, request builders, and tool builders.
- Add real request-executing helpers for xAI chat completions, model listing, and a broader adjacent endpoint where it fits cleanly.
- Add builder helpers for custom tools, tool choice, structured outputs, search parameterization, citations, collections/file search, code execution, and MCP.
- Preserve the existing Grok `build_request()` compatibility entry point.
- Do not modify Anthropic or Gemini provider packages in this ticket.
Relevant Files:
- `src/providers/grok/api.py`: add xAI endpoint, header, and URL builders.
- `src/providers/grok/client.py`: add a `GrokClient` with real API-call helpers such as chat completions, model listing, and embeddings or responses if cleanly supported.
- `src/providers/grok/requests.py`: add payload builders for chat-completions-style requests, structured outputs, search controls, and request options.
- `src/providers/grok/tools.py`: add reusable builders for custom function tools, web search, X search, collections search/file search compatibility, code execution, and remote MCP.
- `src/providers/grok/helpers.py`: keep compatibility wrappers and delegate to the new module layout.
- `src/providers/grok/__init__.py`: export the expanded Grok helper surface.
- `tests/test_grok_provider.py`: add Grok-specific request builder and client-call coverage.
Approach: Reuse the shared request transport and the OpenAI-style message/tool helpers where the xAI API is intentionally compatible, but add xAI-specific tool builders and request options in separate focused modules so compatibility logic and xAI-only capabilities remain easy to follow. Keep the client API symmetric with OpenAI where semantics overlap, then diverge into xAI-specific helpers for search/collections/MCP.
Assumptions:
- xAI’s chat-completions surface is the correct compatibility anchor for the existing Grok provider.
- xAI-specific built-in tools should be modeled as separate helpers rather than hidden behind generic OpenAI names when semantics differ.
- The collections search capability can be represented as a request/tool helper without implementing full file-management workflows in this ticket.
Acceptance Criteria:
- [ ] The Grok package is reorganized into focused modules with a thin compatibility `helpers.py`.
- [ ] `GrokClient` can execute core xAI requests through the shared transport using injected request executors in tests.
- [ ] Grok helper functions cover xAI-specific built-in tools and request options including search parameters, citations, collections/file search compatibility, and remote MCP.
- [ ] Existing Grok `build_request()` behavior remains available and covered by tests.
- [ ] Grok-specific unit tests pass without live network calls.
Verification Steps:
- Run `python -m unittest tests.test_grok_provider`.
- Run the full test suite with `python -m unittest`.
- Perform a smoke check that injects a fake transport into `GrokClient` and verifies auth headers, endpoint path, and tool payload assembly.
- Manually inspect public exports from `src/providers/grok/__init__.py` to confirm symmetric/shared names and xAI-specific names are both exposed.
Dependencies: Ticket 1.
Drift Guard: This ticket must stay within the xAI/Grok provider package and its tests. It must not pull Anthropic or Gemini semantics into shared abstractions, and it must not expand into collection/file-management endpoints beyond what is needed to support the modeled chat/tool use cases cleanly.
