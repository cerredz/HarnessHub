# One Way Guide

This artifact gives repeated repository decisions a default answer.

It is the contributor-facing guide for work that already has a canonical shape in Harnessiq. Use it when you are adding a new extension point and want the default path instead of inventing a fresh pattern.

If this guide conflicts with a concrete public contract, preserve the public contract. If it conflicts with an older implementation detail, follow the guide for new work.

## Default Map

| If you are adding... | Default home | Canonical references |
| --- | --- | --- |
| a third-party provider | `harnessiq/providers/<provider>/` plus public tool export from `harnessiq/tools/<provider>/` | `harnessiq/providers/apollo/`, `harnessiq/tools/apollo/`, `harnessiq/providers/arxiv/`, `harnessiq/tools/arxiv/` |
| a built-in tool family | `harnessiq/tools/` plus toolset registration when users should discover it by family | `harnessiq/tools/general_purpose.py`, `harnessiq/tools/context_compaction.py`, `harnessiq/toolset/catalog_builtin.py` |
| a new agent harness | `harnessiq/agents/<agent>/` with shared state in `harnessiq/shared/<agent>.py` and manifest wiring when it is public | `harnessiq/agents/linkedin/`, `harnessiq/shared/linkedin.py`, `harnessiq/agents/leads/`, `harnessiq/shared/leads.py`, `harnessiq/shared/harness_manifest.py` |
| durable memory | file-backed store in `harnessiq/shared/<domain>.py` plus runtime instance registration via `BaseAgent` | `harnessiq/shared/linkedin.py`, `harnessiq/shared/leads.py`, `harnessiq/shared/instagram.py`, `harnessiq/utils/agent_instances.py` |
| runtime parameters | explicit schemas and normalization near the owning harness state or manifest | `harnessiq/shared/linkedin.py`, `harnessiq/shared/prospecting.py`, `harnessiq/shared/harness_manifest.py`, `harnessiq/cli/leads/commands.py` |
| artifact updates | `artifacts/` plus generator updates and rerun when the artifact should surface in generated docs | `artifacts/file_index.md`, `artifacts/commands.md`, `scripts/sync_repo_docs.py` |

## Core Rules

1. Agents orchestrate. Tools execute deterministic operations. Providers wrap external systems. Utilities own cross-cutting runtime infrastructure.
2. Shared state belongs in `harnessiq/shared/`. If a concept survives resets, is loaded into parameter sections, or is needed by both the harness and CLI, it does not belong inline in an agent module.
3. Agents reach external systems through tools, not through ad hoc provider or HTTP calls embedded in the harness.
4. If a tool family should be user-discoverable, wire it through `harnessiq/toolset/`.
5. Durable memory is a product surface. File names, JSON shapes, and parameter-section semantics should be changed deliberately.
6. Generated docs are contracts too. If you add a maintained artifact or change a structural default, update the generator inputs and rerun the generator.

## Add A Provider

Default answer: put provider internals under `harnessiq/providers/<provider>/` and expose the executable factory from `harnessiq/tools/<provider>/`.

Expected files:

- `harnessiq/providers/<provider>/credentials.py`: typed credentials with constructor validation.
- `harnessiq/providers/<provider>/api.py`: URL, header, and request-shape helpers.
- `harnessiq/providers/<provider>/client.py`: authenticated execution client.
- `harnessiq/providers/<provider>/operations.py`: operation catalog, request preparation, and the canonical `create_<provider>_tools()` path when the provider owns that preparation logic.
- `harnessiq/providers/<provider>/requests.py`: optional request-body and query builders when payload normalization is non-trivial.
- `harnessiq/providers/<provider>/__init__.py`: public provider exports.
- `harnessiq/tools/<provider>/__init__.py`: public tool-layer export for `create_<provider>_tools()`.
- `harnessiq/tools/<provider>/operations.py`: only when the executable layer has meaningful behavior beyond a thin re-export.

Required follow-through:

- Add the family to `harnessiq/toolset/catalog_provider.py`.
- Add tests for credentials, client behavior, operation catalog behavior, and tool-factory behavior.
- Export the public provider or tool surface from package `__init__.py` files when it is intended for SDK users.

Copy this pattern:

