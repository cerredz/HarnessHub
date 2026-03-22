# Ticket 2 — Post-Critique Notes

## Observations

1. **`importlib.resources.files` with Path fallback** — Using `resources.files("harnessiq.master_prompts.prompts")` is the correct modern approach for locating package data. The `Path(__file__).parent / "prompts"` fallback ensures the module works in environments where the resources API behaves unexpectedly. Both paths produce identical results in the intended usage.

2. **Lazy module-level registry** — The shared `_registry` is initialized on first call and reused thereafter. This is the correct pattern: no module-level IO at import time, no repeated disk reads across calls.

3. **`prompts/` as a subpackage** — Adding `__init__.py` to the `prompts/` directory is required for `importlib.resources.files` to locate it as a package resource. Without it, the resources API cannot traverse into the directory in some distribution layouts. Correct.

4. **`pyproject.toml` `package-data` entry** — `"harnessiq.master_prompts.prompts" = ["*.json"]` is the minimal, correct declaration. This ensures JSON files are included in `sdist` and `wheel` distributions. Correct.

5. **`_cache: dict[str, MasterPrompt] | None`** — Using `None` sentinel for uninitialized state and `dict` once loaded is idiomatic. The `_load_all` method checks before re-loading. Correct.

6. **`get()` error message includes available keys** — When a key is not found, the `KeyError` message lists available keys. This is a meaningful improvement to developer experience over a bare `KeyError(key)`. Correct.

7. **`__init__.py` module docstring includes usage examples** — The module docstring shows three ways to access prompts. This is the right place for it — SDK users reading `help(harnessiq.master_prompts)` see it immediately.

## Issues Found and Resolved
None.
