### 1a: Structural Survey

The repository is a Python package centered on `harnessiq/`, with runtime behavior split across clear layers:

- `harnessiq/agents/` contains concrete harness implementations and shared agent runtime primitives.
- `harnessiq/tools/` contains tool registries, tool factories, and built-in tool surfaces.
- `harnessiq/providers/` contains provider adapters, HTTP clients, request builders, and service operation catalogs.
- `harnessiq/master_prompts/` contains the bundled master prompt catalog, the registry used to load it, and session-injection helpers that expose prompts to Claude Code and Codex.
- `tests/` contains focused regression suites for the public SDK, CLI, agent behavior, and bundled prompt catalog.
- `docs/` contains user-facing documentation for runtime features, including the prompt session injection workflow.

The prompt subsystem relevant to this task is intentionally file-driven:

- `harnessiq/master_prompts/prompts/*.json` are the source-of-truth bundled prompt assets.
- `harnessiq/master_prompts/registry.py` auto-discovers `.json` files and materializes each into a `MasterPrompt` dataclass using `title`, `description`, and `prompt` fields.
- `harnessiq/master_prompts/__init__.py` exposes the public API used by the SDK and tests.
- `harnessiq/master_prompts/session_injection.py` renders the active prompt into repo-local instruction overlays.
- `tests/test_master_prompts.py` hard-codes the expected bundled prompt key set and enforces the section-structure contract for bundled prompts.
- `tests/test_master_prompt_session_injection.py` verifies that injected project guidance includes the selected prompt text.
- `tests/test_master_prompts_cli.py` verifies the CLI prompt catalog surfaces bundled prompt metadata correctly.

The packaging path is already configured to ship prompt JSON files:

- `pyproject.toml` includes `[tool.setuptools.package-data] "harnessiq.master_prompts.prompts" = ["*.json"]`.

That means adding a new JSON prompt file in the prompts package is sufficient for runtime discovery and packaging. No registry table, manifest, or setup changes are needed unless a test assumes a fixed key set.

The repository contains existing task artifacts under `memory/`, including several prior master prompt additions. Those show the local workflow convention but do not change the runtime path: the product code for this task still lives in `harnessiq/master_prompts/prompts/` with test coverage in `tests/test_master_prompts.py`.

### 1b: Task Cross-Reference

User request: create a new master prompt exactly from the provided prompt body beginning with `Identity / Persona` and the persona description `You are a cognitive multiplexer ...`.

Concrete codebase mapping:

- `harnessiq/master_prompts/prompts/`
  - Target directory for the new bundled prompt JSON asset.
- `harnessiq/master_prompts/registry.py`
  - Existing discovery mechanism that will pick up the new prompt automatically. This file should remain unchanged unless the request unexpectedly requires nonstandard loading behavior.
- `tests/test_master_prompts.py`
  - Must be updated to include the new bundled prompt key in the expected catalog and to add prompt-specific assertions where useful.
- `tests/test_master_prompts_cli.py`
  - Existing CLI catalog coverage should pass without direct edits because it is count/key driven, but it is part of the blast radius for verification.
- `tests/test_master_prompt_session_injection.py`
  - Existing session injection tests should continue to pass because they exercise shared prompt retrieval and overlay rendering.
- `docs/master-prompt-session-injection.md`
  - No content change expected, but the docs surface is adjacent because it describes how bundled prompts are exposed.
- `memory/create-new-master-prompt/`
  - Task artifacts required by the workflow.

Relevant existing behavior to preserve:

- Bundled prompt loading must remain auto-discovered from the prompt package directory.
- The public API contract for `get_prompt`, `get_prompt_text`, `list_prompts`, and `list_prompt_keys` must remain unchanged.
- Shared section-structure tests for standard prompts must continue to pass.
- Existing prompts and catalog ordering must remain alphabetical by key.

What is net-new:

- One prompt JSON file for the new bundled prompt.
- Test expectations for the new prompt key and likely one direct content assertion validating the requested persona text survived intact.

Blast radius:

- Low. This is an additive asset change plus test updates.
- The highest behavioral risk is not code breakage but fidelity drift: accidentally modifying the user-provided prompt body instead of preserving it exactly.

### 1c: Assumption & Risk Inventory

Assumptions:

- The intended deliverable is a new bundled master prompt in the prompt catalog, not a replacement of an existing prompt.
- “Exactly” applies to the provided prompt body, while the surrounding JSON metadata can be inferred from repository conventions.
- The inferred prompt slug can be `cognitive_multiplexer`, with title `Cognitive Multiplexer`.
- The prompt should use the exact section names the user provided, including `Identity / Persona`, which is already allowed by the existing special handling for nonstandard structure in `tests/test_master_prompts.py`.

Ambiguities:

- The user did not specify the exact prompt key, title, or one-paragraph description required by the bundled JSON format.
- The user did not explicitly say whether this prompt should be listed in docs, but the repository’s prompt catalog is auto-discovered and CLI-driven, so bundling it implies listing everywhere the catalog is surfaced.

Risks:

- If the prompt body is altered during JSON escaping or normalization, the deliverable will violate the “exactly” requirement.
- If the new prompt key is not added to the expected test set, prompt catalog tests will fail.
- If the prompt is treated as a standard seven-section prompt in tests even though it begins with `Identity / Persona`, the structural assertions could become brittle.
- The current repository root is dirty with unrelated untracked `memory/` work, so implementation must be isolated from that state before branching and pushing.

Mitigations:

- Preserve the prompt body verbatim when creating the JSON file, only adding the required JSON metadata wrapper.
- Extend `tests/test_master_prompts.py` deliberately for the new prompt key and direct prompt-content checks instead of relying only on shared structure assertions.
- Implement in a clean worktree from `origin/main` rather than from the current working tree.

Phase 1 complete.
