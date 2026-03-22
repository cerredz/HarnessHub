# Ticket 1: Config Layer Foundation and HTTP Transport Updates

## Title
Add `harnessiq/config/` credential layer and extend `_infer_provider_name()` for all 8 new providers

## Intent
Two pieces of shared plumbing must exist before any provider implementation can be built cleanly:
1. `harnessiq/config/` — a credential loader that resolves named env vars from a repo-local `.env` file. Every new provider's credentials object references this layer.
2. `_infer_provider_name()` in `harnessiq/providers/http.py` — hostname-based map that labels `ProviderHTTPError` instances. All 8 new provider hostnames must be added so errors are correctly attributed.

## Scope
**Creates:**
- `harnessiq/config/__init__.py`
- `harnessiq/config/loader.py` — `CredentialLoader` class
- `harnessiq/config/models.py` — `ProviderCredentialConfig` base TypedDict
- `tests/test_config_loader.py`

**Modifies:**
- `harnessiq/providers/http.py` — `_infer_provider_name()`: add hostname entries for all 8 providers
- `harnessiq/__init__.py` — add `"config"` to `_EXPORTED_MODULES`
- `artifacts/file_index.md` — document `harnessiq/config/` and note all 8 new provider packages

**Does not touch:** any existing provider module, any agent module, any existing test.

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/config/__init__.py` | Create: exports `CredentialLoader`, `ProviderCredentialConfig` |
| `harnessiq/config/loader.py` | Create: `CredentialLoader` class |
| `harnessiq/config/models.py` | Create: `ProviderCredentialConfig` base TypedDict |
| `harnessiq/providers/http.py` | Modify: `_infer_provider_name()` hostname map (additive only) |
| `harnessiq/__init__.py` | Modify: add `"config"` to `_EXPORTED_MODULES` |
| `artifacts/file_index.md` | Modify: register new packages |
| `tests/test_config_loader.py` | Create: `CredentialLoader` unit tests |

## Approach

**`CredentialLoader`** — a plain class (not a dataclass, it performs I/O):
- Constructor: `__init__(self, env_path: str | None = None)` — defaults to `.env` in `os.getcwd()`
- `load(key: str) -> str` — reads `.env`, parses, returns value. Raises `FileNotFoundError` if `.env` absent. Raises `KeyError` if key missing.
- `load_all(keys: Sequence[str]) -> dict[str, str]` — batch load; raises on first missing key.
- `.env` parsing: line-by-line, `str.strip()`, skip empty + `#`-prefixed lines, `split("=", 1)`, strip surrounding `'` or `"` from value. No external deps.
- Does NOT cache `.env` contents between calls (predictable test behavior).

**`ProviderCredentialConfig`** — a `TypedDict` base (annotation-only pattern anchor):
```python
class ProviderCredentialConfig(TypedDict):
    """Base type for per-provider credential configuration."""
```
Concrete sub-TypedDicts are defined per provider in `credentials.py` within each provider package.

**`_infer_provider_name()` additions:**
```python
if "snov.io" in host or "snovio" in host:  return "snovio"
if "leadiq" in host:                        return "leadiq"
if "salesforge" in host:                    return "salesforge"
if "phantombuster" in host:                 return "phantombuster"
if "zoominfo" in host:                      return "zoominfo"
if "peopledatalabs" in host:                return "peopledatalabs"
if "nubela" in host or "proxycurl" in host: return "proxycurl"
if "coresignal" in host:                    return "coresignal"
```

**`harnessiq/__init__.py`:** Find the `_EXPORTED_MODULES` tuple/list and add `"config"` to it.

## Assumptions
- `.env` format is `KEY=VALUE` one per line with optional `#` comments and optional quote-wrapping of values.
- `CredentialLoader` re-reads the file on every call (no caching).
- `ProviderCredentialConfig` is a pure TypedDict annotation pattern; concrete credential types extend it per provider.
- The `harnessiq/__init__.py` lazy-load mechanism handles `"config"` with zero changes beyond adding to `_EXPORTED_MODULES`.

## Acceptance Criteria
- [ ] `from harnessiq.config import CredentialLoader, ProviderCredentialConfig` works
- [ ] `import harnessiq; harnessiq.config` works via lazy load
- [ ] `CredentialLoader().load("KEY")` returns correct value from a `.env` file
- [ ] `CredentialLoader().load("KEY")` raises `FileNotFoundError` when `.env` absent
- [ ] `CredentialLoader().load("MISSING")` raises `KeyError` with key name in message
- [ ] `CredentialLoader().load_all(["A","B"])` raises on first missing key
- [ ] Quoted values (`KEY="value"`, `KEY='value'`) are returned unquoted
- [ ] Blank lines and `#`-prefixed lines are skipped without error
- [ ] `_infer_provider_name("https://api.snov.io/...")` returns `"snovio"`
- [ ] Same test for all 8 new hostnames
- [ ] All pre-existing tests remain green

## Verification Steps
1. `python -m pytest tests/test_config_loader.py -v`
2. `python -m pytest tests/test_provider_base.py -v`
3. `python -m pytest tests/ -v`
4. `python -c "from harnessiq.config import CredentialLoader; print('ok')"`
5. `python -m py_compile harnessiq/config/loader.py harnessiq/config/models.py harnessiq/config/__init__.py`

## Dependencies
None — foundation ticket. All provider tickets (2–9) depend on this.

## Drift Guard
This ticket must not implement any provider-specific credential models, agent wiring, CLI commands, or changes to existing provider clients. Config package foundation and hostname map additions only.
