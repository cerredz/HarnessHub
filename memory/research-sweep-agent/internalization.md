### 1a: Structural Survey

HarnessHub is a Python 3.11 SDK/CLI repository centered on the live `harnessiq/` package. `pyproject.toml` exposes a single `harnessiq` console entrypoint, and the generated `artifacts/file_index.md` establishes the repository standard that `harnessiq/` is the only authoritative runtime source tree while `build/`, `src/`, and packaging residue are non-authoritative. The runtime architecture is split cleanly:

- `harnessiq/shared/` owns stable data definitions, harness manifests, provider operation metadata, and durable memory-store classes.
- `harnessiq/agents/` owns orchestration logic. Concrete harnesses subclass `BaseAgent` or a provider-specialized base and are expected to keep orchestration concerns separate from provider/tool execution.
- `harnessiq/tools/` owns executable tool factories. Provider-backed integrations are exposed here and ultimately delegate into `harnessiq/providers/`.
- `harnessiq/providers/` owns external service clients and operation catalogs.
- `harnessiq/cli/` owns two CLI layers: a platform-first manifest-driven surface (`prepare`, `show`, `run`, `inspect`, `credentials`) and several harness-specific top-level command families (`outreach`, `instagram`, `linkedin`, `prospecting`, `leads`).
- `tests/` provides unit coverage over agents, manifests, providers, tools, CLI entrypoints, packaging, and the generated docs.
- `scripts/sync_repo_docs.py` regenerates `README.md`, `artifacts/commands.md`, `artifacts/file_index.md`, and `artifacts/live_inventory.json` from live code.

The core runtime contract lives in [`harnessiq/agents/base/agent.py`](../../harnessiq/agents/base/agent.py). `BaseAgent` persists instance identity via `AgentInstanceStore`, loads durable parameter sections through `load_parameter_sections()`, keeps a rolling transcript, and automatically resets the transcript when estimated token pressure crosses `runtime_config.reset_threshold * max_tokens`. Durable context-tool state is stored in `context_runtime_state.json` under the agent memory path and survives `reset_context()` calls. The generic context tool family is designed around this runtime state and is already capable of write-once, overwrite, append, bulk-write, handoff, and summarization behaviors.

The manifest layer in [`harnessiq/shared/harness_manifest.py`](../../harnessiq/shared/harness_manifest.py) and [`harnessiq/shared/harness_manifests.py`](../../harnessiq/shared/harness_manifests.py) is the authoritative registration mechanism for built-in harnesses. Each manifest declares:

- identity (`manifest_id`, `agent_name`, `display_name`, import path)
- CLI wiring (`cli_command`, `cli_adapter_path`)
- default memory root
- typed runtime/custom parameters
- declared durable memory files
- provider families
- output schema

The platform-first CLI in [`harnessiq/cli/platform_commands.py`](../../harnessiq/cli/platform_commands.py) consumes manifests directly. New manifests automatically appear under `harnessiq prepare/show/run/inspect/credentials` if a CLI adapter exists. Provider credentials are managed through `credentials bind/show/test`, not by embedding API keys in harness-specific config files.

Harness-specific top-level CLIs are separate hand-authored modules under `harnessiq/cli/<harness>/commands.py`. They typically expose `prepare`, `configure`, `show`, and `run`, backed by a harness-native memory store under `harnessiq/shared/<harness>.py`. This direct CLI layer is more user-friendly than the platform-first surface and often persists prompt/config text into dedicated memory files. There is already a consistent pattern for this in outreach, instagram, linkedin, and prospecting.

The repo’s conventions are stable:

- shared modules define dataclasses, defaults, manifests, and memory-store helpers
- agents orchestrate; they do not embed raw HTTP provider logic
- provider-backed tools are created through `harnessiq.tools.*` factories
- durable memory is first-class and explicitly surfaced in manifests
- tests expect packaging exports, manifest registration, platform CLI registration, and generated docs to stay in sync

Inconsistencies worth noting because they affect this task:

- direct harness CLIs and the platform CLI coexist; not every harness has both
- some direct CLIs use credential factories at run time while the platform CLI uses stored credential bindings
- `BaseAgent` automatically renders a generic `Context Memory` section title, but this design doc wants an agent-specific `Research Sweep Memory` section title and flattened schema
- the current generic `context.inject.handoff_brief` tool is less specialized than the design doc’s desired orientation brief

### 1b: Task Cross-Reference

The requested `ResearchSweepAgent` spans every major integration seam that the repo uses for first-class harnesses:

1. SDK agent implementation
   - Add a new concrete agent package under `harnessiq/agents/research_sweep/`.
   - Export the agent from `harnessiq/agents/__init__.py`.
   - Implement a `BaseAgent` subclass that:
     - composes a minimal tool surface from Serper plus a restricted subset of context tools
     - persists durable sweep state in BaseAgent’s context runtime state
     - renders the master prompt as a static parameter section
     - emits durable outputs/metadata for the final report

