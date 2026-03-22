# Ticket 3: Registration, Registry Fix, Tests, and Docs

## Title
Wire arXiv into the toolset catalog, fix `ToolsetRegistry` credential guard for no-auth providers, write tests, and update docs

## Intent
Complete the end-to-end integration: add the `ARXIV_REQUEST` constant, register arXiv in the toolset catalog and factory dispatch table, add the arXiv hostname to HTTP error inference, fix the registry so `requires_credentials=False` providers don't require a credentials object at call time, write the full test suite, and update `file_index.md`.

## Scope
**Modifies:**
- `harnessiq/shared/tools.py` — add `ARXIV_REQUEST` constant + `__all__` entry
- `harnessiq/toolset/catalog.py` — add `ToolEntry` to `PROVIDER_ENTRIES` + `PROVIDER_FACTORY_MAP` entry
- `harnessiq/providers/http.py` — add `"arxiv"` branch to `_infer_provider_name()`
- `harnessiq/toolset/registry.py` — update `_resolve_provider_tool` and `_resolve_family` to skip credential guard when `entry.requires_credentials is False`
- `artifacts/file_index.md` — add arXiv provider and tool factory entries

**Creates:**
- `tests/test_arxiv_provider.py` — full test suite

**Does not touch:** any provider or tool factory file.

## Relevant Files
| File | Change |
|------|--------|
| `harnessiq/shared/tools.py` | Add `ARXIV_REQUEST = "arxiv.request"` in provider constants block; add to `__all__` |
| `harnessiq/toolset/catalog.py` | Add `ToolEntry(key="arxiv.request", ..., requires_credentials=False)` to `PROVIDER_ENTRIES`; add `"arxiv"` to `PROVIDER_FACTORY_MAP` |
| `harnessiq/providers/http.py` | Add `if "arxiv" in host: return "arxiv"` in `_infer_provider_name()` |
| `harnessiq/toolset/registry.py` | Gate credential-None check on `entry.requires_credentials` in `_resolve_provider_tool`; same gate in `_resolve_family` for provider families |
| `tests/test_arxiv_provider.py` | New — full test suite (see below) |
| `artifacts/file_index.md` | Add arXiv provider/tools entries under Source layout and Tests sections |

## Approach

### `shared/tools.py`
Add after `CORESIGNAL_REQUEST`:
```python
ARXIV_REQUEST = "arxiv.request"
```
Add `"ARXIV_REQUEST"` to `__all__` in alphabetical position.

### `toolset/catalog.py`
Add to `PROVIDER_ENTRIES` (alphabetical by key):
```python
ToolEntry(
    key="arxiv.request",
    name="arxiv_request",
    description="Execute arXiv academic paper search and retrieval API operations (no credentials required).",
    family="arxiv",
    requires_credentials=False,
),
```
Add to `PROVIDER_FACTORY_MAP`:
```python
"arxiv": ("harnessiq.tools.arxiv", "create_arxiv_tools"),
```

### `providers/http.py`
Add to `_infer_provider_name()` before the final `return "provider"`:
```python
if "arxiv" in host:
    return "arxiv"
```

### `toolset/registry.py`
**`_resolve_provider_tool` fix:**
```python
def _resolve_provider_tool(self, key: str, credentials: object) -> RegisteredTool:
    entry = PROVIDER_ENTRY_INDEX[key]
    family = entry.family
    if credentials is None and entry.requires_credentials:  # was: if credentials is None
        raise ValueError(
            f"Tool '{key}' requires credentials for the '{family}' provider. ..."
        )
    tools = _invoke_provider_factory(family, credentials)
    ...
```

**`_resolve_family` fix:**
```python
if family in PROVIDER_FACTORY_MAP:
    family_entries = [e for e in PROVIDER_ENTRIES if e.family == family]
    needs_creds = any(e.requires_credentials for e in family_entries)
    if credentials is None and needs_creds:  # was: if credentials is None
        raise ValueError(...)
    tools = _invoke_provider_factory(family, credentials)
    return tools
```

