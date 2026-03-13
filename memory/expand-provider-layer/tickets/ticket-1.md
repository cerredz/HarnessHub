Title: Add shared HTTP transport and expand the OpenAI provider client surface
Issue URL: https://github.com/cerredz/HarnessHub/issues/9
Intent: Establish the reusable request-execution foundation for provider clients, then turn the OpenAI provider into a real, organized client layer with small builders for core API requests, built-in tools, MCP, and structured outputs.
Scope:
- Add shared provider HTTP/request helpers that provider-specific clients can reuse without duplicating JSON request logic.
- Reorganize the OpenAI provider package into focused modules for transport-facing client calls, request builders, and tool builders.
- Preserve the existing `build_request()` entry point while adding richer OpenAI-specific helpers and real request execution methods.
- Split provider tests so OpenAI/shared coverage is isolated from the later provider tickets.
- Do not implement xAI, Anthropic, or Gemini-specific client surfaces in this ticket.
Relevant Files:
- `src/providers/base.py`: extend shared provider primitives with reusable dict/None-filter helpers as needed while preserving current normalization behavior.
- `src/providers/http.py`: add shared JSON HTTP request execution and transport error handling.
- `src/providers/__init__.py`: export any new shared provider errors/types needed by callers.
- `src/providers/openai/api.py`: add OpenAI endpoint, header, and URL builders.
- `src/providers/openai/client.py`: add an `OpenAIClient` with real API-call helpers such as responses, chat completions, embeddings, and model listing.
- `src/providers/openai/requests.py`: add small payload builders for responses, chat completions, embeddings, structured output, and response input items.
- `src/providers/openai/tools.py`: add reusable builders for custom function tools, tool choice, file search, web search, code interpreter, image generation, computer use, and MCP tools.
- `src/providers/openai/helpers.py`: keep compatibility wrappers and delegate to the new module layout.
- `src/providers/openai/__init__.py`: export the expanded public OpenAI helper surface.
- `tests/test_provider_base.py`: add shared transport/base helper coverage.
- `tests/test_openai_provider.py`: add OpenAI-specific request builder and client-call coverage.
- `tests/test_providers.py`: remove or replace the previous monolithic provider test coverage now that tests are provider-scoped.
Approach: Introduce a shared stdlib-based JSON transport layer that accepts method/url/headers/body and returns parsed JSON while surfacing clear provider request errors. Build the OpenAI provider around small pure functions that assemble payload fragments and a thin client object that supplies authentication/base URL/timeout once and delegates actual calls through the shared transport. Keep the existing chat-style helper as a compatibility shim implemented on top of the new request builders rather than preserving a parallel codepath.
Assumptions:
- Stdlib HTTP transport is preferred over adding SDK dependencies to a repository that currently has no packaging/dependency configuration.
- The OpenAI provider should cover the modern Responses API as well as the currently used chat-completions-style payload helper.
- Model listing and embeddings are in scope as “broader services” for OpenAI because they are core adjacent endpoints and keep the client layer meaningfully useful.
Acceptance Criteria:
- [ ] `src/providers/http.py` provides a reusable JSON request executor with deterministic error handling and unit coverage.
- [ ] The OpenAI package is split into focused modules instead of a single all-in-one helper module.
- [ ] `OpenAIClient` can build and execute at least responses, chat completions, embeddings, and model list requests through an injectable request executor.
- [ ] OpenAI helper functions cover custom function tools, tool choice, structured outputs, and documented built-in tool payloads including MCP.
- [ ] The existing `build_request()` behavior remains available and covered by tests.
- [ ] Shared/OpenAI tests pass without depending on live network calls.
Verification Steps:
- Run shared/OpenAI unit tests with `python -m unittest tests.test_provider_base tests.test_openai_provider`.
- Run the full test suite with `python -m unittest`.
- Perform a smoke check in a Python one-liner or small snippet that instantiates `OpenAIClient`, injects a fake transport, and verifies the request path, headers, and payload.
- Manually inspect public exports from `src/providers/openai/__init__.py` to confirm the intended helper surface is reachable.
Dependencies: None.
Drift Guard: This ticket must not introduce provider-specific behavior for Anthropic, Grok/xAI, or Gemini, and it must not become a general-purpose SDK clone. The goal is a focused OpenAI client/helper surface built on shared request plumbing, not exhaustive coverage of every OpenAI endpoint.
