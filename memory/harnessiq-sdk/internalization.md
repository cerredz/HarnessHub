## Harnessiq SDK Internalization

### 1a: Structural Survey

#### Repository shape

- `src/` is the only production code root. It is a plain Python source tree, not an installable package distribution yet.
- `tests/` contains the verification surface. The suite is written in `unittest` style and is compatible with `pytest`.
- `artifacts/file_index.md` is the repo-maintained structural index and reflects the intended architecture.
- `memory/` stores prior planning, ticketing, quality, and critique artifacts from earlier workstreams.
- Root packaging metadata is absent. There is no `pyproject.toml`, `setup.py`, `setup.cfg`, `MANIFEST.in`, or lockfile/workspace config.
- `requirements.txt` currently contains only `langsmith>=0.6.7,<1.0.0`.

#### Source architecture

- `src/shared/`
  - Shared type definitions, constants, and data models.
  - `agents.py` defines the provider-agnostic agent loop contracts and runtime data models.
  - `tools.py` defines the canonical tool schema, tool registry payloads, and core tool keys.
  - `providers.py` defines provider names and normalized provider message types.
  - `linkedin.py` holds LinkedIn-specific shared constants/config/data records used by the concrete LinkedIn harness.

- `src/tools/`
  - The reusable tool runtime layer.
  - `registry.py` provides deterministic registration, lookup, schema validation, and execution.
  - `builtin.py` composes the default tool set from several tool families.
  - `general_purpose.py` exposes pure utility tools for text, records, and human pause signaling.
  - `filesystem.py` exposes explicitly non-destructive filesystem tools.
  - `context_compaction.py` exposes context-window compaction and summarization helpers/tools.
  - `prompting.py` builds system prompts from structured context.
  - `resend.py` exposes the largest external integration: a declarative Resend operation catalog, validated request preparation, and a single MCP-style request tool.
  - `src/tools/__init__.py` is already treated as a public surface for internal consumers. It re-exports tool constants, types, helper functions, and registry entrypoints.

- `src/agents/`
  - The agent harness layer.
  - `base.py` provides a provider-agnostic agent loop with transcript management, tool execution, pause handling, and context reset/compaction support.
  - `email.py` defines an abstract email-capable agent harness that injects Resend tooling and masked credential metadata.
  - `linkedin.py` defines a concrete LinkedIn job application harness, durable memory store, browser tool definitions/stubs, pause-notify behavior, and append-only run-state tools.
  - `src/agents/__init__.py` already behaves like a curated public export module for agent consumers.

- `src/providers/`
  - Provider translation and transport helpers.
  - `base.py` normalizes messages and converts canonical tool definitions into provider-native formats.
  - `http.py` provides stdlib HTTP execution and normalized error handling.
  - `langsmith.py` provides tracing decorators/wrappers for agent, model, and tool runs.
  - `anthropic/`, `openai/`, `grok/`, and `gemini/` each contain request builders, tool builders/translators, helpers, and thin clients.
  - Each provider subpackage has its own `__init__.py` acting as a curated API surface.

#### Current data flow

- Agent flow:
  - Concrete agent subclasses produce a system prompt plus durable parameter sections.
  - `BaseAgent` converts those plus transcript state and tool definitions into `AgentModelRequest`.
  - A provider-agnostic model adapter is expected to implement `AgentModel.generate_turn`.
  - Tool calls are executed through `AgentToolExecutor`/`ToolRegistry`.
  - Tool results are written back to transcript state unless they are compaction tools that rewrite the current context window.
  - The run terminates on completion, explicit pause, tool-generated `AgentPauseSignal`, or max cycle count.

- Tool flow:
  - Tool metadata is canonicalized as `ToolDefinition`.
  - `ToolRegistry` validates runtime arguments against the canonical schema and executes handlers.
  - Built-in tools are composed into a stable ordered set through `BUILTIN_TOOLS`.
  - Higher-level agent harnesses compose custom tools on top of the reusable tool families.

- Provider flow:
  - Canonical provider messages/tool definitions are translated into provider-native request payloads.
  - Thin clients (`OpenAIClient`, `AnthropicClient`, `GeminiClient`, `GrokClient`) wrap request builders and stdlib HTTP execution.
  - LangSmith tracing sits beside provider logic, not inside the core agent loop.

#### Test strategy

- Tests are broad and module-oriented rather than end-to-end system tests.
- Coverage exists for:
  - generic agent loop behavior,
  - LinkedIn and email harness behavior,
  - tool registry and each tool family,
  - Resend request tooling,
  - provider translation/helpers/clients,
  - LangSmith tracing helpers.
- Tests primarily assert on:
  - stable payload shapes,
  - deterministic ordering,
  - validation behavior,
  - request URL/header construction,
  - transcript/context behavior.
- There is no visible lint config, type checker config, or packaging-install test today.

#### Conventions in use

- Code style:
  - Python with `from __future__ import annotations`.
  - Heavy use of frozen dataclasses with `slots=True`.
  - Explicit `__all__` export lists in public modules.
  - Absolute imports rooted at `src.*`.
  - Clear docstrings on public functions/classes.

- API design:
  - Public surfaces are curated via package `__init__.py` files.
  - Canonical internal schemas are defined once in shared modules and translated outward.
  - External-service integration favors declarative operation catalogs over ad hoc request functions.

- Error handling:
  - Validation failures generally raise `ValueError` or domain-specific subclasses.
  - `BaseAgent` converts tool execution exceptions into structured tool-result error payloads rather than crashing the loop.
  - HTTP errors are normalized into `ProviderHTTPError`.

