### 1a: Structural Survey

Repository shape:
- `harnessiq/` is the production SDK package. The top-level domains in active use are `agents/`, `providers/`, `tools/`, `toolset/`, `shared/`, `config/`, `cli/`, `integrations/`, and `utils/`.
- `tests/` contains unit coverage across agents, providers, tools, CLI flows, and the SDK package surface.
- `artifacts/file_index.md` is the active architectural index. It explicitly defines `harnessiq/shared/` as the place for shared types, configs, and constants reused across modules.
- `memory/` already stores prior engineering artifacts and is the expected location for this task’s process documents.

Technology and tooling:
- Python package managed through `pyproject.toml` with `setuptools`.
- Test stack is mixed but lightweight: `unittest` is common, and some newer suites use `pytest` style assertions.
- No dedicated linter or type-checker configuration is present in `pyproject.toml`.
- Git worktree usage is common in this repo, but the current workspace is already dirty on `simplify-file-index-folders`.
- `git fetch origin` worked in this environment, and local `main` has been updated to match `origin/main` at `99730ea98688fca6f3dab598520b374870accba7`.

Architecture and conventions:
- Agent harnesses inherit runtime behavior from `BaseAgent` and should keep non-behavioral definitions in `harnessiq/shared/` when those definitions are durable, reusable, or part of the public surface.
- Provider packages are split into focused modules: `api.py` for endpoint helpers, `client.py` for thin HTTP clients, `operations.py` for provider operation metadata and tool-facing request prep, `requests.py` for payload builders, and `credentials.py` where applicable.
- `harnessiq/shared/` already centralizes several categories:
  - `shared/agents.py` for generic agent runtime types and config.
  - `shared/linkedin.py`, `shared/knowt.py`, and `shared/exa_outreach.py` for agent-specific constants and data models.
  - `shared/providers.py` for provider-agnostic provider aliases/constants.
  - `shared/tools.py` for tool constants, tool runtime dataclasses, and tool-facing aliases.
- Public package `__init__.py` files are curated export layers. Internal refactors should preserve the current package-level API unless there is a strong reason not to.
- Non-behavioral dataclasses and constants are routinely marked `frozen=True, slots=True`; mutable file-backed stores use `slots=True`.

Relevant inconsistencies:
- The shared pattern is only partially applied.
- `harnessiq/agents/email/agent.py` still defines `DEFAULT_EMAIL_AGENT_IDENTITY` and `EmailAgentConfig` inline instead of sourcing them from `harnessiq/shared/`.
- `harnessiq/agents/linkedin/agent.py` still defines `LinkedInMemoryStore`, `SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS`, and `normalize_linkedin_runtime_parameters()` inline even though `shared/linkedin.py` already owns the LinkedIn constants and core data models.
- `harnessiq/agents/exa_outreach/agent.py` still defines `ExaOutreachAgentConfig` inline while the rest of that agent’s data model lives in `shared/exa_outreach.py`.
- Many provider packages still define reusable constants and operation metadata inside `providers/*`:
  - `DEFAULT_BASE_URL` and similar endpoint constants remain in provider `api.py` files.
  - Several provider operation modules still define provider request-key constants that are already duplicated in `shared/tools.py`.
  - Provider operation dataclasses/catalog metadata still live under `providers/*/operations.py` even when those types are imported by adjacent tool/provider modules and behave like definition-only shared state.

Data flow relevant to this task:
- Agent harnesses import config/constants/types from `harnessiq/shared/*`, then combine them with runtime behavior in the concrete agent module.
- Provider clients and tools depend on provider constants and operation metadata to build URLs, validate operation names, and construct tool surfaces.
- Tests assert on the current public import surfaces for agents/providers and on some exact constant-driven behavior such as default URLs and tool names.

### 1b: Task Cross-Reference

User request:
- Slightly refactor the codebase so that configs/types/constants for all agents and providers live in the shared folder as the central source of truth.
- Follow the file index as the architectural rule.
- Ensure local `main` is up to date before starting.

Task-to-code mapping:
- “Make sure local main is up to date before starting”
  - Completed by fetching `origin` and fast-forwarding the local `main` branch ref to `origin/main`.
