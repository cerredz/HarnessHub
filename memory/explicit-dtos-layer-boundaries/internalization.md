### 1a: Structural Survey

HarnessIQ is a Python 3.11+ SDK/CLI package with the live source under `harnessiq/`, test coverage under `tests/`, and a generated high-signal architecture map in `artifacts/file_index.md`. The file index matches the current source layout and confirms the intended architectural boundary: `harnessiq/shared/` is the canonical home for reusable cross-layer definitions, agents orchestrate, providers wrap external systems, and CLI/platform code should consume typed shared metadata rather than inventing local shapes.

Top-level runtime architecture:

- `harnessiq/agents/`: long-running harnesses and reusable agent bases.
  - `harnessiq/agents/base/agent.py` defines the core loop, transcript model usage, instance store integration, and ledger emission.
  - `harnessiq/agents/provider_base/agent.py` adds the provider-backed agent scaffold.
  - Concrete harnesses live in `apollo`, `email`, `exa`, `exa_outreach`, `instagram`, `instantly`, `knowt`, `leads`, `linkedin`, `outreach`, `prospecting`, and `research_sweep`.
- `harnessiq/shared/`: authoritative shared types/constants/configs already used for manifests, credentials, provider metadata, some agent configs, and some durable-memory models.
- `harnessiq/providers/`: provider and model integration layer. The dominant patterns are:
  - service-provider REST surfaces with `api.py`, `client.py`, `operations.py`, and shared operation dataclasses in `harnessiq/shared/{provider}.py`
  - model-provider helpers/builders for OpenAI, Anthropic, Gemini, and Grok
- `harnessiq/tools/`: MCP-style tool factories. Many providers now have duplicated request-surface logic in both `providers/*/operations.py` and `tools/*/operations.py`.
- `harnessiq/cli/`: argparse entrypoints plus the platform-first adapter layer. `harnessiq/cli/commands/platform_commands.py` and `harnessiq/cli/commands/command_helpers.py` are the main orchestration boundary for persisted profiles, run snapshots, bound credentials, and adapter execution.
- `harnessiq/config/`: persisted profile/credential models and storage.
- `harnessiq/utils/`: agent instance registry, ledger/export/output-sink support, and storage utilities.

Current design conventions relevant to DTO work:

- The codebase already prefers immutable dataclasses with `frozen=True, slots=True` for shared contracts, for example `AgentRuntimeConfig`, `AgentModelRequest`, `HarnessRunSnapshot`, `HarnessProfile`, provider `*Credentials`, and provider `*Operation` / `*PreparedRequest` models.
- Shared definitions are meant to live in `harnessiq/shared/`, and the packaging tests (`tests/test_sdk_package.py`) enforce that shared configs/operations/errors originate from shared modules rather than agent/provider local modules.
- Despite that shared-definition convention, many layer boundaries still exchange raw `dict[str, Any]`, `Mapping[str, Any]`, or raw JSON-shaped objects instead of explicit DTOs.

Data flow through the relevant layers:

1. CLI commands resolve a manifest, build a `HarnessAdapterContext`, and persist `HarnessProfile` / `HarnessRunSnapshot` state.
2. CLI adapters read and write native harness state using raw dict runtime/custom payloads, then instantiate concrete agents.
3. Agents build raw instance payload dicts for `AgentInstanceStore`, construct tool registries, and return raw dict ledger outputs / metadata.
4. Provider tools accept raw `operation`, `path_params`, `query`, and `payload` arguments, coerce them into provider-specific prepared requests, then return raw dict tool outputs.
5. Model-provider helpers and clients accept / return raw lists and dicts representing provider-native payload shapes.

Concrete raw-boundary hotspots found during the survey:

- Agent instance payloads:
  - `BaseAgent.build_instance_payload()` returns `dict[str, Any]`.
  - Concrete helpers such as `harnessiq/agents/linkedin/helpers.py`, `harnessiq/agents/exa_outreach/helpers.py`, `harnessiq/agents/knowt/helpers.py`, and similar functions in `instagram`, `leads`, `prospecting`, and `research_sweep` build raw instance payload dicts.
  - `harnessiq/utils/agent_instances.py` persists `payload: dict[str, Any]` in `AgentInstanceRecord`.
- CLI adapter and command payloads:
  - `HarnessCliAdapter.load_native_parameters()` returns `tuple[dict[str, Any], dict[str, Any]]`.
  - `HarnessCliAdapter.show()` and `HarnessCliAdapter.run()` return raw JSON-safe dict payloads.
  - `HarnessAdapterContext.runtime_parameters` / `custom_parameters` are mutable dicts.
  - `_base_payload()` and other helpers in `harnessiq/cli/commands/command_helpers.py` construct nested raw dict response envelopes.