- Configuration:
  - Configuration is dataclass-based and validated in `__post_init__`.
  - No repo-wide environment/config loader exists.

#### Inconsistencies and gaps

- The repo is organized like a reusable library but is not packaged as one.
- Public consumption currently depends on `src.*` imports, which is a repository-internal import root rather than a user-facing distribution name.
- Root docs are minimal; there is no install/use documentation for third-party consumers.
- Dependency declaration is incomplete for a distributable SDK. Only `langsmith` is declared, while provider integrations rely on stdlib HTTP and do not express optional extras or SDK-level install groups.
- Quality gates for linting/type checking are not configured in the repo, despite strong test coverage.
- The package identity is currently `HarnessHub` in docs/comments, while the requested SDK identity is `Harnessiq`.

### 1b: Task Cross-Reference

#### User request mapped to the codebase

User intent: package “our agents and injectible tools (core functionalities), and just this repo in general” into an SDK named `Harnessiq` so external users can use the agents being built here in their own code.

Relevant existing code:

- Agent primitives and concrete harnesses already exist under:
  - `src/agents/base.py`
  - `src/agents/email.py`
  - `src/agents/linkedin.py`
  - `src/agents/__init__.py`

- Reusable injectable tool primitives already exist under:
  - `src/tools/*.py`
  - `src/tools/__init__.py`
  - `src/shared/tools.py`

- Provider/client utilities that external users would likely need to pair with agents exist under:
  - `src/providers/*.py`
  - `src/providers/*/__init__.py`
  - `src/shared/providers.py`

- Shared runtime models that are part of the practical public API already exist under:
  - `src/shared/agents.py`
  - `src/shared/linkedin.py`
  - `src/shared/tools.py`

What is missing for an SDK:

- A real installable package/distribution with packaging metadata.
- A user-facing top-level package namespace matching `Harnessiq`.
- Removal or encapsulation of `src.*` as the required consumer import root.
- A consciously designed public API surface that separates stable SDK exports from internal modules.
- Installation and usage documentation for external consumers.
- Validation that the package can be imported/installed in the way external users will consume it.

Likely file/module impact:

- Root packaging/config:
  - net-new `pyproject.toml` or equivalent build metadata.
  - possible README expansion for SDK installation/examples.

- Public package namespace:
  - either rename/move `src/` into a distributable `harnessiq/` package or create a top-level `harnessiq/` facade package that re-exports the current implementation.
  - any such change will touch most source imports because the codebase currently imports through `src.*`.

- Public export design:
  - package-level `__init__.py` modules for `harnessiq`, `harnessiq.agents`, `harnessiq.tools`, `harnessiq.providers`, and possibly `harnessiq.shared`.

- Tests:
  - import-path updates/additional tests to verify the SDK surface.
  - likely packaging/import smoke tests.

Behavior that must be preserved:

- Existing agent loop semantics, tool execution behavior, provider request builders, and current test expectations.
- Stable tool keys and canonical schemas.
- Existing concrete agent capabilities, especially `LinkedInJobApplierAgent` and `BaseEmailAgent`.
- Existing provider client/request builder behavior.

Blast radius

- Medium to high.
- The repo is small, but the import-root decision affects nearly every source file and test because `src.*` is embedded throughout the codebase.
- A packaging-only wrapper could reduce code churn, but it changes how external users import and understand the SDK.
- A full rename/move to `harnessiq` would be cleaner externally but broader internally.

### 1c: Assumption & Risk Inventory

#### Assumptions embedded in the task

- “SDK” could mean:
  - an installable Python package only,
  - a package plus documented extension points,
  - or a broader developer product with CLI/examples/templates.
- “agents and injectable tools” implies external users should both:
  - instantiate the existing agents directly, and/or
  - compose their own agents with the shared runtime/tool layers.
- The desired SDK name is `Harnessiq`, but the task does not specify whether:
  - the import path must be `import harnessiq`,
  - the distribution name must be `harnessiq`,
  - or whether internal code should also be renamed from `HarnessHub` to `Harnessiq`.
- The task does not specify whether provider helpers are in scope as first-class public SDK APIs or only internal support utilities.
- The task does not specify whether the LinkedIn and email agents should remain “reference harnesses” or be treated as stable supported SDK components.

#### Material ambiguities

- Import-path strategy:
  - keep internal `src` structure and add a thin `harnessiq` facade, or
  - rename the source package entirely.
- Public API scope:
  - expose only curated package exports, or
  - expose most existing modules as public SDK surface.
- Distribution/publishing target:
  - local editable installs only,
  - private package distribution,
  - or eventual public PyPI compatibility.
- Dependency strategy:
  - keep provider integrations stdlib-only and optional where possible,
  - or define extras such as `langsmith`, provider-specific, and email/browser extras.

#### Risks

- A naive package rename will break all current tests/imports and require repo-wide path churn.
- A facade-only SDK may preserve compatibility but can create duplicate surfaces (`src.*` and `harnessiq.*`) unless the old path is intentionally deprecated or kept internal.
- If the public API is too broad, this repo will accidentally freeze internal implementation details as supported SDK contracts.
- If the public API is too narrow, external users will still need to import internal modules directly, which defeats the SDK boundary.
- Packaging without install/import smoke tests risks producing a nominal SDK that still only works inside the repo.
- The existing minimal README and lack of packaging metadata mean external users currently have no supported install path; documentation debt will immediately show up in adoption friction.
- The skill workflow expects GitHub issue creation later, but network/auth constraints may block `gh` commands in this environment even if local implementation is possible.

Phase 1 complete.
