## Task

Create a config-loader layer in the SDK so users can easily store and load credentials for the tooling layer. Agents should be able to accept this config-layer class for their credential inputs, while also preserving the ability for users to pass credentials directly in their own code. The new credential configs should live under a dedicated config folder in `harnessiq/` and remain distinct from existing shared config/constants modules.

### 1a: Structural Survey

Top-level architecture:

- `harnessiq/` is the installable Python SDK package.
- `harnessiq/agents/` contains the provider-agnostic runtime base plus concrete agent harnesses.
- `harnessiq/tools/` contains tool runtimes and third-party integrations. This is where the current Resend credential type lives.
- `harnessiq/providers/` contains provider clients and request helpers; provider clients currently accept raw API keys directly.
- `harnessiq/shared/` contains reusable dataclasses, constants, and protocol definitions.
- `harnessiq/cli/` currently only exposes LinkedIn commands backed by the LinkedIn memory store.
- `tests/` is an extensive `unittest` suite with file-aligned module coverage.

Relevant runtime patterns:

- Agent constructors are explicit and typed. `BaseAgent` owns the runtime loop; concrete agents compose tool registries and durable parameter sections.
- Durable agent state is implemented today only for LinkedIn via `LinkedInMemoryStore` in `harnessiq/agents/linkedin.py`.
- Credential-bearing integrations are currently direct-object based, not store based:
  - `EmailAgentConfig` in `harnessiq/agents/email.py` requires `ResendCredentials`.
  - `ResendClient` in `harnessiq/tools/resend.py` requires `ResendCredentials`.
  - Provider clients under `harnessiq/providers/*/client.py` accept raw `api_key: str`.
- Public API exposure is export-driven through `harnessiq/agents/__init__.py`, `harnessiq/tools/__init__.py`, and lazy top-level module exports in `harnessiq/__init__.py`.

Conventions in use:

- Dataclasses are frozen and slot-based when representing stable config/value objects.
- Validation happens in `__post_init__` with clear `ValueError` messages.
- Persistent local state uses JSON or text files with small store/helper classes.
- Tests emphasize public behavior and prompt/tool surface, not implementation details.
- Documentation lives in `README.md` and focused docs files under `docs/`.

Observed inconsistencies relevant to this task:

- Durable runtime state exists for LinkedIn, but secret/credential persistence has no equivalent abstraction.
- Credentials currently live in integration modules (`harnessiq/tools/resend.py`) instead of a central config namespace.
- Provider clients and agents use different credential shapes: provider clients take raw strings; email agents take a typed credentials object.

### 1b: Task Cross-Reference

The requested change maps onto the codebase as follows:

- New config namespace:
  - A new package under `harnessiq/config/` is the correct place for a dedicated credential config/store layer because the user explicitly wants a dedicated config folder separate from `harnessiq/shared/`.
- Agent credential ingestion:
  - `harnessiq/agents/email.py` is the only current agent module with an explicit credential parameter (`EmailAgentConfig.resend_credentials`). It must accept either direct credentials or the new config-layer object without breaking existing direct usage.
  - `harnessiq/agents/__init__.py` will need export updates if new credential-config types are part of the agent-facing surface.
- Third-party credential model:
  - `harnessiq/tools/resend.py` contains `ResendCredentials`, the only current typed third-party credential object used by an agent. It is the primary adapter target for the new store/loader layer.
- Packaging and discoverability:
  - `harnessiq/__init__.py` may need to expose the new `config` module at the top level.
  - `pyproject.toml` already packages `harnessiq*`, so a new `harnessiq/config/` package will be included automatically.
- Tests:
  - `tests/test_email_agent.py` must expand to cover store-backed credential loading while preserving direct credential injection.
  - `tests/test_sdk_package.py` should verify the new module is importable from the built package if it becomes public API.
  - Net-new tests will likely be needed for the credential store/config layer itself.
- Documentation:
  - `README.md` and likely one focused doc/example should show direct credential usage versus stored credential usage.
- Repository architecture artifact:
  - `artifacts/file_index.md` already notes that meaningful structural folders should be tracked, so adding `harnessiq/config/` implies updating this index.

Behavior that must be preserved:

- Existing direct construction paths using `ResendCredentials(api_key=...)` must continue to work unchanged.
- Existing email-agent prompt rendering must continue to redact secrets and avoid leaking raw keys.
- LinkedIn memory-store behavior must remain unaffected unless intentionally extended.

Net-new behavior likely required:

- A small credential store abstraction for saving/loading credential configs.
- A serializable credential-config shape that can represent values sourced from environment variables and/or direct third-party API keys.
- An adapter path from stored config objects into the concrete runtime credential type used by the agent/tool layer.

Blast radius:

- Medium. The public SDK surface changes, but the behavioral touch points are limited if the first implementation targets the current email/Resend path and introduces a generic store that future agents can reuse.

### 1c: Assumption & Risk Inventory

Assumptions currently implied by the request:

- "Each agent" likely means every agent that has credential-bearing integrations, not necessarily retrofitting a credentials parameter into agents that currently do not have one.
- "Store and upload credentials" likely means local SDK-managed persistence/load APIs, not a hosted remote secret manager.
- "Actual values should be solely environment variables or api keys" could mean either:
  - the store should persist literal secret values and env-var references, or
  - the store should persist only env-var names and never literal secrets.
- The new config layer should be agent-facing first, with provider/client support optional unless needed to avoid duplication.

Risks:

- Public API drift: adding a credential abstraction that is too specific to Resend will age poorly once more agents require credentials.
- Secret-handling mistakes: prompt rendering and serialized storage must not accidentally expose raw values where only redacted summaries belong.
- Ambiguous persistence contract: without clear rules for env-var references versus literal API key storage, the loader API can become inconsistent or unsafe.
- Over-scoping: extending every provider client and all future credential types in one change would increase blast radius beyond the current agent surface.

Open ambiguities that materially affect implementation:

- Whether stored credential configs may contain literal secrets, env-var references, or both.
- Whether the first implementation should support only the current email/Resend agent path or also provider clients and non-email agents.
- Whether "upload" requires CLI/file ingestion in this ticket or only SDK APIs for saving/loading config objects.

Phase 1 complete.