- Provider service surfaces:
  - Tool factories in `harnessiq/tools/*/operations.py` still accept raw `ToolArguments` and pass raw `path_params`, `query`, and `payload` mappings into provider clients.
  - Many provider clients still expose signatures such as `prepare_request(..., path_params: Mapping[str, object] | None, query: Mapping[str, object] | None, payload: Any | None)` and return `Any`.
  - The newer service providers already have useful shared dataclasses such as `ExaOperation` and `ExaPreparedRequest`, but the request/input boundary before those dataclasses remains raw.
- Model-provider request builders:
  - `harnessiq/providers/openai/client.py`, `anthropic/client.py`, `grok/client.py`, and `gemini/client.py` accept raw message/tool/config dicts and return `Any`.
  - Builder modules such as `harnessiq/providers/gemini/content.py` and `harnessiq/providers/anthropic/messages.py` are heavily dict-shaped.

Test strategy and constraints:

- The repo has broad unit coverage across agents, providers, CLI, and packaging.
- `tests/test_sdk_package.py` is especially relevant because it enforces that shared definitions originate from `harnessiq/shared/*`.
- `tests/test_platform_cli.py`, `tests/test_provider_base_agents.py`, and the per-provider suites give focused seams for DTO regression coverage.

Repository state risk observed during survey:

- The git working tree is dirty on branch `add-never-stop-master-prompt` with user changes across multiple agent files plus untracked memory artifacts. Any later implementation work must avoid overwriting those edits and will need careful preservation before syncing `main` for the worktree-based GitHub workflow.

### 1b: Task Cross-Reference

User request summary:

- Audit the agent code and inject the “explicit DTOs at layer boundaries” pattern.
- Put the DTO definitions in `harnessiq/shared/`.
- Audit the provider layer and define explicit DTOs through all relevant layers, explicitly mentioning providers, CLI, SDK, and related surfaces.
- Create tickets for the work and then implement them sequentially using the GitHub software engineering workflow.
- Use `artifacts/file_index.md` as a reference artifact.

Concrete mapping of the request to the repository:

Agent layer targets:

- `harnessiq/agents/base/agent.py`
  - Current boundary: raw dict instance payloads and raw dict ledger outputs / metadata.
  - Likely DTO candidates: agent instance payload DTOs, ledger output/metadata DTOs, or at minimum typed wrappers for persisted instance payloads.
- Concrete agent helpers and constructors:
  - `harnessiq/agents/linkedin/helpers.py`
  - `harnessiq/agents/exa_outreach/helpers.py`
  - `harnessiq/agents/knowt/helpers.py`
  - `harnessiq/agents/leads/helpers.py`
  - `harnessiq/agents/prospecting/helpers.py`
  - `harnessiq/agents/instagram/helpers.py`
  - `harnessiq/agents/research_sweep/agent.py`
  These currently build or consume raw persisted payload shapes and are the main places to inject explicit agent-boundary DTOs.
- Shared storage models already exist for some agent domains:
  - `harnessiq/shared/linkedin.py`
  - `harnessiq/shared/exa_outreach.py`
  - `harnessiq/shared/prospecting.py`
  - `harnessiq/shared/instagram.py`
  - `harnessiq/shared/leads.py`
  Those modules are the natural home for agent-specific DTOs when the boundary is domain-specific.

CLI layer targets:

- `harnessiq/cli/adapters/base.py`
- `harnessiq/cli/adapters/context.py`
- `harnessiq/cli/adapters/utils/payloads.py`
- `harnessiq/cli/commands/platform_commands.py`
- `harnessiq/cli/commands/command_helpers.py`
- `harnessiq/config/harness_profiles.py`

The CLI currently has three raw boundaries:

1. adapter-to-command payloads (`show()` / `run()` dicts)
2. profile/runtime/custom parameter transport (`dict[str, Any]`)
3. persisted run snapshot adapter arguments (`dict[str, Any]`)

Provider service layer targets:

- Tool-factory request boundaries in `harnessiq/tools/*/operations.py`
- Provider client request boundaries in `harnessiq/providers/*/client.py`
- Prepared request contracts already shared in modules like `harnessiq/shared/exa.py`, `harnessiq/shared/attio.py`, `harnessiq/shared/apollo.py`, etc.

The repeated request-shaping pattern is consistent enough that a foundational DTO set in `harnessiq/shared/` could cover:

- provider tool input/request envelopes
- provider prepared request envelopes
- provider tool result envelopes

with provider-specific DTOs layered on top only where necessary.

Model-provider targets:

