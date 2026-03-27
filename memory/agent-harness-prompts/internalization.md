### 1a: Structural Survey

**Repository shape**
- `harnessiq/` is the live Python package; `pyproject.toml` packages `harnessiq*` and bundles prompt assets explicitly.
- `harnessiq/agents/` holds concrete harness packages plus the generic `BaseAgent` runtime in `harnessiq/agents/base/`.
- `harnessiq/shared/` owns cross-layer contracts: manifests, config dataclasses, file-backed memory stores, DTOs, tool constants, and validation.
- `harnessiq/tools/` owns executable tool definitions/registries. Tools are deterministic local handlers; model orchestration stays in agents.
- `harnessiq/master_prompts/` bundles JSON master-prompt assets with a registry that resolves prompts by filename-derived key.
- `tests/` is `unittest`-based and already covers agents, manifests, master prompts, tools, providers, and context-window behavior.

**Agent/runtime conventions**
- Concrete harnesses subclass `BaseAgent`, wire a model plus `ToolRegistry`, and expose durable state through `load_parameter_sections()`.
- Durable file-backed state belongs in a matching `harnessiq/shared/<domain>.py` module, not inside the concrete agent module.
- Reusable harness metadata is declared through `HarnessManifest` instances in `harnessiq/shared/*` and registered in `harnessiq/shared/harness_manifests.py`.
- Public exports are centralized through `harnessiq/agents/__init__.py` and `harnessiq/shared/__init__.py`.

**Existing orchestration patterns**
- `ResearchSweepAgent` is the closest reset-safe orchestration pattern: it constrains context tools, persists state in memory files, and lets the model mutate durable memory through explicit context tools.
- `GoogleMapsProspectingAgent` is the closest typed multi-call pattern: it uses a `JsonSubcallRunner` seam and `_run_json_subcall()` to turn targeted model calls into validated JSON artifacts for deterministic downstream logic.
- Base-agent context tools already support model subcalls (`run_model_subcall`) for summarization/compaction, but there is no first-class generic tool for arbitrary typed sub-agent orchestration yet.

**Test and packaging conventions**
- Tests usually use fake `AgentModel` implementations that capture `AgentModelRequest` objects and return scripted `AgentModelResponse` values.
- Shared contracts are tested directly through focused shared/tool tests plus concrete harness tests.
- Packaged prompts are verified through `tests/test_master_prompts.py`, and manifest registration is verified through `tests/test_harness_manifests.py`.

**Relevant inconsistencies / constraints**
- There is no existing concrete harness built from bundled master prompts alone; current agents either load Markdown prompts from their package or JSON prompts from the prompt registry, but not both.
- DTO usage exists (`harnessiq/shared/dtos/`) but is still sparse; most shared contracts are dataclasses in domain modules rather than DTO packages.
- The repo has context-tool subcalls and direct JSON subcalls, but no single shared abstraction for “run a typed LLM worker stage and persist its artifact.”

### 1b: Task Cross-Reference

**User request to codebase mapping**
- “Create two reusable agent harness classes” maps to two new concrete packages under `harnessiq/agents/`, each with an `agent.py` and package `__init__.py`.
- “Translate these master prompts into a harness” maps to new orchestration logic that breaks each prompt into smaller deterministic stages instead of exposing the raw prompt as one monolithic system prompt.
- “Mission Driven Master prompt ... represent the different artifacts of this prompt” maps to a new shared mission-state contract and memory store under `harnessiq/shared/`, with explicit files for mission definition, task plan, memory store, decisions, progress log, test results, artifacts, checkpoints, and README narrative.
- “Spawn sub-agents harness ... orchestrator master prompt, assign tasks to different llm calls with the correct context and connect them via tool calling” maps to a harness that plans work locally, emits bounded worker assignments, runs worker/synthesis subcalls, and records orchestration state durably.
- “If you need to add tools in our tooling layer feel free” maps to `harnessiq/tools/` and `harnessiq/shared/tools.py`. The likely need is a generic typed JSON subcall/orchestration helper or narrowly-scoped orchestration tools if current seams are insufficient.
- “Create contracts ... input data that we need in the shared folder according to the file index” maps to new `harnessiq/shared/<domain>.py` modules containing manifests, config dataclasses, memory store classes, and normalizers.
- “Create interfaces if necessary in the interfaces folder that we have, create DTOs for these agents” maps to `harnessiq/interfaces/` and `harnessiq/shared/dtos/`. These are only necessary if the new orchestration introduces a reusable boundary that is not already captured by existing `AgentModel` / tool protocols.

