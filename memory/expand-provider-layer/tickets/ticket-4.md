Title: Expand the Gemini provider with content, tool, grounding, caching, and file-search helpers
Issue URL: https://github.com/cerredz/HarnessHub/issues/12
Intent: Build a real Gemini client layer that covers content generation requests plus Gemini-specific built-in tools and adjacent services such as grounding, code execution, URL context, file search, and context caching in a clean provider package layout.
Scope:
- Reorganize the Gemini provider package into focused modules for client calls, content/config builders, and built-in tool helpers.
- Add real request-executing helpers for generate-content, count-tokens, model listing, and context caching or other cleanly bounded Gemini-adjacent services.
- Add builder helpers for custom function tools, function-calling config, structured outputs, Google Search grounding, Google Maps grounding, URL context, code execution, file search, and cache references where supported by the HTTP API.
- Preserve the existing Gemini `build_request()` compatibility entry point.
- Do not add speculative local MCP runtime integration unless it is cleanly expressible and testable in this repository.
Relevant Files:
- `src/providers/gemini/api.py`: add Gemini endpoint, API-key transport, and URL builders.
- `src/providers/gemini/client.py`: add a `GeminiClient` with real API-call helpers such as generate content, count tokens, list models, and cache creation/listing when supported.
- `src/providers/gemini/content.py`: add content-part, generation-config, structured-output, and cached-content builders.
- `src/providers/gemini/tools.py`: add reusable builders for custom function tools, function-calling config, Google Search, Google Maps, URL context, code execution, and file search tools.
- `src/providers/gemini/helpers.py`: keep compatibility wrappers and delegate to the new module layout.
- `src/providers/gemini/__init__.py`: export the expanded Gemini helper surface.
- `tests/test_gemini_provider.py`: add Gemini-specific request builder and client-call coverage.
Approach: Keep Gemini’s content/tool configuration explicit and provider-native rather than forcing OpenAI-like shapes onto it. Use small builders for content parts, generation config, and built-in tools, then wrap the HTTP interactions in a thin `GeminiClient` that centralizes API key handling and endpoint construction. Preserve the current compatibility helper by implementing it atop the new content/generate-content builders.
Assumptions:
- Gemini’s `generateContent` and `countTokens` APIs are the correct core endpoints to support in this provider layer.
- Context caching and file search are sufficiently bounded to include as broader services without turning this ticket into a full file-management SDK.
- Gemini MCP should be omitted unless an official, request-level HTTP representation is clear and testable in the current repository.
Acceptance Criteria:
- [ ] The Gemini package is reorganized into focused modules with a thin compatibility `helpers.py`.
- [ ] `GeminiClient` can execute generate-content and count-tokens requests through the shared transport using injected request executors in tests.
- [ ] Gemini helper functions cover structured outputs, function-calling config, and documented built-in tools including grounding, code execution, URL context, and file search.
- [ ] Existing Gemini `build_request()` behavior remains available and covered by tests.
- [ ] Gemini-specific unit tests pass without live network calls.
Verification Steps:
- Run `python -m unittest tests.test_gemini_provider`.
- Run the full test suite with `python -m unittest`.
- Perform a smoke check that injects a fake transport into `GeminiClient` and verifies query-parameter authentication, endpoint path, and tool/config payload assembly.
- Manually inspect public exports from `src/providers/gemini/__init__.py` to confirm the intended helper surface is reachable.
Dependencies: Ticket 1.
Drift Guard: This ticket must stay within the Gemini provider package and its tests. It must not invent unsupported REST features merely for symmetry, and it must avoid turning Gemini file-search or caching management into a sprawling subsystem beyond the request helpers needed for a useful provider layer.