- Credentialed service provider: `harnessiq/providers/apollo/` plus `harnessiq/tools/apollo/`
- Credential-free provider family: `harnessiq/providers/arxiv/` plus `harnessiq/tools/arxiv/`

Do not:

- Call provider clients directly from an agent.
- Skip the public tool-layer export and force callers to import deep provider internals.
- Invent a provider-specific handler shape that does not return `tuple[RegisteredTool, ...]`.

## Add A Tool Family

First decide which family you are adding:

- Built-in deterministic family with no credentials: implement it in `harnessiq/tools/`.
- Provider-backed family: follow the provider flow above and register it in `harnessiq/toolset/catalog_provider.py`.
- Harness-internal family for one agent or domain: put it under `harnessiq/tools/<agent_or_domain>/` and import it into the harness constructor.

Built-in family checklist:

- Create the module or package in `harnessiq/tools/`.
- Return `tuple[RegisteredTool, ...]` from the factory.
- Export the factory from `harnessiq/tools/__init__.py` if it is public SDK surface.
- Register it in `harnessiq/toolset/catalog_builtin.py` if users should discover it through `get_family()` or `list_tools()`.
- Add focused tests for definitions, validation, and execution behavior.

Canonical references:

- Built-in multi-key family: `harnessiq/tools/general_purpose.py`
- Runtime-significant compaction family: `harnessiq/tools/context_compaction.py`
- Single-tool built-in family in the catalog: `harnessiq/tools/instagram/operations.py`
- Harness-specific composed family: `harnessiq/tools/leads/operations.py`

Do not:

- Leave non-trivial tool definitions embedded in an agent module.
- Register a family in the catalog if it is not intended to be user-discoverable.
- Let a tool family own durable-state schemas that belong in `harnessiq/shared/`.

## Add A New Agent Harness

Default answer: create a dedicated package in `harnessiq/agents/<agent>/`, keep prompts on disk, keep durable models in `harnessiq/shared/<agent>.py`, inherit from `BaseAgent`, and add manifest wiring if the harness is part of the public platform-first CLI.

Required pieces:

- `harnessiq/agents/<agent>/agent.py`: orchestration layer.
- `harnessiq/agents/<agent>/__init__.py`: package-level exports for the intended public surface.
- `harnessiq/agents/<agent>/prompts/master_prompt.md`: prompt asset loaded from disk.
- `harnessiq/shared/<agent>.py`: config dataclasses, durable-memory types, filename constants, and normalization helpers.
- `harnessiq/tools/<agent>/` or `harnessiq/tools/<domain>/`: internal executable tools when the harness needs them.
- `tests/test_<agent>_agent.py` plus any supporting shared/CLI/tool tests.

If the harness should appear in the public manifest and CLI layer, also update:

- `harnessiq/shared/harness_manifest.py`: typed manifest schema.
- `harnessiq/shared/harness_manifests.py`: built-in manifest registry.
- `harnessiq/cli/platform_commands.py` and the platform adapters indirectly driven by the manifest surface.

Harness rules:

- Implement `build_instance_payload()` so the shared instance registry can resolve stable ids and memory paths.
- Load prompts from files, not embedded multi-hundred-line strings.
- Keep `load_parameter_sections()` reset-safe. If the model needs it after a transcript reset, read it from durable memory there.
- Compose tools in the constructor. Do not make the harness reach directly into provider transport code.
- Re-export the harness from `harnessiq/agents/__init__.py` when it is intended to be public SDK surface.

Copy this pattern:

- File-backed harness with runtime parameters and managed files: `harnessiq/agents/linkedin/agent.py` with `harnessiq/shared/linkedin.py`
- Rotating multi-ICP harness with domain-specific internal tools: `harnessiq/agents/leads/agent.py` with `harnessiq/tools/leads/operations.py` and `harnessiq/shared/leads.py`
- Prompt-plus-file pipeline harness: `harnessiq/agents/knowt/agent.py` with `harnessiq/shared/knowt.py`

Do not:

- Put config dataclasses, filename constants, or normalization helpers in the agent module.
- Treat a harness as a singleton by default; the runtime already supports per-instance ids and memory paths.
- Assume transcript state survives resets.

## Model Durable Memory

Default answer: model durable memory as a file-backed store in `harnessiq/shared/<domain>.py` with explicit filename constants, constructor-validated records, a `prepare()` method, and deterministic `read_*` / `write_*` helpers.