**Likely affected runtime files**
- New shared domain modules:
  - `harnessiq/shared/mission_driven.py`
  - `harnessiq/shared/spawn_subagents.py`
  - possibly new DTO modules under `harnessiq/shared/dtos/`
- New agent packages:
  - `harnessiq/agents/mission_driven/`
  - `harnessiq/agents/spawn_subagents/`
- Registry/export updates:
  - `harnessiq/shared/harness_manifests.py`
  - `harnessiq/shared/__init__.py`
  - `harnessiq/agents/__init__.py`
- Potential tooling additions:
  - `harnessiq/shared/tools.py`
  - one or more files under `harnessiq/tools/`
- Tests:
  - focused agent tests for each harness
  - shared/manifests tests for new contracts and registry entries

**Existing behavior that must be preserved**
- No regressions to current harness manifests, exports, or built-in tool keys.
- Existing master-prompt registry stays asset-centric; the new harnesses should consume prompt assets without changing prompt-registry behavior.
- `BaseAgent` remains the core run loop; the new harnesses should fit its model/tool/transcript contract rather than bypass it.

**Blast radius**
- Moderate. This adds two first-class harnesses, new shared contracts, and likely new tool constants/helpers, but should remain isolated if manifests/exports/tests are updated carefully.
- Highest-risk areas are manifest registration, new durable-memory file layout, and any generic JSON subcall helper that touches shared tooling.

### 1c: Assumption & Risk Inventory

1. **First-class harness assumption**: I am assuming these agents should be first-class built-in harnesses with `HarnessManifest` entries, because the file index explicitly treats reusable harness metadata as shared-layer source of truth. Risk: if the user only wanted importable classes and not registry entries, this adds more surface area than required.

2. **CLI surface assumption**: I am assuming explicit CLI adapters/commands are not required for this task, because the user asked for reusable harness classes and shared contracts, not end-user CLI flows. Risk: the harnesses will be programmatically reusable and inspectable via manifests, but not immediately runnable from top-level CLI commands unless added later.

3. **Typed subcall strategy assumption**: I am assuming the safest existing pattern is to use the prospecting-style JSON subcall seam for deterministic worker stages, optionally factored into shared helpers, rather than creating a model-calling tool that recursively invokes the live agent loop. Risk: if the user expected subcalls to be exposed as model-visible tools instead of internal helper methods, the implementation may be more structured than they intended.

4. **Mission artifact scope assumption**: I am assuming the mission-driven harness should materialize the prompt’s full storage layout as real files in `memory/<mission>/`, not only store a compressed subset in `context_runtime_state.json`, because the prompt explicitly treats those files as the durable contract. Risk: this creates a larger shared contract than a lighter-weight memory-field approach.

5. **Interface necessity assumption**: I am assuming new `interfaces/` modules are only warranted if a new reusable boundary appears during implementation. Today `AgentModel` plus tool protocols already cover the core runtime contract, so forcing extra interfaces may add indirection without value.

6. **GitHub skill workflow risk**: The requested skill normally implies ticket decomposition artifacts and potentially remote issue/PR workflow. The code changes themselves do not require remote GitHub mutation, so the implementation work should stay safely local unless a later step clearly requires issue creation.

**Phase 1 complete.**