- `harnessiq/shared/providers.py`
- `harnessiq/providers/base.py`
- `harnessiq/providers/openai/client.py`
- `harnessiq/providers/openai/requests.py`
- `harnessiq/providers/anthropic/client.py`
- `harnessiq/providers/anthropic/messages.py`
- `harnessiq/providers/gemini/client.py`
- `harnessiq/providers/gemini/content.py`
- `harnessiq/providers/grok/client.py`

These are the main SDK-facing provider APIs, and they currently expose raw provider-native lists/dicts rather than explicit request DTOs.

Public-package / SDK targets:

- `harnessiq/__init__.py`
- `harnessiq/agents/__init__.py`
- `harnessiq/providers/__init__.py`
- `harnessiq/shared/__init__.py`
- `tests/test_sdk_package.py`

If DTOs become part of the intended public SDK surface, exports and packaging tests will need to be updated deliberately.

What already exists that is relevant:

- The repo already uses explicit dataclasses successfully for many contracts (`AgentModelRequest`, `AgentRunResult`, `HarnessRunSnapshot`, provider credentials, provider operations, prepared requests).
- The main missing piece is not whether DTOs are acceptable, but which boundaries should be upgraded first and how far the public API should move away from raw dict compatibility.

What is missing and needs to be built:

- A shared DTO module strategy in `harnessiq/shared/` for cross-layer request/response envelopes.
- Agent-specific DTOs for persisted instance payloads and other agent boundary shapes.
- CLI DTOs for adapter context/result payloads and possibly runtime/custom parameter transport.
- Provider DTOs for service-provider tool inputs/results and model-provider request payloads.
- Regression tests that lock the new DTO behavior in place without breaking current public flows unintentionally.

Behavior that must likely be preserved:

- Existing CLI command JSON output shape unless the user explicitly wants a breaking change.
- Existing external constructor usability for agents/providers unless the user explicitly wants to expose DTO-first public APIs immediately.
- Existing packaging/shared-definition conventions enforced by `tests/test_sdk_package.py`.

Blast radius:

- Small if limited to introducing shared DTOs plus internal adapters that still accept/return dicts at the top-level public API.
- Very large if every provider client, CLI response, and public SDK constructor is converted to DTO-first signatures in one pass.

### 1c: Assumption & Risk Inventory

Unresolved assumptions embedded in the request:

1. “Inject this pattern into the agent classes” could mean:
   - define DTOs for persisted agent payloads and run/result envelopes while preserving current public constructor signatures, or
   - convert public agent constructors and helper APIs themselves to DTO-first contracts.
2. “Define these specific data transfer objects at all layers” could mean:
   - foundational DTO envelopes shared across layers, or
   - per-provider and per-agent request/response DTO classes for nearly every public operation.
3. “Create tickets for it, and then implement it sequentially” could mean:
   - create the full backlog but implement only the first ticket in this session, or
   - create and implement the entire backlog in this same session.
4. The correct shared placement is unresolved:
   - one central `harnessiq/shared/dtos.py`,
   - several focused shared modules such as `shared/agent_dtos.py`, `shared/provider_dtos.py`, `shared/cli_dtos.py`,
   - or provider/domain-specific DTOs placed in existing shared domain modules.
5. The acceptable compatibility policy is unresolved:
   - preserve current JSON/dict-shaped public behavior and add DTOs internally,
   - or change CLI/provider/SDK public methods to expose DTOs directly.

Primary implementation risks:

1. Ticket explosion risk: a strict per-provider/per-boundary DTO rollout across all agents, service providers, model providers, CLI adapters, and SDK exports is large enough that it must be decomposed carefully.
2. Over-design risk: forcing DTOs onto purely internal transformation helpers could add ceremony without improving boundary safety.
3. Breaking-change risk: the SDK and CLI have tests that currently assert dict-shaped outputs and builder inputs.
4. Inconsistency risk: some boundaries already have partial explicit models (`*PreparedRequest`, `HarnessRunSnapshot`, `AgentModelRequest`), so a careless rollout could introduce overlapping DTO concepts rather than a coherent boundary model.
5. Workflow risk: the required GitHub workflow assumes clean worktree creation from `main`, but the current checkout is dirty and not on `main`; that state can be handled, but only after the scope is clarified enough to justify opening implementation tickets.

Recommended implementation posture based on the survey:

- Treat this as a staged refactor.
- Start with shared foundational DTO primitives plus the highest-value repeated seams:
  - agent instance payload DTOs
  - CLI adapter/result DTOs
  - provider request/result DTO envelopes for service-provider tools
- Then layer model-provider DTOs and remaining public-surface adoption behind follow-on tickets.

Phase 1 complete
