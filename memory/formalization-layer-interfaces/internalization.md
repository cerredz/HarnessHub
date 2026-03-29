### 1a: Structural Survey

The authoritative runtime code lives under `harnessiq/`, per [artifacts/file_index.md](/C:/Users/422mi/HarnessHub/artifacts/file_index.md). The package is organized by runtime responsibility: `agents/` owns orchestration and run loops, `tools/` owns deterministic operations, `providers/` wrap external systems, `shared/` holds reusable DTOs and runtime types, and `interfaces/` exposes SDK-facing dependency seams.

The current `harnessiq.interfaces` package is flat and intentionally lightweight. Existing modules are:

- `harnessiq/interfaces/models.py`: runtime-checkable model-client protocols.
- `harnessiq/interfaces/provider_clients.py`: request-preparation and execution contracts.
- `harnessiq/interfaces/output_sinks.py`: sink delivery contracts.
- `harnessiq/interfaces/tool_selection.py`: dynamic tool-selection and embedding contracts.
- `harnessiq/interfaces/cli.py`: callable-based CLI loader contracts.

Public exports are centralized in [harnessiq/interfaces/__init__.py](/C:/Users/422mi/HarnessHub/harnessiq/interfaces/__init__.py). Top-level `harnessiq/__init__.py` exports the `interfaces` module lazily as part of the SDK surface.

The agent runtime is centered on [harnessiq/agents/base/agent.py](/C:/Users/422mi/HarnessHub/harnessiq/agents/base/agent.py) and [harnessiq/agents/base/agent_helpers.py](/C:/Users/422mi/HarnessHub/harnessiq/agents/base/agent_helpers.py). `BaseAgent` currently has durable parameter sections, transcript/reset management, tool execution, hook execution, context tools, dynamic tool selection, and snapshot support. There is no existing formalization-layer concept in the runtime loop, but there are already adjacent concepts that a future formalization system could shape:

- `build_system_prompt()` and `_effective_system_prompt()` for system-prompt composition.
- `load_parameter_sections()` and `_compose_parameter_sections()` for durable context-window sections.
- `_resolve_active_tool_keys()` for model-visible tool narrowing.
- `reset_context()` for deterministic reset boundaries.
- `prepare()` and `snapshot()` as pre-run assembly points.

The test strategy is unittest-first. Public interface coverage already exists in [tests/test_interfaces.py](/C:/Users/422mi/HarnessHub/tests/test_interfaces.py), which validates exports, flat package structure, and protocol runtime-checkability. Base-agent behavior is covered heavily in [tests/test_agents_base.py](/C:/Users/422mi/HarnessHub/tests/test_agents_base.py). This suggests the safest path is to add one new interface module, export it, and extend `tests/test_interfaces.py` with self-contained tests for the new public contracts.

Conventions observed:

- Module docstrings are short and explicit.
- Public interfaces include concise docstrings on classes and methods.
- `__all__` is maintained carefully.
- The repository currently tolerates light dataclass use in shared/public layers.
- Existing interface files prefer minimal dependencies and avoid binding to concrete runtime implementations.

### 1b: Task Cross-Reference

The user asked for a minimal change to the interfaces folder and SDK that introduces self-documenting formalization layer abstractions. Mapped to the codebase, that means:

- [harnessiq/interfaces/__init__.py](/C:/Users/422mi/HarnessHub/harnessiq/interfaces/__init__.py): must export the new contracts to the SDK-facing package.
- New file [harnessiq/interfaces/formalization.py](/C:/Users/422mi/HarnessHub/harnessiq/interfaces/formalization.py): should house the new base class and typed abstract bases.
- [tests/test_interfaces.py](/C:/Users/422mi/HarnessHub/tests/test_interfaces.py): should validate exports and the default self-documenting behavior.

Relevant existing runtime shapes that inform the interface design, but should not be modified in this change:

- [harnessiq/shared/agents.py](/C:/Users/422mi/HarnessHub/harnessiq/shared/agents.py): provides `AgentParameterSection` and related types that the formalization layer should use for context-window rendering.
- [harnessiq/agents/base/agent.py](/C:/Users/422mi/HarnessHub/harnessiq/agents/base/agent.py): exposes the runtime hook points that the formalization abstraction should name and document.
- [harnessiq/agents/base/agent_helpers.py](/C:/Users/422mi/HarnessHub/harnessiq/agents/base/agent_helpers.py): shows how system prompts, parameter sections, tool availability, and resets are currently composed.

What currently exists that is relevant:

- An interface package for SDK-facing contracts.
- Shared agent runtime types for parameter sections and tool visibility.
- Tests that assert the `interfaces` package stays flat and public.

What is missing:

- Any formalization-layer abstraction.
- Any self-documenting layer record/type for rules and descriptions.
- Any typed formalization bases for contracts, artifacts, hooks, stages, state, roles, or tool contributions.

Behavior that must be preserved:

- Existing exports from `harnessiq.interfaces`.
- Existing interface-package flat-file convention.
- Existing agent runtime behavior, because this task should not integrate the new interfaces into execution yet.

Blast radius:

- Low if constrained to the new module, exports, and tests.
- Medium only if runtime types or base-agent execution are modified, which this task should avoid.

### 1c: Assumption & Risk Inventory

1. Assumption: the user wants public abstract base classes, not only runtime-checkable protocols.
Why it matters: the requested self-documenting defaults require concrete shared behavior, which strongly favors ABCs.
Resolution: treat this as confirmed by the conversation’s repeated references to abstract classes with default helper methods.

2. Assumption: “some of the base formalization layer objects” means a focused subset of typed base layers, not every typed layer from the design document.
Why it matters: implementing all seven typed layers would expand scope and increase review surface.
Resolution: implement the common base plus a representative subset tied directly to the user’s explicit examples, such as contracts, artifacts, hooks, stages, and state.

3. Risk: adding runtime integration now would couple an unfinished public API to `BaseAgent` behavior and broaden the change beyond the user’s stated minimal scope.
Mitigation: keep the new module interface-only and document the future runtime hook intent in docstrings and method names.

4. Risk: overfitting the new abstractions to imagined runtime details rather than current repository shapes.
Mitigation: reuse existing runtime types like `AgentParameterSection` and name hook methods after actual BaseAgent lifecycle seams already present in the repo.

5. Risk: the worktree is already dirty in unrelated files.
Mitigation: modify only scoped files needed for this task and do not regenerate broad docs or touch unrelated tracked changes.

Phase 1 complete.
