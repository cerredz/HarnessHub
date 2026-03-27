## Dynamic Tool Selection Internalization

### 1a: Structural Survey

#### Repository shape

- `harnessiq/` is the authoritative runtime source tree.
- `docs/` contains curated hand-written usage notes.
- `artifacts/` contains generated repository reference documents, including `artifacts/file_index.md` and `artifacts/commands.md`.
- `scripts/sync_repo_docs.py` is the generator that keeps the README and generated repo-doc artifacts aligned with the source tree.
- `tests/` is the primary verification surface and is broad, repository-wide, and behavior-oriented.
- `memory/` stores task artifacts, implementation planning, and prior workstream documents; it is part of repo workflow, not shipped runtime code.

#### Technology and runtime stack

- Language: Python 3.11+.
- Packaging: setuptools via `pyproject.toml`.
- CLI: argparse-based under `harnessiq/cli/`.
- Runtime model abstraction: provider-agnostic `AgentModel` protocol plus provider-backed implementations in `harnessiq/integrations/`.
- Tool execution: in-memory deterministic `ToolRegistry` and `RegisteredTool` / `ToolDefinition` models.
- Testing: pytest configured, but tests are mostly `unittest` style modules.

#### Core runtime architecture

- `harnessiq/agents/base/agent.py`
  - owns the shared run loop, transcript management, parameter sections, context reset/pruning, hook execution, and model-request construction.
  - current `build_model_request()` uses `self.available_tools()`, which in turn delegates to the agent's `tool_executor`.

- `harnessiq/shared/agents.py`
  - owns `AgentRuntimeConfig`, `AgentModelRequest`, `AgentModelResponse`, and shared runtime dataclasses.
  - `allowed_tools` is runtime config state here, but it is not itself the source of model-visible schemas.

- `harnessiq/tools/registry.py`
  - provides `ToolRegistry`, the canonical executable registry surface.
  - supports stable ordered lookup, definitions-by-key, and execution.
  - already supports subset selection by key through `definitions(tool_keys=...)` and `select(tool_keys=...)`.

- `harnessiq/tools/hooks/defaults.py`
  - owns the built-in approval and allowlist gate.
  - this is where `allowed_tools` is currently enforced before execution.
  - empty `allowed_tools` means “no explicit allowlist restriction,” not “no tools available.”

- `harnessiq/toolset/`
  - owns catalog/lookup/registration for reusable tool composition.
  - `catalog_provider.py` holds lightweight static provider metadata (`ToolEntry`).
  - `registry.py` resolves catalog-backed `RegisteredTool` objects.
  - this package is catalog-oriented rather than execution-oriented, which makes it the natural home for tool-selection logic that depends on catalog metadata.

- `harnessiq/interfaces/`
  - contains protocol definitions for dependency seams, such as provider clients and model clients.
  - current convention is flat protocol modules plus re-export from `harnessiq/interfaces/__init__.py`.
  - this is the correct architectural home for a `DynamicToolSelector` protocol.

- `harnessiq/shared/`
  - contains shared runtime dataclasses, manifests, provider metadata, and cross-module types/constants.
  - shared selection config/result/profile dataclasses would fit this package well.

#### Tool and prompt composition patterns

- Agents orchestrate and tools execute deterministic work.
- Provider-backed tools are generally exposed as one request-style tool per provider family with operation selection through arguments.
- Concrete agents compose their runtime tool surfaces differently:
  - some accept additive `tools=`
  - some accept specialized surfaces like `browser_tools=`
  - some build prompts that enumerate tool descriptions directly from `available_tools()`

- Notable prompt/building patterns relevant to this task:
  - `harnessiq/agents/provider_base/agent.py` builds provider tool prompt text from `self.available_tools()`.
  - `harnessiq/agents/leads/agent.py` renders a tool list into the master prompt from `self.available_tools()`.

#### CLI and configuration conventions

