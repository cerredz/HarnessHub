### 1a: Structural Survey

**arXiv API**
- Base URL: `https://export.arxiv.org/api/query`
- No authentication required for all read/search operations
- Query string built with field prefixes: `ti:`, `au:`, `abs:`, `cat:`, `all:` + boolean operators (`AND`, `OR`, `ANDNOT`)
- Additional params: `start` (pagination offset), `max_results` (≤2000), `sortBy` (relevance/lastUpdatedDate/submittedDate), `sortOrder` (ascending/descending)
- Response format: **Atom 1.0 XML** — not JSON
- Rate limit: 1 request every 3 seconds (soft, ToS-enforced)
- No native full-text or embedding/semantic search — only title/abstract/metadata keyword search

**Codebase Provider Pattern (from Exa + Coresignal cross-reference):**
```
harnessiq/providers/<name>/
  __init__.py      — re-exports
  client.py        — credentials dataclass + HTTP client
  api.py           — DEFAULT_BASE_URL, build_headers(), URL builders
  operations.py    — OperationCatalog frozen dataclass + _CATALOG OrderedDict

harnessiq/tools/<name>/
  __init__.py      — re-exports create_*_tools()
  operations.py    — build_*_request_tool_definition() + create_*_tools() factory
```

**Key shared files touched by every new provider:**
- `harnessiq/shared/tools.py` — add `ARXIV_REQUEST = "arxiv.request"` constant + `__all__` entry
- `harnessiq/toolset/catalog.py` — add `ToolEntry` to `PROVIDER_ENTRIES` + entry to `PROVIDER_FACTORY_MAP`
- `harnessiq/providers/http.py` — add `"arxiv"` to `_infer_provider_name()`

**Critical arXiv-specific delta from standard pattern:**
- `requires_credentials=False` in the catalog entry — first provider with no auth
- `request_json` returns raw Atom XML string (falls back from JSON decode failure in `_decode_response`) — XML parsing must happen in the client layer
- No `build_headers()` needed (no auth headers)
- Factory must still accept `credentials=None` for signature compatibility

**`request_json` XML handling:** `_decode_response` tries `json.loads(text)`; on `JSONDecodeError` returns the raw text string. So for arXiv, the executor returns the raw Atom XML string, which the client then parses with `xml.etree.ElementTree`.

---

### 1b: Task Cross-Reference

| Task component | Location |
|---|---|
| `ARXIV_REQUEST` constant | `harnessiq/shared/tools.py` — add alongside `CORESIGNAL_REQUEST` |
| `ArxivCredentials` / no-auth config | `harnessiq/providers/arxiv/client.py` — lightweight transport-config-only dataclass |
| `ArxivClient` with `search()` + `get_paper()` | `harnessiq/providers/arxiv/client.py` |
| Atom XML parser | `harnessiq/providers/arxiv/api.py` — `parse_arxiv_feed()` helper |
| URL builder + provider name hint | `harnessiq/providers/arxiv/api.py` + `harnessiq/providers/http.py` |
| `ArxivOperation` catalog + `_CATALOG` | `harnessiq/providers/arxiv/operations.py` |
| `build_arxiv_request_tool_definition()` | `harnessiq/tools/arxiv/operations.py` |
| `create_arxiv_tools()` factory | `harnessiq/tools/arxiv/operations.py` |
| Catalog + factory dispatch registration | `harnessiq/toolset/catalog.py` |
| Unit tests | `tests/test_arxiv_provider.py` |
| `file_index.md` update | `artifacts/file_index.md` |

**What currently exists:** Nothing — net-new across all files.

**Blast radius:** Low. The only changes to existing files are: (1) appending a constant to `shared/tools.py`, (2) appending two entries to `toolset/catalog.py`, and (3) appending one branch to `_infer_provider_name()` in `providers/http.py`.

---

### 1c: Assumption & Risk Inventory

**A1 — No-credentials factory signature:**
All existing providers require credentials; the factory signature `create_*_tools(*, credentials=None, client=None, ...)` is used to inject a pre-built client. For arXiv (no auth), the `credentials` parameter becomes a transport-config object (base_url, timeout_seconds) or is simply unused. Whether to expose a `credentials`-like config object or drop the parameter entirely is ambiguous.

**A2 — "Embedding search" interpretation:**
The tweet references "embedding search tools." The native arXiv API provides keyword search only. This could mean: (a) out-of-scope / not implemented; (b) a separate semantic-search operation backed by a third-party service (Semantic Scholar, etc.); (c) a marketing description of agent-level semantic reasoning over keyword results. Implementing (b) would require a second external dependency. Implementing (a) is safe and consistent with other API-native providers.

**A3 — XML response normalization:**
arXiv returns Atom XML. The tool handler can return: (a) the raw XML string (consistent with how `request_json` fallback works for other non-JSON APIs); (b) a normalized `list[dict]` of paper records (more useful for agents). Returning normalized dicts is strongly preferred for agent usability but is a deviation from how Exa/Coresignal return raw API responses.

**A4 — Paper download / file storage:**
The `blazickjp/arxiv-mcp-server` includes `download_paper` and `read_paper` tools backed by local file storage. The HarnessHub tools layer has a filesystem tool family already. Including download-to-disk in the arXiv provider would couple it to the local filesystem, which is out of scope for a data-provider MCP. Whether to include this operation is unclear.

**A5 — Rate-limit enforcement:**
arXiv ToS: 1 req/3 seconds. Other providers don't bake in delays. Including a `delay_seconds` param (like `arxiv.py` does) would be the only first in the codebase. Whether to enforce this or document it as caller responsibility is unresolved.

Phase 1 complete.
