## SDK Agent Runtime Extensibility Internalization

### 1a: Structural Survey

#### Repository shape

- `harnessiq/` is the production SDK package and is already packaged through `pyproject.toml`.
- `docs/` and `README.md` describe public SDK usage patterns.
- `tests/` is the primary quality surface and uses `unittest`-style tests runnable through `pytest`.
- `artifacts/file_index.md` defines the architectural boundaries that new work must follow.
- `memory/` stores task artifacts from prior workstreams and is part of the repo workflow, not the shipped package.

#### Relevant architecture

- `harnessiq/agents/`
  - `base/agent.py` contains the shared runtime loop, instance registry integration, context reset/pruning logic, and ledger emission.
  - Concrete harnesses compose memory stores, prompts, and tools around `BaseAgent`.
  - Tool extension support is inconsistent across harnesses: some accept `tools=`, some accept specialized tool args such as `browser_tools=`, and several inline duplicate merge logic.

- `harnessiq/shared/`
  - Holds runtime dataclasses and cross-module definitions such as `AgentRuntimeConfig`, `AgentParameterSection`, and agent-specific memory/config models.
  - Multiple harnesses duplicate small parameter-rendering helpers instead of sharing one SDK helper.

- `harnessiq/tools/`
  - Contains executable tool runtime logic plus `ToolRegistry`.
  - `harnessiq/toolset/` already provides first-class custom-tool creation and registration through `define_tool()`, `tool()`, `register_tool()`, and `register_tools()`.
  - The missing piece is ergonomic propagation of those tools into concrete agents through a consistent constructor surface.

- `harnessiq/utils/`
  - Owns the agent instance registry and the framework audit ledger/output sink subsystem.
  - Sink construction currently supports only built-in sink kinds through hard-coded branching in `ledger_sinks.py`.
  - Users can inject an `OutputSink` instance directly through `AgentRuntimeConfig.output_sinks`, but they cannot register a new sink type and resolve it through `build_output_sinks()` / CLI sink specs.

#### Public documentation state

- `README.md`, `docs/agent-runtime.md`, `docs/tools.md`, and `docs/output-sinks.md` document the runtime, tool layer, and sink layer.
- Current docs explain built-in custom-tool creation via `toolset`, but they do not yet present a cohesive "define custom tool, inject into an agent, define custom sink, register it, and build it from specs" story.

#### Testing state

- `tests/test_agents_base.py` covers runtime behavior, sink emission, and tool inspection.
- `tests/test_output_sinks.py` covers built-in sink construction and spec parsing.
- `tests/test_toolset_factory.py` and `tests/test_toolset_registry.py` cover custom tool definition and registration.
- There is not yet coverage for custom sink registration or for consistent `tools=` injection across the agent surface.

### 1b: Task Cross-Reference

User request: update the SDK so it is current with the evolved agent/base-agent surface and gives users seamless helpers for payloads, memory-oriented parameter blocks, output sinks, audits/ledgers, and custom tool/sink injection.

Concrete codebase mapping:

- Base runtime and shared agent contracts:
  - `harnessiq/agents/base/agent.py`
  - `harnessiq/shared/agents.py`

- Tool runtime and SDK customization surface:
  - `harnessiq/tools/registry.py`
  - `harnessiq/tools/__init__.py`
  - `harnessiq/toolset/__init__.py`
  - concrete harness constructors in `harnessiq/agents/*/agent.py`

- Sink / audit / ledger extension surface:
  - `harnessiq/utils/ledger.py`
  - `harnessiq/utils/ledger_models.py`
  - `harnessiq/utils/ledger_sinks.py`
  - `harnessiq/utils/ledger_connections.py`
  - `harnessiq/utils/__init__.py`

- Public SDK exports and documentation:
  - `harnessiq/agents/__init__.py`
  - `README.md`
  - `docs/agent-runtime.md`
  - `docs/output-sinks.md`
  - `docs/tools.md`

- Verification surface:
  - `tests/test_agents_base.py`
  - `tests/test_output_sinks.py`
  - `tests/test_toolset_factory.py`
  - `tests/test_toolset_registry.py`
  - targeted agent tests for constructors whose tool injection surface changes

Current gaps relative to the request:

- Custom sinks are injectable only as already-instantiated objects, not as first-class SDK-registered sink types.
- Tool injection into concrete agents is not standardized across the agent catalog.
- Small but repeated agent-runtime helpers such as tool merging and parameter-section JSON rendering are private and duplicated instead of public SDK helpers.
- The docs do not yet show an end-to-end customization story spanning custom tools, custom sinks, and agent runtime configuration.

Behavior that must be preserved:

- Existing built-in sink kinds and sink-spec syntax.
- Existing toolset behavior, especially `define_tool()` / `register_tool()` semantics.
- Existing concrete harness defaults and backward-compatible constructor arguments.
- Existing audit-ledger behavior: sinks remain post-run only and must not participate in the agent loop.

### 1c: Assumption & Risk Inventory

#### Assumptions

- The user wants additive SDK ergonomics rather than a redesign of per-agent memory-store internals.
- Backward compatibility matters: existing constructor arguments such as `browser_tools` and `email_tools` should keep working.
- Custom sink support should integrate with the current `build_output_sinks()` / sink-spec flow, not just with raw `OutputSink` object injection.
- A small shared helper surface for durable parameter sections is sufficient to cover the "memory / run memory" part of the request without inventing a new generic memory-store abstraction.

#### Risks

- Changing constructor signatures across several agents can create subtle import or behavior regressions if defaults shift.
- Sink registration must reject collisions with built-ins clearly; otherwise users could accidentally shadow framework sinks.
- Adding helper APIs without using them in the concrete harnesses would leave the SDK still feeling fragmented.
- The base runtime file contains at least one likely gap (`build_context_window()` calls `_transcript_entry_to_context_entry()` but the helper is not currently defined as an instance method), so adjacent runtime cleanup may be required during implementation.

#### Clarification status

- No blocking ambiguities remain for implementation.
- Proceeding with additive SDK helpers that keep current behavior intact while standardizing extensibility.

Phase 1 complete.
