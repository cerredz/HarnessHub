### 1a: Structural Survey

Repository shape:

- `src/` holds a small Python package with two concerns:
- `src/tools/` defines canonical tool metadata (`ToolDefinition`), runtime bindings (`RegisteredTool`), built-in example tools, and a deterministic `ToolRegistry`.
- `src/providers/` translates provider-agnostic chat/tool primitives into provider-specific request payloads.
- `tests/` contains `unittest` coverage for the registry and provider payload translation.
- `artifacts/file_index.md` is the only maintained architecture artifact outside `memory/`.
- `memory/` stores prior planning and verification artifacts from earlier repository work.

Technology and execution model:

- Plain Python package layout with no visible packaging, lint, or type-check configuration at the repository root.
- Tests use the standard-library `unittest` runner rather than `pytest`.
- The provider layer is deliberately functional and dictionary-oriented. There are no HTTP clients, SDK wrappers, dataclasses, or serialization models in the current implementation.

Current provider architecture:

- `src/providers/base.py` contains shared primitives:
- `ProviderName`, `ProviderMessage`, and `RequestPayload` type aliases.
- `ProviderFormatError` for invalid canonical input.
- `normalize_messages()` for validating role/content pairs.
- Shared tool translators: `build_openai_style_tool()`, `build_anthropic_tool()`, `build_gemini_tool_declaration()`.
- Shared message translators: `build_openai_style_messages()` and `build_gemini_contents()`.
- Each provider package currently exports only two helpers:
- `format_tool_definition()`
- `build_request()`

Provider-specific behavior today:

- `anthropic.helpers.build_request()` emits `model`, `system`, `messages`, and `tools`.
- `openai.helpers.build_request()` emits `model`, `messages`, and `tools`, representing the system prompt as a leading chat message and forcing `strict=False` on function tools.
- `grok.helpers.build_request()` mirrors the OpenAI-style payload but omits the `strict` flag.
- `gemini.helpers.build_request()` emits `model`, `contents`, optional `system_instruction`, and optional `tools` under `functionDeclarations`.

Tooling conventions:

- Canonical tool schemas are JSON-Schema-like dictionaries stored in `ToolDefinition.input_schema`.
- Tool registry validation currently checks only required keys and `additionalProperties`.
- Provider helpers treat tools as passive metadata translation only; no provider-specific tool choice, tool result encoding, or built-in tool configuration exists.

Test strategy:

- `tests/test_tools.py` covers deterministic key order, metadata projection, runtime validation, and execution of built-in tools.
- `tests/test_providers.py` covers stable provider enumeration, message validation, and one basic request-shape assertion per provider.
- There are no integration tests against external provider SDKs or HTTP APIs.

Observed conventions and gaps:

- The codebase favors small, pure helper functions and plain dictionaries over classes.
- Public exports are curated in each package `__init__.py`.
- Error handling is explicit but minimal and localized to invalid canonical input.
- The provider layer is internally consistent, but it is materially incomplete relative to current provider feature sets:
- no structured-output helpers
- no tool-choice helpers
- no built-in/server tool helpers
- no MCP helpers
- no response/input content-part helpers beyond basic text messages
- no documentation artifact describing provider capability coverage
- Repository-level developer tooling is sparse: no visible formatter, linter, or static type checker config.

### 1b: Task Cross-Reference

User request mapping:

- "expand our provider layer" maps directly to `src/providers/base.py` and each provider package under `src/providers/{anthropic,openai,grok,gemini}/`.
- "insert more helper/utility function for each one of the providers" implies net-new public helper APIs in each provider package and corresponding exports in each package `__init__.py`.
- "use web search for each one of the providers" requires current official documentation research before deciding helper scope. This affects OpenAI, Anthropic, xAI/Grok, and Gemini/Google only.
- "understand the full capability suite of each one of the providers" maps to documenting and selecting provider features that can reasonably be represented as deterministic payload builders in this repository.
- "encapsulate all use cases of each providers (api calls, tools, mcp, etc)" expands scope beyond the current `build_request()` helpers:
- request-envelope helpers
- tool definition and tool choice helpers
- built-in/server tool helpers where supported
- MCP configuration helpers where supported
- structured-output / response-format helpers where supported
- provider-specific content blocks or request options needed to express those capabilities
- "just more things in the doc and actually interacting with them" suggests both implementation and repository documentation updates. The most natural repository location is a new artifact in `artifacts/` because current provider documentation is otherwise absent.