- Shared CLI runtime config assembly lives in `harnessiq/cli/common.py`.
- `build_runtime_config()` currently accepts sinks, approval policy, and `allowed_tools`.
- Policy flags are shared and repeatable, with normalization helpers such as `parse_allowed_tool_values()`.
- Adding dynamic tool selection through `AgentRuntimeConfig` and the CLI helper layer is consistent with existing patterns.

#### Documentation and generation conventions

- `README.md` is partially generated from live code and references curated docs.
- `docs/tools.md` and `docs/agent-runtime.md` describe the tool and runtime layers at a user-facing level.
- `scripts/sync_repo_docs.py` hard-codes doc-link lists and key-file descriptions that drive generated repo docs.
- Any new documentation meant to be a stable repo doc should be linked through the established docs surfaces and may require updating generator references where appropriate.

#### Testing strategy and patterns

- The test surface is broad and explicit:
  - `tests/test_agents_base.py` covers base runtime behavior.
  - `tests/test_hook_agent_runtime.py` and `tests/test_hook_tools.py` cover allowlist and approval policy behavior.
  - `tests/test_toolset_registry.py` and `tests/test_tool_catalog_families.py` cover catalog behavior.
  - `tests/test_interfaces.py` covers `harnessiq/interfaces` as a public contract layer.
  - `tests/test_cli_policy_options.py` covers CLI runtime/policy parsing behavior.
  - `tests/test_docs_sync.py` covers repo-doc generation behavior.

- The codebase favors small targeted tests over giant integration fixtures for most runtime features.

#### Conventions and notable inconsistencies

- Conventions:
  - protocols live in `harnessiq/interfaces/`
  - shared runtime data models live in `harnessiq/shared/`
  - agents orchestrate; tools do work; providers wrap external systems
  - runtime config is expressed through immutable dataclasses
  - docs and README synchronization is script-driven

- Inconsistencies relevant to this task:
  - the refined design doc initially described `allowed_tools` as if it were the current model-visible schema set, but the live code exposes all `tool_executor` definitions by default and uses `allowed_tools` only as an execution gate.
  - tool metadata is split today between executable `ToolDefinition` and lightweight catalog `ToolEntry`, with no richer retrieval-profile layer.
  - some agents render active tools dynamically from the current executor, but there is no shared “active tool subset for this turn” concept yet.

### 1b: Task Cross-Reference

User request: use the `github-software-engineer` workflow to create tickets and fully implement the optional dynamic tool-calling layer described in `memory/dynamic-tool-selection/design.md`, including code and documentation.

Task-to-codebase mapping:

- Dynamic selection abstraction
  - likely new protocol in `harnessiq/interfaces/`
  - relevant because the user explicitly wants the dynamic tool layer to be “an interface in our interfaces class”
  - impacted files:
    - `harnessiq/interfaces/__init__.py`
    - new `harnessiq/interfaces/tool_selection.py`
    - `tests/test_interfaces.py`

- Shared selection models and runtime config
  - required to store opt-in config and per-turn selection results cleanly
  - impacted files:
    - `harnessiq/shared/agents.py`
    - likely new `harnessiq/shared/tool_selection.py`

- Catalog/profile layer
  - required to express retrieval metadata per tool
  - impacted files:
    - `harnessiq/toolset/catalog_provider.py`
    - `harnessiq/toolset/catalog.py`
    - `harnessiq/toolset/__init__.py`
    - possibly new catalog/profile helpers in `harnessiq/toolset/`

- Concrete selector implementation
  - required to perform indexing and per-turn narrowing
  - best-fit package is `harnessiq/toolset/` because the feature depends on catalog metadata and tool selection, not executable tool functions
  - likely new file:
    - `harnessiq/toolset/dynamic_selector.py`

- Agent runtime integration
  - required to compute active tool keys before prompt/schema assembly
  - impacted files:
    - `harnessiq/agents/base/agent.py`
    - possibly `harnessiq/agents/base/agent_helpers.py` if logging or helper extraction is needed

