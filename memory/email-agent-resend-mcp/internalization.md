### 1a: Structural Survey

Repository shape:

- `src/agents/` contains the provider-agnostic agent runtime (`BaseAgent`) plus the current concrete LinkedIn harness.
- `src/tools/` contains the canonical tool runtime: `RegisteredTool`, `ToolDefinition`, deterministic validation/execution via `ToolRegistry`, and built-in tool families.
- `src/shared/` stores reusable typed definitions that sit below both agents and tools.
- `src/providers/` contains HTTP/request helpers and model-provider-specific builders/clients; its stdlib JSON transport is reusable outside model providers.
- `tests/` uses `unittest` and favors fake executors over live integrations.
- `artifacts/file_index.md` is the maintained architecture index for the repo and should stay aligned with meaningful structure/test additions.
- `memory/` stores workflow artifacts for prior repository tasks.

Technology and conventions:

- Plain Python package layout with standard-library networking and testing.
- Small dataclasses, protocols, and explicit helper functions are preferred over framework-heavy abstractions.
- Public surfaces are curated through `__init__.py` exports.
- Tool metadata is canonical and provider-agnostic; runtime behavior is injected via handlers and fakeable executors.
- Existing harnesses keep domain-specific state in dedicated modules rather than entangling it with the generic agent loop.

Relevant existing patterns:

- `src/agents/base.py` provides the reusable long-running harness contract and transcript/tool execution lifecycle.
- `src/agents/linkedin.py` shows how a domain-specific harness composes a `ToolRegistry`, exposes stable tool definitions, and layers domain memory/config around the generic loop.
- `src/providers/http.py` already offers a reusable JSON transport abstraction and deterministic HTTP error handling.
- `src/tools/__init__.py` and sibling modules expose tool factories/helpers as the public tooling layer.

Notable gaps relative to the request:

- There is no email-focused agent base class.
- There is no Resend integration in either the tooling layer or a reusable client/helper surface.
- There is no current abstraction for agents that share an external delivery provider while remaining extensible for future domain-specific workflows.

### 1b: Task Cross-Reference

User request mapping:

- "make an agent that is capable of sending emails" maps to a new email-focused agent harness in `src/agents/`.
- "make the email agent an abstract class" maps to a reusable base class that composes email-delivery tooling but leaves domain mission/context overridable by subclasses.
- "the harness should be about sending emails" maps to a system-prompt/parameter-section scaffold oriented around outbound email operations rather than LinkedIn/browser behavior.
- "add tool calls to send emails ... to our tooling layer" maps to a new `src/tools/` module exporting a Resend-backed tool surface and related helpers.
- "use the resend api" maps to a stdlib HTTP client wrapper and operation catalog aligned with the current official Resend API surface.
- "more like an MCP ... incorporate all the functionalities of the resend api" maps to a generic Resend request tool backed by an operation catalog rather than a one-off `send_email` helper only.
- "parameters should be the resend credentials" maps to constructor/config parameters for the email base agent and a redacted credential parameter section in model context rather than hard-coding secrets.

Concrete code locations likely affected:

- `src/tools/resend.py`: new Resend client, operation catalog, and tool factory.
- `src/tools/__init__.py`: export the Resend tooling surface.
- `src/agents/email.py`: new abstract base class for email-capable harnesses.
- `src/agents/__init__.py`: export the new email agent surface.
- `src/providers/http.py`: small shared improvement so transport errors identify `resend` cleanly.
- `tests/`: new unit coverage for the Resend tool/client behavior and the abstract email harness integration.
- `artifacts/file_index.md`: reflect the new tests/memory artifact and keep the architecture index aligned.

Blast radius:

- Mostly additive. The only cross-cutting change is a minor improvement to shared HTTP error inference for the Resend host.
- The new email agent should not disturb the LinkedIn harness or existing built-in tools.
- Tooling design should stay future-friendly so later subclasses can reuse the same Resend-backed base agent without copying client logic.

### 1c: Assumption & Risk Inventory

Implementation assumptions:

- "Resend credentials" means runtime configuration for the agent/tooling layer, not exposing a raw secret into model-visible prompt text.
- A single MCP-style `resend.request` tool with a documented operation catalog is a better fit for "all Resend capabilities" than dozens of unrelated top-level tools.
- The supported operation catalog should cover the currently documented/stable Resend SDK surface: emails, batch send, attachments, receiving, domains, API keys, segments/audiences, contacts/contact topics, contact properties, broadcasts, templates, topics, and webhooks.
- The abstract email agent can remain intentionally non-instantiable as long as tests provide a minimal concrete subclass and the public API clearly supports future extension.

Risks and edge cases:

- Resend’s API surface is broad; a bespoke hand-written method for every endpoint would be noisy and brittle. The operation-catalog design needs to stay explicit enough to be understandable while avoiding repetitive code.
- If the tool schema is too generic, the agent loses guidance; if it is too strict per endpoint, maintenance cost explodes. The catalog description and runtime validation need to strike a middle ground.
- Some Resend endpoints support optional headers such as `Idempotency-Key` and `x-batch-validation`; omitting them would make the integration incomplete for send/batch flows.
- Existing `request_json()` error labeling returns `"provider"` for unknown hosts today, so Resend errors would be less actionable without a small transport improvement.
- The file index should remain accurate without overreacting to every file-level addition; only meaningful updates should be made.

Phase 1 complete