Concrete files likely affected:

- `src/providers/base.py`: shared validation and reusable low-level builders that prevent provider modules from duplicating schema assembly logic.
- `src/providers/openai/helpers.py`: new OpenAI request, tool, MCP, and response-format helpers informed by current OpenAI docs.
- `src/providers/openai/__init__.py`: export the expanded OpenAI helper surface.
- `src/providers/anthropic/helpers.py`: new Anthropic message/tool/server-tool/MCP/count-token helper surface.
- `src/providers/anthropic/__init__.py`: export the expanded Anthropic helper surface.
- `src/providers/grok/helpers.py`: new xAI/Grok chat-completions helpers for tool choice, response format, search/citation toggles, and remote MCP based on current docs.
- `src/providers/grok/__init__.py`: export the expanded Grok helper surface.
- `src/providers/gemini/helpers.py`: new Gemini content, generation-config, tool, and grounding/code-execution helper surface.
- `src/providers/gemini/__init__.py`: export the expanded Gemini helper surface.
- `tests/test_providers.py`: broaden coverage to assert the new provider helpers encode documented request shapes correctly.
- `artifacts/`: add a provider-capability reference documenting what is covered and which features are intentionally not represented.

Behavior that must be preserved:

- Existing `build_request()` entry points must remain usable for the current tests and likely downstream callers.
- Existing message normalization semantics in `normalize_messages()` should remain stable unless a provider-specific extension is implemented as a separate helper.
- Existing tool translation behavior for current tests must still pass.

Blast radius:

- Mostly isolated to provider modules and their tests.
- Minimal interaction with the tool registry, except that richer provider helpers may consume `ToolDefinition` more extensively.
- No existing runtime/network layer exists, so any "API call" encapsulation must stay within deterministic payload-building unless a new client abstraction is deliberately introduced.

External research used for mapping:

- OpenAI official docs indicate a modern Responses/tooling surface including custom function tools, built-in tools such as file search, web search, code interpreter, image generation, computer use, and remote MCP servers.
- Anthropic official docs indicate Messages API helpers for custom tools, tool choice, server tools (for example web search and text editor/computer-use-related tools), token counting, and MCP connectors/servers.
- xAI official docs indicate chat-completions helpers for function tools, structured outputs, search parameterization, citations, and remote MCP tools.
- Google Gemini official docs indicate helpers for function calling, code execution, grounding with Google Search, URL context, and generation configuration. I did not find an official Gemini API MCP feature in the provider docs surveyed.

### 1c: Assumption & Risk Inventory

Assumptions:

- The requested scope is to expand deterministic provider payload builders, not to introduce live authenticated HTTP clients or SDK dependencies.
- "all use cases" means "cover the major documented request-building surfaces of each provider that fit this repository's current abstraction style," not literal parity with every endpoint in each provider platform.
- Official provider documentation is the source of truth for helper design, even when providers expose multiple overlapping APIs.
- It is acceptable to add repository documentation under `artifacts/` to explain the new helper surfaces.

Ambiguities and risks:

- The phrase "api calls" could mean actual network-invoking client helpers rather than payload-shaping helpers. That would materially change the architecture, dependencies, and testing strategy.
- The phrase "actually interacting with them" could mean encoding request payloads for built-in tools/MCP, or it could mean executing real provider calls. The repository currently has no secrets management, HTTP client layer, or integration test scaffolding for live calls.
- "full capability suite" is larger than the current repo abstraction can safely absorb in one pass if interpreted literally. Each provider has adjacent features like streaming, batch APIs, file uploads, multimodal inputs, and conversation state that may not fit a small helper library cleanly.
- Provider capabilities are asymmetric. For example, official documentation surfaced MCP support for OpenAI, Anthropic, and xAI, but not clearly for Gemini API. Forcing a symmetric API across all four providers risks inventing unsupported behavior.
- Introducing many helpers can produce a fragmented public API unless the naming and export pattern are kept consistent across providers.
- The repository has no configured lint/type-check commands visible yet, so the later quality pipeline will need to infer or document the available tooling.

Phase 1 complete
