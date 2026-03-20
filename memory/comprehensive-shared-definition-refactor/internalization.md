### 1a: Structural Survey

Repository shape:
- `harnessiq/` is the shipped SDK package. The main runtime boundaries are `agents/`, `providers/`, `tools/`, `toolset/`, `shared/`, `config/`, `cli/`, `integrations/`, and `utils/`.
- `artifacts/file_index.md` is the active architectural source of truth. It explicitly assigns `harnessiq/shared/` as the home for shared types, configs, and constants.
- `tests/` contains package-level coverage across agents, providers, tools, CLI entrypoints, config loading, and public package exports.
- `memory/` is already used as the engineering-artifact workspace for prior tasks and is the correct place for this task’s planning and verification docs.

Technology and tooling:
- Python package built with `setuptools` via `pyproject.toml`.
- No repo-configured linter or type checker is declared in `pyproject.toml`.
- Test execution uses `pytest` from the local virtualenv/tooling in the repo.
- The working tree is currently dirty on `feature/agent-audit-ledger-sinks`, so implementation should be isolated in a clean worktree from `origin/main` rather than layered directly on this branch.

Architecture and conventions:
- Agent harnesses inherit from `BaseAgent` and are expected to keep durable models, runtime config, and reusable constants outside the behavior-heavy harness loop where possible.
- Provider packages generally split responsibilities into `api.py` for URL/header helpers, `client.py` for thin execution wrappers, `operations.py` for operation metadata and request preparation, and `requests.py` where payload builders are needed.
- `harnessiq/shared/` already centralizes a meaningful subset of repo definitions:
  - `shared/agents.py` contains generic runtime types/configs for the base harness.
  - `shared/linkedin.py`, `shared/instagram.py`, `shared/knowt.py`, `shared/exa_outreach.py`, and `shared/email.py` already hold several agent-domain constants and config/data-model definitions.
  - `shared/providers.py` holds many provider base URLs and generic provider aliases.
  - `shared/tools.py` holds tool keys, tool runtime models, and tool-facing constants.
- Public `__init__.py` files are curated export surfaces. Internal moves need to preserve import ergonomics and not strand tests or downstream callers on old paths.

Current consistency level:
- Agent-side shared-definition discipline is partially in place and materially better than provider-side discipline.
- Provider-side definitions are still fragmented:
  - Some providers already source default base URLs from `shared/providers.py` (`openai`, `anthropic`, `gemini`, `arcads`, `exa`, `instantly`, `leadiq`, `lemlist`, `outreach`, `peopledatalabs`, `phantombuster`, `proxycurl`, `salesforge`, `snovio`, `zoominfo`, `grok`, `google_drive`).
  - Some providers still own base URL constants directly in provider modules (`attio`, `paperclip`, `inboxapp`, `serper`).
  - Most provider credentials/config dataclasses still live inline in `client.py`.
  - Most provider operation metadata dataclasses and catalogs still live inline in `operations.py`.
- Agent harness modules still own some non-behavioral constants such as prompt-path locators and default-memory-path locators even where the durable config/data models have already been centralized.

Codebase-level audit findings from the live tree:
- Agents:
  - `harnessiq/agents/email/agent.py` already imports config/identity from `shared/email.py`.
  - `harnessiq/agents/linkedin/agent.py` already imports LinkedIn runtime config, memory store, and runtime-parameter helpers from `shared/linkedin.py`.
  - `harnessiq/agents/exa_outreach/agent.py`, `harnessiq/agents/instagram/agent.py`, and `harnessiq/agents/knowt/agent.py` still define module-private prompt path constants (`_PROMPTS_DIR`, `_MASTER_PROMPT_PATH`) and, in some cases, `_DEFAULT_MEMORY_PATH`.
- Providers:
  - Inline credential/config dataclasses exist in many `client.py` modules (`ArcadsCredentials`, `AttioCredentials`, `CreatifyCredentials`, `ExaCredentials`, `GoogleDriveCredentials`, `InboxAppCredentials`, `InstantlyCredentials`, `LemlistCredentials`, `OutreachCredentials`, `PaperclipCredentials`, `SerperCredentials`, plus model-provider configs like `OpenAIClient`, `AnthropicClient`, `GeminiClient`, `GrokClient`).
  - Inline operation metadata types/catalogs exist in many `operations.py` modules (`ArcadsOperation`, `AttioOperation`, `CoreSignalOperation`, `CreatifyOperation`, `ExaOperation`, `GoogleDriveOperation`, `InboxAppOperation`, `InstantlyOperation`, `LeadIQOperation`, `LemlistOperation`, `OutreachOperation`, `PaperclipOperation`, `PeopleDataLabsOperation`, `PhantomBusterOperation`, `ProxycurlOperation`, `SalesforgeOperation`, `SnovioOperation`, `ZoomInfoOperation` and their prepared-request companions where applicable).
  - `harnessiq/providers/output_sinks.py` also owns sink config constants such as `DEFAULT_NOTION_VERSION`, which is outside the user’s stated agent/provider scope but still structurally similar.

