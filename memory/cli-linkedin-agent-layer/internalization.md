### 1a: Structural Survey

Repository shape:

- `harnessiq/` is the production Python package. It is already the renamed main source layer the user alluded to; there is no separate `src/` directory anymore.
- `harnessiq/agents/` contains the provider-agnostic agent runtime (`BaseAgent`) plus concrete harnesses such as `LinkedInJobApplierAgent` and `BaseEmailAgent`.
- `harnessiq/shared/` holds reusable dataclasses, protocols, constants, and typed aliases that are shared across package layers.
- `harnessiq/tools/` implements the executable tool runtime, built-in tool families, and the `ToolRegistry`.
- `harnessiq/providers/` contains provider-facing transport and message translation helpers, but the current task does not need to modify provider integrations unless a CLI eventually wires in a model adapter.
- `docs/` contains lightweight usage documentation for tools and agents.
- `tests/` uses `unittest` and package-level smoke tests; there is no pytest-specific configuration in the repository.
- `artifacts/file_index.md` is the maintained architecture index and should be updated if a new top-level structural folder is added under the package.
- `memory/` contains prior workflow artifacts from earlier repository tasks.

Technology and execution model:

- Python 3.11+ package built with `setuptools` from `pyproject.toml`.
- The codebase prefers standard-library primitives, dataclasses, protocols, small helper functions, and explicit constructor injection.
- Testing is via `python -m unittest`; there is no configured linter or dedicated type checker visible at the repository root.
- The package public API is curated through `__init__.py` re-exports.

Current architecture conventions:

- New cross-cutting runtime concepts are introduced as additive package subfolders under `harnessiq/` and then exported deliberately.
- Shared definition-only types live in `harnessiq/shared/`, while executable logic lives in domain packages such as `harnessiq/agents/` and `harnessiq/tools/`.
- File and path behavior is explicit and usually implemented with `pathlib.Path`.
- Validation is lightweight but deterministic, with clear exceptions for invalid configuration or arguments.
- Tests are behavior-oriented and generally instantiate real runtime objects with fake injected collaborators.

Relevant existing LinkedIn behavior:

- `harnessiq/agents/linkedin.py` already owns the LinkedIn durable memory model through `LinkedInMemoryStore`.
- `LinkedInMemoryStore.prepare()` bootstraps `job_preferences.md`, `user_profile.md`, `agent_identity.md`, `applied_jobs.jsonl`, `action_log.jsonl`, and a `screenshots/` directory.
- `LinkedInJobApplierAgent` already exposes configurable runtime parameters such as `memory_path`, `max_tokens`, `reset_threshold`, `action_log_window`, `linkedin_start_url`, `notify_on_pause`, and `pause_webhook`.
- Browser-facing LinkedIn tool definitions already include an `upload_file` browser tool, but there is no human-facing CLI for collecting files or parameter values.

Notable gaps and inconsistencies relevant to this task:

- There is no `harnessiq/cli/` package, no `__main__.py`, and no console-script entrypoint in `pyproject.toml`.
- The package currently documents Python import usage only; it does not document or test any command-line experience.
- The LinkedIn agent’s durable input model is text-file based, but the user request implies a richer CLI experience for collecting files plus custom parameters.
- The phrase "inside of the main src layer" is outdated relative to the current repo shape, so path and packaging choices need to align to `harnessiq/`, not `src/`.

### 1b: Task Cross-Reference

User request mapping:

- "add a cli layer inside of the main src layer" maps to a new `harnessiq/cli/` package inside the existing main package, not a new top-level directory.
- "add a subfolder in the cli folder for the linkedin agent" maps to something like `harnessiq/cli/linkedin/` that encapsulates LinkedIn-specific command handling and argument parsing.
- "The user should be able to add upload files/information about the types of job they are looking for in relation to the linkedin agent" maps to CLI commands or options that can populate the LinkedIn durable memory inputs and potentially stage user-supplied files for later browser uploads.
- "and also define/input custom parameters into the cli layer" maps to a CLI surface for setting runtime configuration values beyond the default LinkedIn memory files, but the exact parameter set is ambiguous.

Concrete code locations likely affected:

- `harnessiq/cli/` as a new package for the CLI layer.
- `harnessiq/cli/linkedin/` as the LinkedIn-specific CLI package.
- `harnessiq/agents/linkedin.py` if the current memory store needs new helper methods for CLI-driven file ingestion or structured parameter persistence.
- `harnessiq/shared/linkedin.py` if the CLI introduces new durable LinkedIn-specific config filenames or a typed config object.
- `harnessiq/__init__.py` only if the package should publicly expose the CLI module, though a CLI can remain internal.
- `pyproject.toml` if the CLI should be installable via a console-script entrypoint.
- `tests/` for new CLI behavior coverage and any LinkedIn memory-store extensions.
- `docs/linkedin-agent.md` and/or `README.md` for CLI usage examples.
- `artifacts/file_index.md` because `harnessiq/cli/` would be a meaningful structural addition.

Behavior that should be preserved:

- Existing `LinkedInJobApplierAgent` constructor behavior and durable memory bootstrapping should remain backward compatible for import-based SDK consumers.
- Existing LinkedIn memory file names and prompt injection behavior should keep working unless the user explicitly wants the file contract changed.
- The CLI should layer on top of the SDK rather than bypassing or duplicating the current LinkedIn memory-store logic.

Blast radius:

- Moderate. The CLI itself is additive, but durable input handling can leak into `LinkedInMemoryStore` and documentation.
- Packaging changes may affect installation and smoke tests if a console script is introduced.
- The largest design risk is choosing the wrong boundary between free-form user data files, runtime parameters, and agent memory files.

### 1c: Assumption & Risk Inventory

Ambiguities that require clarification:

- It is unclear whether the CLI should only manage LinkedIn memory/config files, or whether it should also instantiate and run `LinkedInJobApplierAgent`.
- "upload files" could mean storing local document paths for future browser automation, copying files into the LinkedIn memory directory, or immediately driving the browser upload tool. Those are materially different implementations.
- "custom parameters" could mean existing `LinkedInAgentConfig` runtime fields, arbitrary user-defined key/value metadata, prompt sections, or browser/tool runtime overrides.
- It is unclear whether the user wants a single command with many flags, a nested subcommand structure, or an interactive prompt flow.

Implementation assumptions if not clarified:

- The CLI should live under `harnessiq/cli/` and be package-native.
- LinkedIn-specific CLI behavior should compose with `LinkedInMemoryStore` instead of inventing a parallel persistence system.
- Runtime configuration should remain file-based where practical so the agent can still be used outside the CLI.

Risks and edge cases:

- If the CLI stores file paths only, later browser upload actions may break when run from a different machine or working directory.
- If the CLI copies uploaded files into memory storage, there needs to be a defined naming and update strategy to avoid collisions and stale references.
- If custom parameters are fully arbitrary, the runtime needs a stable schema or serialization format so the agent can consume them deterministically.
- If a console entrypoint is added, packaging tests likely need to expand so the new CLI surface is covered in wheel/sdist smoke tests.

Phase 1 complete
