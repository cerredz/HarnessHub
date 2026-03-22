# Ticket 1: HTTP Transport Updates and Config Layer Foundation

## Title
Add `harnessiq/config/` credential layer and extend HTTP transport hostname map

## Intent
Two pieces of shared plumbing must exist before any of the six provider implementations can be built cleanly:
1. The `_infer_provider_name()` function in `harnessiq/providers/http.py` uses a hostname-based map to label `ProviderHTTPError` instances. All six new provider hostnames must be added here so error messages are correctly attributed.
2. The credential-config-loader (`harnessiq/config/`) was designed and clarified in prior work but never implemented. Each new provider needs a typed credential-config model and a `.env`-backed loader so callers can resolve credentials from the repo-local `.env` file instead of passing raw strings. This ticket creates the foundation; individual provider credential models are added per provider in their own tickets.

## Scope
**Creates:**
- `harnessiq/config/__init__.py`
- `harnessiq/config/loader.py` — `CredentialLoader`: reads `.env`, resolves named variables, raises on missing file or missing key
- `harnessiq/config/models.py` — base `ProviderCredentialConfig` TypedDict + abstract pattern for per-provider models (concrete models added per provider ticket)
- `tests/test_config_loader.py`

**Modifies:**
- `harnessiq/providers/http.py` — `_infer_provider_name()`: add hostname entries for all 6 new providers
- `harnessiq/__init__.py` — add `"config"` to `_EXPORTED_MODULES`
- `artifacts/file_index.md` — document `harnessiq/config/`

**Does not touch:** any existing provider module, any agent module, any existing test file.

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/config/__init__.py` | Create: exports CredentialLoader, ProviderCredentialConfig |
| `harnessiq/config/loader.py` | Create: CredentialLoader class |
| `harnessiq/config/models.py` | Create: ProviderCredentialConfig base TypedDict |
| `harnessiq/providers/http.py` | Modify: `_infer_provider_name()` hostname map |
| `harnessiq/__init__.py` | Modify: add `"config"` to `_EXPORTED_MODULES` |
| `artifacts/file_index.md` | Modify: add config and new provider folder entries |
| `tests/test_config_loader.py` | Create: CredentialLoader unit tests |

## Approach
**CredentialLoader:** A class (not a dataclass — it performs I/O) that:
- Accepts an optional `env_path: str | None = None` (defaults to `.env` in the current working directory)
- `load(key: str) -> str`: reads the `.env` file, resolves the named key, returns the value. Raises `FileNotFoundError` if `.env` does not exist. Raises `KeyError` with a clear message if the key is absent.
- `load_all(keys: Sequence[str]) -> dict[str, str]`: batch-load multiple keys; raises on the first missing key with the key name in the error message.
- `.env` parsing: line-by-line, strip whitespace, skip blank lines and `#`-prefixed comment lines, split on first `=`, strip surrounding quotes from values.
- No external dependencies (no `python-dotenv`). Stdlib only.

**ProviderCredentialConfig:** A simple `TypedDict` base — not instantiated directly, but imported by per-provider credential models to establish the pattern.

**`_infer_provider_name()` additions:**
```python
if "creatify" in host: return "creatify"
if "arcads" in host: return "arcads"
if "instantly" in host: return "instantly"
if "outreach" in host: return "outreach"
if "lemlist" in host: return "lemlist"
if "exa" in host: return "exa"
```

## Assumptions
- The `.env` file format is `KEY=VALUE`, one per line, with optional `#` comments and optional quote-wrapping of values.
- `CredentialLoader` is intentionally not a frozen dataclass — it performs file I/O and must not cache `.env` contents across multiple `load()` calls (keeps behavior predictable during tests).
- `ProviderCredentialConfig` is a TypedDict pattern anchor, not enforced at runtime. Each provider's concrete credential config is its own TypedDict defined in its own provider module.
- The `harnessiq/__init__.py` lazy-load mechanism (`__getattr__`) handles `"config"` with zero changes beyond adding it to `_EXPORTED_MODULES`.

## Acceptance Criteria
- [ ] `harnessiq/config/` is importable as `import harnessiq.config` and via `from harnessiq import config`
- [ ] `CredentialLoader().load("KEY")` returns the correct string value from a `.env` file
- [ ] `CredentialLoader().load("KEY")` raises `FileNotFoundError` when `.env` does not exist
- [ ] `CredentialLoader().load("MISSING")` raises `KeyError` with the missing key name in the message
- [ ] `CredentialLoader().load_all(["A", "B"])` raises on the first missing key
- [ ] `.env` values with surrounding single or double quotes are returned unquoted
- [ ] Blank lines and `#`-prefixed comment lines in `.env` are skipped without error
- [ ] `ProviderHTTPError` for a URL containing `creatify.ai` has provider `"creatify"`
- [ ] Same for `arcads`, `instantly`, `outreach`, `lemlist`, `exa`
- [ ] All existing tests continue to pass

## Verification Steps
1. `python -m pytest tests/test_config_loader.py -v` — all new tests pass
2. `python -m pytest tests/test_provider_base.py -v` — existing HTTP tests pass + new hostname assertions pass
3. `python -m pytest tests/ -v` — full suite green
4. `python -c "from harnessiq.config import CredentialLoader; print('ok')"` — import clean
5. `python -m py_compile harnessiq/config/loader.py harnessiq/config/models.py harnessiq/config/__init__.py` — no syntax errors

## Dependencies
None — this is the foundation ticket. All provider tickets (2–7) depend on this one.

## Drift Guard
This ticket must not implement any provider-specific credential models, any agent wiring, any CLI commands, or any changes to existing provider clients. The hostname map and config package foundation are the only deliverables.
