### Clarifying Questions

1. Scope boundary: should this expansion stay in the current "deterministic payload-builder/helper" layer, or do you want actual provider client helpers that perform authenticated HTTP/SDK calls?
Why it matters: live client helpers would require new dependencies, auth/config handling, failure-mode design, and a different testing strategy than the existing pure-function modules.
Options:
- Payload builders only, preserving the current architecture
- Payload builders plus thin client-call wrappers
- Full provider clients where practical

2. Capability target: when you say "full capability suite," do you want me to cover only request-building features that are natural for this repo now, or should I also add adjacent surfaces like streaming, batch APIs, file uploads, and multimodal input helpers where a provider supports them?
Why it matters: the broader interpretation turns this into a much larger provider SDK surface rather than an expansion of the current translation helpers.
Options:
- Core request surfaces only: tools, tool choice, MCP, structured outputs, server/built-in tools, provider request options
- Include advanced request surfaces too: streaming, files, multimodal blocks, batch helpers
- Literal maximal coverage, even if it adds significant surface area

3. Documentation expectation: do you want a repository artifact that documents each provider's supported helper surface and the official docs/source links I used, or do you only want code and tests?
Why it matters: your request explicitly mentions "more things in the doc," and that could either mean internal code docstrings or a durable repo-level capability reference.
Options:
- Code and tests only
- Code/tests plus an `artifacts/` capability reference
- Code/tests plus richer inline/docstring documentation only

4. Symmetry rule: should every provider expose the same helper names where conceptually possible, or should I keep each provider surface idiomatic to the provider even if that means asymmetric APIs?
Why it matters: forcing symmetry can make call sites simpler, but it also risks hiding provider-specific semantics or inventing unsupported abstractions.
Options:
- Prefer symmetric names where capabilities align, diverge only when the provider truly differs
- Keep each provider fully idiomatic, even if the public APIs differ a lot
- Build a symmetric shared facade on top of provider-specific helpers

### Responses

1. Implement actual client helpers with the necessary parameters for each provider, not payload builders only.
2. Broader provider services are acceptable, but functions should stay small, reusable, and each provider folder should be neatly organized.
3. Only code and tests are required; do not add separate repo documentation artifacts for this task.
4. Keep helper names symmetric where capabilities are similar, and diverge into provider-specific functions where the surfaces genuinely differ.

### Implications

- The implementation should introduce real request-executing client helpers, likely via a shared lightweight HTTP transport abstraction plus provider-specific endpoint/header helpers.
- The provider folders should be refactored into multiple focused modules rather than keeping all functionality in a single `helpers.py`.
- No new `artifacts/` documentation file is needed; code structure, docstrings, exports, and tests must carry the clarity burden.
- Shared naming should cover concepts like custom tools, tool choice, structured outputs, and create/list requests when semantics align, while provider-specific helpers should cover features like Anthropic server tools, xAI collections/X search, OpenAI Responses built-in tools, and Gemini grounding/caching features.
