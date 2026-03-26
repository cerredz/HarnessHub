### 1a: Structural Survey

- Repository type: Python SDK/package with editable-install workflow defined in `pyproject.toml`.
- Authoritative runtime tree: `harnessiq/`. Generated/reference repo docs live under `artifacts/` and `docs/`.
- Master prompt system:
  - Prompt assets live as JSON files under `harnessiq/master_prompts/prompts/`.
  - `harnessiq/master_prompts/registry.py` loads every `*.json` file via `importlib.resources`, derives the prompt key from the filename, and expects each JSON document to contain `title`, `description`, and `prompt`.
  - `harnessiq/master_prompts/__init__.py` exposes public API helpers (`get_prompt`, `get_prompt_text`, `list_prompts`, `list_prompt_keys`, `has_prompt`) backed by one shared lazy registry.
  - `harnessiq/cli/master_prompts/commands.py` exposes `harnessiq prompts {list,show,text,activate,current,clear}` on top of the registry/session helpers.
  - `harnessiq/master_prompts/session_injection.py` activates a selected bundled prompt into repo-local instruction overlays for Claude/Codex; it relies only on prompt key/title/description/prompt content, so adding a new prompt asset should flow through automatically.
- Packaging:
  - `pyproject.toml` includes `harnessiq.master_prompts.prompts = ["*.json"]`, so any new JSON prompt asset in that directory ships automatically without extra manifest edits.
- Test strategy:
  - `tests/test_master_prompts.py` is the primary contract test for the master-prompt catalog, registry, public API, and prompt section structure.
  - `tests/test_master_prompts_cli.py` validates CLI discovery and prompt retrieval behavior.
  - `tests/test_master_prompt_session_injection.py` validates prompt activation into project instruction overlays.
- Repository conventions observed:
  - Tests are written with `unittest` and `pytest`.
  - Prompt catalog membership is currently asserted by a hard-coded `EXPECTED_PROMPT_KEYS` set, so adding a new prompt requires synchronizing those tests.
  - `artifacts/file_index.md` is a generated, high-signal architecture reference and should be treated as source-of-truth context, not hand-edited unless the generator output materially changes.

### 1b: Task Cross-Reference

- User request: add the provided master prompt to the repo exactly as-is and name it `mission_driven`.
- Concrete codebase mapping:
  - New bundled prompt asset: `harnessiq/master_prompts/prompts/mission_driven.json`.
  - Prompt catalog contract updates: `tests/test_master_prompts.py` must include `mission_driven` in the expected key set so the catalog assertions remain correct.
  - No registry code changes appear necessary because prompt discovery is filename-driven and package-data shipping is already wildcard-based.
  - No CLI or session-injection code changes appear necessary because both are registry-driven and should surface the new prompt automatically.
- Existing behavior to preserve:
  - The prompt registry must continue loading all bundled prompts from package resources.
  - The CLI must continue listing and showing prompts without any key-specific branching.
  - The prompt body must remain exactly the user-supplied text inside the JSON `prompt` field.
- Blast radius:
  - Limited to the bundled prompt catalog and tests that pin its membership.
  - No runtime agent/provider/tool behavior should change except that a new prompt becomes discoverable/activatable.

### 1c: Assumption & Risk Inventory

- Assumption: “Call it `mission_driven`” means the prompt key/filename should be `mission_driven.json`. This matches the repository’s filename-derived key convention.
- Assumption: “Exactly as it is” applies to the prompt body text, not the surrounding JSON metadata. A title and description still need to be authored because the catalog schema requires them.
- Assumption: The supplied prompt already satisfies the repository’s required prompt section tests because it includes the core section markers in order.
- Risk: Manual transcription into JSON could accidentally alter punctuation, whitespace, or headings inside the prompt body. Mitigation: preserve the supplied text verbatim inside the JSON string.
- Risk: The prompt body contains markdown separators and long content; malformed JSON escaping would break loading. Mitigation: validate by running the focused master-prompt test suite.
- Risk: The repo has unrelated untracked files in `harnessiq/agents/*/helpers.py`. Do not touch or stage them.

Phase 1 complete.