- Prompt/tool alignment
  - required so prompts that enumerate tools render the active turn-level subset rather than the full executor surface
  - impacted files:
    - `harnessiq/agents/provider_base/agent.py`
    - `harnessiq/agents/leads/agent.py`
    - possibly other agents if additional prompt rendering paths are discovered during implementation

- CLI opt-in surface
  - required if the feature is meant to be configurable through existing harness CLI flows rather than Python-only construction
  - impacted files:
    - `harnessiq/cli/common.py`
    - specific harness command modules that expose run/configure surfaces
    - tests such as `tests/test_cli_policy_options.py` and CLI-specific test modules

- Documentation
  - required because the user asked for implementation and documentation
  - impacted files:
    - new `docs/dynamic-tool-selection.md`
    - `docs/tools.md`
    - `docs/agent-runtime.md`
    - `README.md`
    - `scripts/sync_repo_docs.py`
    - `tests/test_docs_sync.py` if generated/doc expectations change

- Verification surface
  - base runtime tests
  - interfaces tests
  - toolset/catalog tests
  - CLI parsing tests
  - prompt alignment / agent tests for specific agents

What currently exists and can be reused:

- `ToolRegistry.definitions(tool_keys=...)` already supports a selected subset.
- `AgentRuntimeConfig` already carries policy-like runtime configuration and merge behavior.
- `interfaces/` already provides the correct protocol pattern.
- `toolset/` already provides a metadata/catalog layer where richer tool-profile concerns can live.

What is missing and must be built:

- a selector protocol
- shared tool-selection dataclasses
- a retrieval/profile layer richer than `ToolEntry`
- a concrete default selector implementation
- a turn-level “active tool subset” path in `BaseAgent`
- docs for authoring and enabling dynamic selection

Existing behavior that must be preserved:

- agents without dynamic selection enabled must behave exactly as they do today
- existing `allowed_tools` execution gating semantics must remain intact
- prompt and tool schema rendering must remain aligned
- no existing agent should incur extra latency unless it opts in

Blast radius:

- medium to high
- touches shared runtime contracts, public interfaces, tool catalog metadata, agent request assembly, CLI runtime config, and docs
- the base runtime change is central but can remain low risk if the disabled path is strictly preserved

### 1c: Assumption & Risk Inventory

#### Assumptions

- The user wants this feature to be available through the public SDK, not only through internal harness wiring.
- The user wants `DynamicToolSelector` to be a protocol in `harnessiq/interfaces/`, with one default implementation behind it.
- The user wants the initial implementation to include both code and public-facing docs.
- Dynamic selection should be opt-in and disabled by default for backward compatibility.
- `allowed_tools` should remain the execution ceiling and should not be redefined as the source of model-visible schemas.

#### Risks

- If retrieval metadata is required for the entire tool catalog in V1, the scope becomes very large because the repo has a broad built-in and provider-backed tool surface.
- If prompt/tool alignment is not handled correctly, the model could be told it has tools that are not actually present for the turn.
- Adding config to `AgentRuntimeConfig` can ripple into merge behavior, CLI parsing, and tests.
- Pulling in a local embedding dependency changes packaging and may be undesirable for an SDK with a small current dependency set.
- Misinterpreting empty `allowed_tools` as “no candidate tools” would break current behavior, because today an empty allowlist means unrestricted execution by policy hook and agents still expose their registered tools.
- If docs are updated without synchronizing the generation pipeline, generated repo docs or README references may drift.

#### Remaining ambiguities that may block implementation

- Whether V1 must support a local embedding dependency or should require an injectable backend only.
- Whether V1 metadata coverage is expected for the entire catalog or only for the first opt-in agents/tool families.
- Whether CLI support is required in the first implementation or whether Python-construction-only opt-in is acceptable initially.
- Whether the user wants the ticket/issue workflow to create temporary GitHub issues and PRs exactly as the skill describes, including deleting issues after PR creation.

Phase 1 complete.
