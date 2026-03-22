# Ticket 2: Add master_prompts module with registry and first prompt

## Intent
Add `harnessiq/master_prompts/` as a new SDK module that bundles curated system prompts (called "master prompts") as JSON files. The module exposes a typed Python API so users can load any master prompt by key and inject it into agents or their own API calls. The first bundled prompt is the "create master prompts" workflow prompt.

## Scope
**Changes:**
- Create `harnessiq/master_prompts/` package with `registry.py` and `__init__.py`
- Create `harnessiq/master_prompts/prompts/` directory containing JSON prompt files
- Add `create_master_prompts.json` as the first prompt
- Expose `master_prompts` in the top-level `harnessiq` package lazy loader
- Write unit tests
- Update `artifacts/file_index.md`

**Does not touch:**
- Agents, tools, providers, config, CLI — all unchanged
- Existing tests — unchanged

## Relevant Files
- CREATE `harnessiq/master_prompts/__init__.py` — public API: `MasterPrompt`, `MasterPromptRegistry`, `get_prompt()`, `list_prompts()`, `get_prompt_text()`
- CREATE `harnessiq/master_prompts/registry.py` — `MasterPrompt` frozen dataclass and `MasterPromptRegistry` implementation
- CREATE `harnessiq/master_prompts/prompts/create_master_prompts.json` — first master prompt
- MODIFY `harnessiq/__init__.py` — add `"master_prompts"` to `_EXPORTED_MODULES`
- CREATE `tests/test_master_prompts.py` — unit tests
- MODIFY `artifacts/file_index.md` — document new layout

## Approach
`MasterPrompt` is a frozen dataclass with `key: str`, `title: str`, `description: str`, `prompt: str`. `MasterPromptRegistry` discovers JSON files in the `prompts/` directory relative to the registry module via `importlib.resources` (stdlib, compatible with installed packages). The key is the JSON filename without the `.json` extension. Module-level convenience functions `get_prompt(key)`, `list_prompts()`, and `get_prompt_text(key)` delegate to a lazily-instantiated shared registry. All public symbols are re-exported from `__init__.py`. The `harnessiq/__init__.py` lazy-load mechanism requires only adding `"master_prompts"` to `_EXPORTED_MODULES`.

## Assumptions
- JSON prompt files must be included in the installed package. `pyproject.toml` already has `include-package-data = true` and a `setuptools.packages.find` rule that picks up `harnessiq*`. A `package_data` entry ensures `.json` files under `harnessiq/master_prompts/prompts/` are bundled.
- Key derivation from filename (no `.json` extension) is the single source of truth — the JSON file itself contains only `title`, `description`, and `prompt`.
- `get_prompt(key)` raises `KeyError` with a descriptive message when the key is not found; it does not return `None`.

## Acceptance Criteria
- [ ] `from harnessiq.master_prompts import get_prompt, list_prompts, get_prompt_text, MasterPrompt, MasterPromptRegistry` all work
- [ ] `import harnessiq; harnessiq.master_prompts.get_prompt("create_master_prompts")` works via lazy loader
- [ ] `get_prompt("create_master_prompts")` returns a `MasterPrompt` with non-empty `title`, `description`, and `prompt` fields
- [ ] `get_prompt_text("create_master_prompts")` returns the raw prompt string directly
- [ ] `list_prompts()` returns a list containing at least one `MasterPrompt` entry
- [ ] `get_prompt("nonexistent_key")` raises `KeyError`
- [ ] All unit tests pass

## Verification Steps
1. `python -m pytest tests/test_master_prompts.py -v` — all tests pass
2. `python -m pytest tests/ -x -q` — full suite passes
3. `python -c "from harnessiq.master_prompts import get_prompt; p = get_prompt('create_master_prompts'); print(p.title)"` — prints the title

## Dependencies
Ticket 1 (optional — these are independent; can be developed in parallel or sequentially).

## Drift Guard
This ticket must not modify any agent, tool, provider, config, or CLI module. It must not add any dependencies outside the Python standard library. The master prompts module is a read-only bundle — it does not write files, interact with the network, or mutate any shared state.