- “Configs/types/constants for all of the agents”
  - `harnessiq/agents/email/agent.py`
    - `DEFAULT_EMAIL_AGENT_IDENTITY`
    - `EmailAgentConfig`
  - `harnessiq/agents/linkedin/agent.py`
    - `LinkedInMemoryStore`
    - `SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS`
    - `normalize_linkedin_runtime_parameters`
    - supporting non-behavioral helper logic tightly coupled to that store/normalization layer
  - `harnessiq/agents/exa_outreach/agent.py`
    - `ExaOutreachAgentConfig`
  - `harnessiq/agents/knowt/agent.py`
    - already aligned: `KnowtAgentConfig`, `KnowtMemoryStore`, and prompt filename constants are in `shared/knowt.py`
  - `harnessiq/shared/linkedin.py`, `harnessiq/shared/exa_outreach.py`
    - existing shared homes that likely need expansion rather than new parallel files
  - `harnessiq/shared/email.py`
    - net-new likely home for reusable email-agent definitions
- “Configs/types/constants for all of the providers”
  - `harnessiq/providers/*/api.py`
    - provider base URL / API version / token URL / scope / MIME type constants are still provider-local
  - `harnessiq/providers/*/operations.py`
    - operation dataclasses, prepared-request dataclasses, catalog constants, and sometimes request-key constants still live inline
  - `harnessiq/shared/providers.py`
    - existing generic shared provider module that can either be expanded for cross-provider constants or supplemented by provider-specific shared modules
  - `harnessiq/shared/tools.py`
    - already holds many provider request-key constants that some provider operation modules still duplicate

High-probability files touched:
- Agent/shared layer:
  - `harnessiq/shared/email.py` (new)
  - `harnessiq/shared/linkedin.py`
  - `harnessiq/shared/exa_outreach.py`
  - `harnessiq/agents/email/agent.py`
  - `harnessiq/agents/linkedin/agent.py`
  - `harnessiq/agents/exa_outreach/agent.py`
  - `harnessiq/agents/email/__init__.py`
  - `harnessiq/agents/linkedin/__init__.py`
  - `harnessiq/agents/__init__.py`
  - tests covering email/linkedin/exa_outreach agents
- Provider/shared layer:
  - `harnessiq/shared/providers.py`
  - provider `api.py` modules for constant imports
  - provider `operations.py` modules that still own reusable metadata/types
  - provider package `__init__.py` files where those definitions are re-exported
  - tests covering provider packages whose constants or operation metadata are public

Behavior that must be preserved:
- Existing public import ergonomics from `harnessiq.agents` and provider packages.
- Constant values such as provider default base URLs, Google Drive scope/token URL, and provider request tool keys.
- Existing provider request-building behavior, agent memory behavior, and test-visible runtime semantics.
- No behavioral redesign of clients, request builders, or agent execution loops beyond the import/boundary changes needed to centralize definitions.

Blast radius:
- Moderate.
- Agent changes are localized but touch public exports and memory/runtime helpers.
- Provider changes are broad because default URL constants and operation metadata are distributed across many packages.
- Structural refactor risk is mostly import churn and accidental circular dependencies rather than logic changes.

### 1c: Assumption & Risk Inventory

Assumptions I am making:
- “Shared folder” means `harnessiq/shared/`, matching `artifacts/file_index.md`, not a new top-level directory.
- “Configs/types/constants” includes immutable config dataclasses, durable memory-store data models, provider operation metadata dataclasses, and provider endpoint constants, but does not require moving behavior-heavy client methods or request-building functions themselves.
- Existing public package exports should keep working after the refactor, even if internal imports are redirected to `harnessiq/shared/*`.
- This should remain a structural refactor, not a redesign of how agents or providers work.

Ambiguities resolved by codebase context rather than user follow-up:
- Whether to create new shared modules or expand existing ones:
  - Use the established pattern: expand `shared/linkedin.py` and `shared/exa_outreach.py`, add `shared/email.py`, and add provider-side shared homes where needed.
- Whether every provider client dataclass belongs in shared:
  - Treat provider endpoint constants and operation metadata as in-scope first because they are definition-only and already reused.
  - Leave behavior-centric client implementations in provider modules unless a config/type must move to satisfy the source-of-truth requirement.

Implementation risks:
- `harnessiq/agents/linkedin/agent.py` is already modified in the working tree; extracting `LinkedInMemoryStore` and runtime-parameter helpers must preserve those in-flight Google Drive and duplicate-application changes.
- Provider operation modules often blend pure metadata with behavior. Splitting only the metadata into shared modules must avoid circular imports with provider clients or tool factories.
- `shared/providers.py` could become an unreadable dumping ground if all provider-specific definitions are forced into one file. Provider-specific shared modules may be the cleaner outcome where metadata is non-trivial.
- Many provider packages re-export constants directly from `api.py` or `operations.py`; public surfaces must be updated carefully so tests and downstream imports do not break.
- The repository is dirty and not on `main`; destructive resets are off limits. Edits must layer on top of the branch’s current state.

Phase 1 complete