2. Shared manifest and memory/config surface
   - Add `harnessiq/shared/research_sweep.py` for constants, config dataclass, memory-store helpers, manifest declaration, and normalization helpers.
   - Register the manifest in `harnessiq/shared/harness_manifests.py`.
   - Export the manifest from `harnessiq/shared/__init__.py`.
   - Decide which native files exist alongside `context_runtime_state.json` so the direct CLI has a stable configure/show surface.

3. Provider/tool composition
   - Use `harnessiq/providers/serper` and `harnessiq/tools/serper` rather than bespoke HTTP logic.
   - Use the existing context tool implementations, but restrict them to the eight tool keys required by the design doc.
   - Potentially adapt or wrap context tool behavior where the design doc needs agent-specific semantics without breaking other harnesses.

4. Platform-first CLI
   - Add `harnessiq/cli/adapters/research_sweep.py`.
   - The manifest registration will cause the harness to appear under:
     - `harnessiq prepare research_sweep`
     - `harnessiq show research_sweep`
     - `harnessiq run research_sweep`
     - `harnessiq inspect research_sweep`
     - `harnessiq credentials bind/show/test research_sweep`

5. Direct top-level CLI
   - Add `harnessiq/cli/research_sweep/commands.py`.
   - Register it in `harnessiq/cli/main.py`.
   - Expose a user-friendly `harnessiq research-sweep ...` flow matching the repo’s existing direct command families.

6. Tests
   - Manifest registry tests: new manifest must be registered and discoverable.
   - Platform CLI tests: new harness must appear in manifest-driven commands and credential binding surfaces.
   - Direct CLI tests: parser registration plus prepare/configure/show/run behavior.
   - Agent tests: parameter sections, tool restriction, durable state handling, report/error outputs, and resume semantics.
   - Packaging tests: SDK exports must include the new agent and manifest as appropriate.
   - Docs sync tests: generated docs must be regenerated after manifest/CLI additions.

7. Generated docs and repo artifacts
   - Run `python scripts/sync_repo_docs.py` so README and artifacts reflect the new harness/CLI command paths.

Blast radius:

- `harnessiq/shared/*` manifest registry and exports
- `harnessiq/agents/*` exports plus a new agent package
- `harnessiq/cli/*` main registration, new adapter, new direct command family
- generated docs and inventory artifacts
- multiple focused test modules

What already exists and should be preserved:

- BaseAgent’s reset and durable runtime-state mechanics
- provider credential binding architecture for the platform-first CLI
- Serper provider/tool factories
- generated documentation workflow
- file-index standard that shared manifest metadata, not ad hoc CLI parsing, is the source of truth for typed parameter rules

What is net-new:

- the research sweep harness itself
- its manifest, CLI adapter, direct CLI family, shared memory/config helpers, and tests

### 1c: Assumption & Risk Inventory

1. The design doc’s pseudocode is not a perfect reflection of the live API surface.
   - `create_context_tools(..., allowed_keys=...)` does not exist in the repo.
   - The generic `context.inject.handoff_brief` tool schema does not currently accept query/completed-count/next-site arguments.
   - The live implementation must realize the same design intent with the repo’s actual primitives.

2. The repo’s credential architecture conflicts with the design doc’s CLI example that passes `serper_api_key` as a custom parameter.
   - Repo convention strongly prefers provider credential bindings (`harnessiq credentials bind`) or explicit credential factories.
   - Introducing raw API-key custom params would cut across an established pattern and the file index explicitly discourages ad hoc provider wiring.
   - The implementation should preserve provider-family-based credentials for the platform CLI and can make the direct CLI ergonomic without weakening that model.

3. The design doc requires the durable parameter section title `Research Sweep Memory`, while `BaseAgent` defaults to a generic `Context Memory` section whenever context runtime state is present.
   - This likely requires a subclass override of the parameter-section composition path so the agent surfaces the requested title and flattened schema.

4. The repo is currently dirty on `main`, and `main` is ahead of `origin/main`.
   - The feature work must not absorb unrelated local user edits or unpublished commits into the PR.
   - The implementation branch should be isolated from the remote default branch state rather than blindly branching from the dirty checkout.

5. The user asked for a single PR into `main`.
   - The skill workflow suggests ticket decomposition and issue creation per ticket, but waiting for merges between dependent tickets is incompatible with finishing this request end-to-end in one session.
   - The cleanest path is a single implementation ticket and one PR for the full harness integration.

6. The direct CLI name in the design doc is `research-sweep`, while manifest IDs elsewhere use underscores.
   - The repo supports both a manifest ID and a CLI alias pattern, so the direct CLI can use the hyphenated user-facing name while the manifest remains `research_sweep`.

7. The design doc expects up to three resets without data loss, but deterministic validation of multi-reset behavior inside unit tests will require either a stub model or focused state-transition tests rather than real token-pressure runs.
   - The test suite should verify the durable-state contract and resume semantics, not attempt a fully realistic external-search run.

Phase 1 complete.