### `tests/test_arxiv_provider.py`
Test classes:
1. **`ArxivConfigTests`** — valid construction, blank base_url, zero timeout, negative delay
2. **`ArxivApiTests`** — `search_url` param encoding, `pdf_url`, `parse_arxiv_feed` happy path, `parse_arxiv_feed` empty feed, `parse_arxiv_entry` field extraction
3. **`ArxivOperationTests`** — catalog size == 4, `get_arxiv_operation` happy path, `get_arxiv_operation` unknown name error message
4. **`ArxivClientTests`** — `search()` calls executor + returns parsed records (mock executor returns sample Atom XML), `search_raw()` returns string, `get_paper()` found + not-found (empty feed), `download_paper()` writes bytes to temp path
5. **`ArxivToolsTests`** — `create_arxiv_tools()` returns 1-tuple, allowed_operations filtering, unknown operation raises, each handler dispatches correctly (mock client), `ToolRegistry(create_arxiv_tools())` round-trip
6. **`ArxivRegistryIntegrationTests`** — `ToolsetRegistry().get("arxiv.request")` succeeds with `credentials=None` (no error), `ToolsetRegistry().get_family("arxiv")` succeeds without credentials, existing provider key still raises with `credentials=None`

**Sample Atom XML fixture** (inline in tests, not a file):
```python
_SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>1</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>10</opensearch:itemsPerPage>
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <title>Attention Is All You Need</title>
    <summary>A landmark transformer paper.</summary>
    <published>2017-06-12T00:00:00Z</published>
    <updated>2017-06-12T00:00:00Z</updated>
    <author><name>Ashish Vaswani</name></author>
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom" label="cs.LG"/>
    <arxiv:primary_category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
    <link rel="alternate" href="https://arxiv.org/abs/2301.12345" type="text/html"/>
    <link rel="related" href="https://arxiv.org/pdf/2301.12345" type="application/pdf" title="pdf"/>
  </entry>
</feed>"""
```

## Assumptions
- `_resolve_family` looks up `PROVIDER_ENTRIES` by family name to determine `needs_creds`. This is correct since all entries for a single family share the same `requires_credentials` value.
- `ToolsetRegistry` tests for existing credential-requiring providers (e.g. `exa.request`) remain unaffected — the guard still fires when `requires_credentials=True`.
- `PROVIDER_ENTRIES` is kept alphabetically sorted by key — arXiv entry goes first.

## Acceptance Criteria
- [ ] `from harnessiq.shared.tools import ARXIV_REQUEST` works; value is `"arxiv.request"`
- [ ] `"ARXIV_REQUEST"` appears in `harnessiq.shared.tools.__all__`
- [ ] `PROVIDER_ENTRY_INDEX["arxiv.request"]` exists with `requires_credentials=False`
- [ ] `PROVIDER_FACTORY_MAP["arxiv"]` points to `("harnessiq.tools.arxiv", "create_arxiv_tools")`
- [ ] `_infer_provider_name("https://export.arxiv.org/api/query")` returns `"arxiv"`
- [ ] `ToolsetRegistry().get("arxiv.request")` succeeds with `credentials=None`
- [ ] `ToolsetRegistry().get_family("arxiv")` succeeds with no credentials argument
- [ ] `ToolsetRegistry().get("exa.request")` still raises `ValueError` when `credentials=None`
- [ ] All tests in `tests/test_arxiv_provider.py` pass
- [ ] `artifacts/file_index.md` updated with arXiv provider and tool entries

## Verification Steps
1. `python -m py_compile harnessiq/shared/tools.py harnessiq/toolset/catalog.py harnessiq/toolset/registry.py harnessiq/providers/http.py`
2. `mypy harnessiq/shared/tools.py harnessiq/toolset/ harnessiq/providers/http.py`
3. `python -m pytest tests/test_arxiv_provider.py -v --tb=short`
4. `python -m pytest tests/ -v --tb=short` — full suite must still pass (regression check)
5. Smoke: `python -c "from harnessiq.toolset import get_tool; t = get_tool('arxiv.request'); print(t.definition.name)"`

## Dependencies
Tickets 1 and 2 must be complete.

## Drift Guard
This ticket must not modify any file under `harnessiq/providers/arxiv/` or `harnessiq/tools/arxiv/`. The registry change is strictly limited to adding an `entry.requires_credentials` guard — no behavioral changes for existing providers.
