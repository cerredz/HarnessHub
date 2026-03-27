### 1a: Structural Survey

- Repository type: Python SDK/package with the live runtime source under `harnessiq/` and tests under `tests/`.
- Bundled master prompt system:
  - Prompt assets live as JSON files under `harnessiq/master_prompts/prompts/`.
  - `harnessiq/master_prompts/registry.py` loads every `*.json` file in that package, derives the prompt key from the filename, and requires `title`, `description`, and `prompt` fields.
  - `harnessiq/master_prompts/__init__.py` exposes the public catalog API (`get_prompt`, `get_prompt_text`, `list_prompts`, `list_prompt_keys`, `has_prompt`).
  - `harnessiq/cli/master_prompts/commands.py` exposes the prompt catalog and activation commands through `harnessiq prompts`.
  - `harnessiq/master_prompts/session_injection.py` injects a selected bundled prompt into repo-local Claude/Codex instruction overlays using only the registry-provided metadata and prompt text.
- Packaging:
  - Prompt assets are shipped as package data from `harnessiq/master_prompts/prompts/*.json`, so adding one new JSON file in that directory is sufficient for runtime discovery.
- Test strategy:
  - `tests/test_master_prompts.py` is the primary contract test for prompt catalog membership, registry behavior, and section-shape validation.
  - `tests/test_master_prompts_cli.py` validates prompt listing, retrieval, and activation from the CLI surface.
  - `tests/test_master_prompt_session_injection.py` validates repo-local prompt activation using the registry.
- Repository conventions observed:
  - Prompt catalog membership is pinned by a hard-coded `EXPECTED_PROMPT_KEYS` set in `tests/test_master_prompts.py`.
  - `artifacts/file_index.md` is a generated architecture artifact; it should only change if the generator output changes materially.
  - Prior master-prompt additions in `memory/` use a task-local source prompt artifact to preserve exact prompt text during JSON packaging.

### 1b: Task Cross-Reference

- User request: add the supplied master prompt to the repository exactly as provided, using a name like `never_stop`.
- Concrete codebase mapping:
  - New prompt asset: `harnessiq/master_prompts/prompts/never_stop.json`.
  - Exact-text preservation artifact: `memory/add-master-prompt-never-stop/source_prompt.md`.
  - Catalog contract update: `tests/test_master_prompts.py` must include `never_stop` in `EXPECTED_PROMPT_KEYS`.
  - Task artifacts for this implementation: `memory/add-master-prompt-never-stop/`.
- Existing behavior to preserve:
  - Registry loading must remain filename-driven with no prompt-specific branching.
  - CLI list/show/text/activate behavior must remain generic.
  - The prompt body itself must remain exactly the user-supplied text once loaded from the JSON bundle.
- Blast radius:
  - Limited to the bundled prompt catalog and the tests that explicitly assert its membership.
  - No provider, agent, CLI parser, or session-injection logic should require changes.

### 1c: Assumption & Risk Inventory

- Assumption: `never_stop` is the intended key/filename because the user explicitly suggested that naming pattern and it matches repository conventions.
- Assumption: “Exactly as it is” applies to the prompt body text, not the required JSON wrapper metadata; a `title` and `description` still need to be authored for the catalog schema.
- Assumption: The supplied prompt should remain in markdown form inside the JSON `prompt` field, consistent with the rest of the bundled prompt catalog.
- Risk: Manual transcription could alter prompt text accidentally. Mitigation: store the supplied text in `memory/add-master-prompt-never-stop/source_prompt.md` and verify the bundled JSON prompt matches it exactly.
- Risk: JSON escaping for a large prompt body could break parsing if done carelessly. Mitigation: validate with the focused master-prompt test suites.
- Risk: The repository has unrelated untracked `memory/` state. Do not touch or stage unrelated local artifacts.

Phase 1 complete.