Memory design rules:

- Persist only state that must survive process restarts or context resets.
- Give each durable file one clear responsibility.
- Prefer append-only logs for audit trails and explicit records for current state.
- Keep JSON stable and deterministic instead of relying on loosely-typed blobs.
- Make `load_parameter_sections()` reconstruct prompt-visible state directly from the memory store.
- Let `BaseAgent` resolve and register the memory path; do not invent a second instance registry.

Canonical references:

- Mixed text, JSON, JSONL, and managed files: `harnessiq/shared/linkedin.py`
- Rich per-ICP run state and search compaction: `harnessiq/shared/leads.py`
- Simpler JSON-backed discovery memory: `harnessiq/shared/instagram.py`
- Shared instance registry and default memory layout: `harnessiq/utils/agent_instances.py`

Do not:

- Store important workflow state only in Python instance fields.
- Allow prompt-visible state to drift away from the durable files the agent is supposed to trust.
- Hide schema changes inside tools without updating the owning shared module and its tests.

## Add Runtime Parameters

Default answer: runtime parameters are explicit, enumerated, and normalized. Add a supported-key constant or schema entry, add a normalization path, persist them in the owning state store, and surface them in parameter sections when they influence model behavior.

Workflow:

1. Decide whether the value is truly runtime behavior or user/domain content.
2. Add the supported key to the owning `SUPPORTED_*_RUNTIME_PARAMETERS` tuple or manifest runtime-parameter schema.
3. Extend the matching normalization path with strict coercion.
4. Persist the values in the harness memory store or CLI-managed runtime-parameter file.
5. Thread the normalized values into harness construction and `AgentRuntimeConfig` or manifest-driven config as appropriate.
6. Add tests for valid coercion, invalid keys, and invalid value types.

Prefer this placement:

- Put normalization in `harnessiq/shared/<domain>.py` when the CLI and harness both need the same rules.
- Use manifest schemas in `harnessiq/shared/harness_manifest.py` when the parameter surface is part of the manifest-driven public harness contract.
- Keep CLI modules thin; they should parse assignments and call the normalization path, not re-encode domain rules.

Canonical references:

- Shared runtime-parameter normalization: `harnessiq/shared/linkedin.py`, `harnessiq/shared/prospecting.py`
- Manifest-driven parameter schemas: `harnessiq/shared/harness_manifest.py`
- CLI-managed runtime/config split: `harnessiq/cli/leads/commands.py`
- Runtime parameters surfaced to the model as parameter sections: `harnessiq/agents/linkedin/agent.py`, `harnessiq/agents/prospecting/agent.py`

Do not:

- Accept arbitrary runtime keys.
- Parse types differently in configure vs run flows.
- Leave model-relevant runtime settings out of parameter sections when the harness expects the model to honor them.

## Write Artifact Updates When Architecture Changes

Default answer: update the artifact that matches the change, and update generator inputs when the artifact should be discoverable through generated docs.

Use this rule:

- Add or update files in `artifacts/` for maintained contributor-facing repo guidance.
- Update `scripts/sync_repo_docs.py` when the new artifact should appear in generated docs like `README.md` or `artifacts/file_index.md`.
- Rerun `python scripts/sync_repo_docs.py` after changing generator inputs.
- Keep `artifacts/commands.md` and `artifacts/file_index.md` generated; do not hand-edit generated outputs without changing the generator source.
- Use `docs/` for SDK-user-facing guidance rather than contributor-facing repository conventions.

Do not:

- Hide architecture changes in README-only prose.
- Add a maintained artifact without deciding whether it should appear in generated docs.
- Use `artifacts/` as a dumping ground for transient notes that belong in `memory/`.

## Minimum Review Checklist

Before merging repeated-pattern work, confirm:

- The dependency direction still matches the current package layout and codebase standards.
- Shared state moved into `harnessiq/shared/` instead of accreting inside an agent or CLI module.
- Public tool discovery is wired through `harnessiq/tools/` and `harnessiq/toolset/` when appropriate.
- Durable memory and parameter sections are reset-safe.
- Tests cover the new public seam, not just one happy-path implementation.
- Generated docs were rerun if you changed generator inputs.