### 1b: Task Cross-Reference

User request:
- Since the Paperclip change is already merged to `main`, perform a codebase-wide pass over all agents and providers and ensure types/constants/config values live in `harnessiq/shared/` per the file index.
- Provide a comprehensive refactor rather than a narrow cleanup.

Task-to-code mapping:
- “All of our agents”
  - `harnessiq/agents/email/agent.py`
  - `harnessiq/agents/exa_outreach/agent.py`
  - `harnessiq/agents/instagram/agent.py`
  - `harnessiq/agents/knowt/agent.py`
  - `harnessiq/agents/linkedin/agent.py`
  - Existing shared homes: `harnessiq/shared/email.py`, `harnessiq/shared/exa_outreach.py`, `harnessiq/shared/instagram.py`, `harnessiq/shared/knowt.py`, `harnessiq/shared/linkedin.py`
- “All of our providers”
  - `harnessiq/providers/*/api.py`
  - `harnessiq/providers/*/client.py`
  - `harnessiq/providers/*/operations.py`
  - Existing shared home: `harnessiq/shared/providers.py`
  - Potential net-new provider-domain shared homes under `harnessiq/shared/` for provider-specific config/type/operation definitions that are too large for the generic shared provider module.
- Public exports and import surfaces that must remain stable:
  - `harnessiq/agents/__init__.py`
  - `harnessiq/agents/<agent>/__init__.py`
  - `harnessiq/providers/__init__.py`
  - `harnessiq/providers/<provider>/__init__.py`
  - tests that import provider constants, credentials, operations, or agent config/types from existing package paths

High-probability change classes:
- Agent refactor:
  - Move remaining non-behavioral agent constants/configs/path definitions out of harness modules and into their corresponding shared agent-domain modules.
  - Keep harness modules focused on orchestration and runtime behavior.
- Provider refactor:
  - Centralize remaining provider base URLs and default API constants into shared definitions.
  - Centralize provider credential/config dataclasses into shared definitions.
  - Centralize provider operation metadata dataclasses/catalog definitions into shared definitions, leaving provider `operations.py` modules as request-preparation and export adapters where needed.
  - Preserve tool and client behavior while shifting source-of-truth ownership.

Behavior that must be preserved:
- Existing HTTP request semantics, auth header behavior, URL building, and operation validation.
- Existing agent memory behavior and prompt loading.
- Existing package exports or at minimum compatibility re-exports from the current provider/agent package surfaces.
- Existing test-visible constant values and runtime defaults.

Blast radius:
- High.
- This touches every agent domain and most provider packages.
- The main technical risks are circular imports, broken package exports, and excessive churn in provider operation modules if shared extraction is too mechanical.

### 1c: Assumption & Risk Inventory

Assumptions:
- “Shared folder” means `harnessiq/shared/`, aligned to `artifacts/file_index.md`.
- “Types/constants/config values” includes immutable config dataclasses, TypedDicts/type aliases, operation metadata dataclasses, prepared-request dataclasses, and provider default endpoint/version/scope constants.
- Behavior-heavy code should remain in agents/providers; only definition ownership should move.
- Public import compatibility should be preserved via re-exports where necessary.

Open ambiguities that materially affect the implementation:
- Whether module-private prompt path and default-memory-path constants in agent harnesses should also move to `shared/`, or whether those may remain harness-local because they are implementation scaffolding rather than reusable shared definitions.
- Whether provider credential/config dataclasses should all move to `shared/` even when only one provider module currently consumes them.
- Whether the sweep should stay strictly within `agents/` and `providers/` or also include structurally similar config/constants in adjacent runtime modules such as `providers/output_sinks.py`.

Implementation risks:
- The current workspace is heavily dirty and not based directly on `main`; implementation in place would risk mixing unrelated changes. A dedicated worktree from `origin/main` is the safe path.
- Provider operation modules currently mix pure metadata with request-preparation logic. Extracting metadata without causing import cycles requires disciplined module boundaries.
- `shared/providers.py` is already dense; forcing every provider’s full metadata into one file would make it unmaintainable. Provider-specific shared modules are likely required.
- Some tests import through provider package surfaces, so removing exports instead of re-pointing them would create unnecessary breakage.

Phase 1 complete
