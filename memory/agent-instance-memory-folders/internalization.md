### 1a: Structural Survey

Top-level architecture:
- `harnessiq/` is the shipped SDK package. Agent runtime code lives under `harnessiq/agents/`, shared datamodels under `harnessiq/shared/`, CLI entrypoints under `harnessiq/cli/`, and agent-agnostic persistence helpers under `harnessiq/utils/`.
- `memory/` is already used for durable runtime state and prior engineering artifacts. It is the natural root for a shared agent-instance registry plus instance-specific memory directories.
- `tests/` contains unit-style coverage for the base runtime, concrete harnesses, CLI commands, and some packaging/runtime smoke tests.

Relevant source layout:
- `harnessiq/agents/base/agent.py` is the generic agent loop. It currently owns name, runtime config, transcript handling, context reset, and tool execution, but it does not consistently own instance registration.
- `harnessiq/utils/agent_ids.py` and `harnessiq/utils/agent_instances.py` already define stable payload normalization, payload fingerprints, deterministic instance ids, and a filesystem-backed registry under `memory/agent_instances.json`.
- `harnessiq/agents/instagram/agent.py` and `harnessiq/agents/prospecting/agent.py` already assume a richer base-runtime contract with `instance_payload` and `repo_root`, but `BaseAgent` has not caught up to that contract.
- `harnessiq/agents/linkedin/agent.py`, `harnessiq/agents/exa_outreach/agent.py`, and `harnessiq/agents/knowt/agent.py` still resolve memory independently and do not yet feed stable instance payloads into the base runtime.
- `harnessiq/cli/*/commands.py` still resolve memory folders from agent-specific `memory/<agent-type>/<slug>` logic rather than a shared instance-aware resolver.

Technology and conventions:
- Python 3.11+, `argparse`, stdlib-heavy persistence helpers, `dataclass`-based models with explicit validation, JSON files written with `indent=2` and `sort_keys=True`.
- Filesystem-backed stores generally expose `prepare()`, `read_*`, and `write_*` methods.
- Public SDK APIs are re-exported from package `__init__.py` modules.

Current inconsistencies:
- The checked-in `BaseAgent` initializer does not accept `instance_payload` or `repo_root`, while two concrete agents already pass those arguments.
- `harnessiq/utils/__init__.py` does not export the instance-registry helpers, even though `harnessiq/agents/__init__.py` imports them from there.
- Default SDK memory paths for several agents still point inside the package tree instead of a stable per-instance directory under the repo `memory/` root.

### 1b: Task Cross-Reference

Task mapping:
- "whenever we run an agent I want to create an agent-id" maps to `harnessiq/agents/base/agent.py` plus the existing instance-registry helpers in `harnessiq/utils/agent_ids.py` and `harnessiq/utils/agent_instances.py`.
- "maybe put this somewhere in the base agent class" maps directly to `BaseAgent` public properties and constructor-time instance resolution.
- "save the agent id's somewhere with their parameters" maps to the existing registry file `memory/agent_instances.json`, surfaced through `AgentInstanceStore`.
- "each one of the agents should have a memory folder" maps to concrete harness constructors and CLI memory resolution.
- "there could theoretically be 100 of each of these and they each need their own memory folder" maps to changing SDK defaults from package-local singleton memory folders to per-instance folders under a shared root like `memory/agents/<agent_name>/<instance_id>/`.
- "all of our agents" maps to the concrete harnesses currently in the repo: LinkedIn, Instagram, Exa outreach, Knowt, and Google Maps prospecting.

Concrete files touched by this change:
- `harnessiq/agents/base/agent.py`: add instance registration, resolved memory-path ownership, and public instance metadata.
- `harnessiq/utils/__init__.py`: export the existing instance-registry helpers so the public package surface is coherent.
- `harnessiq/agents/linkedin/agent.py`: feed a deterministic payload into `BaseAgent` and build the memory store from the resolved instance path.
- `harnessiq/agents/exa_outreach/agent.py`: same for outreach payloads and resolved memory.
- `harnessiq/agents/knowt/agent.py`: same for Knowt, including config precedence.
- `harnessiq/agents/instagram/agent.py` and `harnessiq/agents/prospecting/agent.py`: align them with the finalized `BaseAgent` contract and any shared helper changes.
- `harnessiq/cli/instagram/commands.py`, `harnessiq/cli/linkedin/commands.py`, `harnessiq/cli/exa_outreach/commands.py`, and `harnessiq/cli/prospecting/commands.py`: surface resolved instance ids and ensure CLI-managed runs remain registered in the shared catalog.
- `tests/`: add or update tests for base-agent instance metadata, concrete agent default memory paths, and CLI outputs/compatibility.
- `artifacts/file_index.md`: update the architectural artifact to reflect the shared registry plus per-instance memory layout.

Behavior to preserve:
- Existing per-agent memory file schemas.
- Explicit `memory_path` overrides for SDK and CLI flows.
- Existing CLI ability to manage named memory folders before a run.

Blast radius:
- Medium. The runtime contract is shared by all agents, but the change is narrowly about instance identity and memory-path resolution rather than tool execution or prompt behavior.

### 1c: Assumption & Risk Inventory

Assumptions:
- Instance identity should remain deterministic for the same logical agent name plus normalized payload.
- Explicit `memory_path` values remain supported and should be recorded as the instance memory path rather than overwritten.
- The shared default instance layout should live under `memory/agents/<agent_name>/<instance_id>/`.
- CLI-managed named folders can remain compatible, but runs should still be recorded in the shared registry and expose the resolved `instance_id`.

Risks:
- Some constructor arguments are not serializable (`model`, tool objects, live clients). Payload builders must be explicit and include only stable configuration values.
- `KnowtAgent` accepts an injected config object that can override scalar constructor arguments. The payload must reflect the effective config, not the raw inputs alone.
- Including `memory_path` in payloads can intentionally create distinct instances for different explicit folders, but doing so for default SDK flows would defeat shared resolution. Payload builders must include it only when an explicit memory path is meaningfully part of the identity.
- Existing tests and package exports already show signs of partial work. The implementation should finish the shared contract cleanly rather than layering another parallel mechanism.

Phase 1 complete
