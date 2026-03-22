# Ticket 1: arXiv Provider Core

## Title
Add `harnessiq/providers/arxiv/` — credentials config, HTTP client, API helpers, and operation catalog

## Intent
Establish the foundational provider layer for arXiv so that downstream tickets can build the tool factory and registration on top of a clean, tested provider contract. This is the data-access layer only — no tool wiring.

## Scope
**Creates:**
- `harnessiq/providers/arxiv/__init__.py`
- `harnessiq/providers/arxiv/client.py` — `ArxivConfig` transport-config dataclass + `ArxivClient`
- `harnessiq/providers/arxiv/api.py` — URL builders, Atom XML parser (`parse_arxiv_feed`, `parse_arxiv_entry`)
- `harnessiq/providers/arxiv/operations.py` — `ArxivOperation` frozen dataclass + `_CATALOG` + `build_arxiv_operation_catalog()` + `get_arxiv_operation()`

**Does not touch:** tool factories, shared/tools.py constants, catalog.py, registry.py, tests, or file_index.md.

## Relevant Files
| File | Change |
|------|--------|
| `harnessiq/providers/arxiv/__init__.py` | New — re-exports `ArxivConfig`, `ArxivClient`, `ArxivOperation`, `build_arxiv_operation_catalog`, `get_arxiv_operation` |
| `harnessiq/providers/arxiv/client.py` | New — `ArxivConfig` + `ArxivClient` |
| `harnessiq/providers/arxiv/api.py` | New — URL builders + Atom XML parser |
| `harnessiq/providers/arxiv/operations.py` | New — operation catalog |

## Approach

### `ArxivConfig` (in `client.py`)
No authentication fields — arXiv search API is fully public. Config holds only transport options:
```python
@dataclass(frozen=True, slots=True)
class ArxivConfig:
    base_url: str = DEFAULT_BASE_URL        # "https://export.arxiv.org"
    timeout_seconds: float = 30.0
    delay_seconds: float = 0.0              # caller sets 3.0 to respect arXiv ToS
```
Validation in `__post_init__`: base_url non-blank, timeout > 0, delay >= 0.

### `ArxivClient` (in `client.py`)
```python
@dataclass(frozen=True, slots=True)
class ArxivClient:
    config: ArxivConfig = field(default_factory=ArxivConfig)
    request_executor: RequestExecutor = request_json
```
Methods:
- `search(*, query, max_results=10, start=0, sort_by="relevance", sort_order="descending") -> list[dict[str, Any]]` — builds query URL, calls executor, parses Atom XML → normalized paper records
- `search_raw(*, query, max_results=10, start=0, sort_by="relevance", sort_order="descending") -> str` — same URL, returns raw XML string
- `get_paper(paper_id: str) -> dict[str, Any] | None` — fetches `id:{paper_id}` query, parses → single record or None
- `download_paper(paper_id: str, save_path: str) -> str` — fetches PDF bytes from `https://arxiv.org/pdf/{paper_id}`, writes to `save_path`, returns save_path

`download_paper` uses `urllib.request` directly (not `request_executor`) because it fetches binary PDF, not JSON/XML.

`delay_seconds` sleep (when > 0) is applied before each `request_executor` call.

### `api.py`
```python
DEFAULT_BASE_URL = "https://export.arxiv.org"
ARXIV_ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"
OPENSEARCH_NS = "http://a9.com/-/spec/opensearch/1.1/"

def search_url(base_url: str, *, query: str, max_results: int, start: int,
               sort_by: str, sort_order: str) -> str: ...
def get_paper_url(base_url: str, paper_id: str) -> str: ...
def pdf_url(paper_id: str) -> str: ...  # https://arxiv.org/pdf/{paper_id}

def parse_arxiv_feed(xml_text: str) -> list[dict[str, Any]]: ...
def parse_arxiv_entry(entry: ET.Element) -> dict[str, Any]: ...
```

Each parsed paper record shape:
```python
{
    "id": "http://arxiv.org/abs/2301.12345v1",
    "arxiv_id": "2301.12345",
    "title": "...",
    "authors": ["Author Name", ...],
    "summary": "Abstract text...",
    "published": "2023-01-30T00:00:00Z",
    "updated": "2023-01-30T00:00:00Z",
    "categories": ["cs.LG", "cs.AI"],
    "primary_category": "cs.LG",
    "pdf_url": "https://arxiv.org/pdf/2301.12345",
    "abs_url": "https://arxiv.org/abs/2301.12345",
}
```
Uses `xml.etree.ElementTree` (stdlib) — no new dependencies.

### `operations.py`
Four operations matching the four client methods:
```python
@dataclass(frozen=True, slots=True)
class ArxivOperation:
    name: str
    category: str
    description: str
    def summary(self) -> str: return self.name
```
Catalog:
- `search` — "Search" — "Search arXiv papers by keyword, author, title, or category; returns normalized paper records."
- `search_raw` — "Search" — "Search arXiv papers; returns raw Atom 1.0 XML."
- `get_paper` — "Retrieval" — "Retrieve a single arXiv paper by ID; returns normalized paper record."
- `download_paper` — "Download" — "Download a paper PDF to a local path."

## Assumptions
- `request_json` returns raw XML string when arXiv responds with Atom XML (confirmed: `_decode_response` falls back to raw text on `JSONDecodeError`).
- `download_paper` is the only operation that uses binary HTTP; it bypasses `request_executor` and uses stdlib `urllib.request` directly.
- `delay_seconds` defaults to `0.0` to avoid slowing tests and respect that enforcement is the caller's responsibility.

## Acceptance Criteria
- [ ] `ArxivConfig()` with no arguments constructs successfully with defaults
- [ ] `ArxivConfig(base_url="")` raises `ValueError`
- [ ] `ArxivConfig(timeout_seconds=0)` raises `ValueError`
- [ ] `ArxivConfig(delay_seconds=-1)` raises `ValueError`
- [ ] `ArxivClient(config=ArxivConfig())` constructs successfully
- [ ] `parse_arxiv_feed(sample_atom_xml)` returns a list of dicts with all normalized fields
- [ ] `parse_arxiv_feed` handles zero-result feeds (empty list, no error)
- [ ] `build_arxiv_operation_catalog()` returns 4 operations in insertion order
- [ ] `get_arxiv_operation("search")` returns the correct operation
- [ ] `get_arxiv_operation("unknown")` raises `ValueError` listing available names
- [ ] `search_url(...)` builds correct URL with all params encoded
- [ ] `pdf_url("2301.12345")` returns `"https://arxiv.org/pdf/2301.12345"`

## Verification Steps
1. `python -m py_compile harnessiq/providers/arxiv/*.py` — no syntax errors
2. `mypy harnessiq/providers/arxiv/` — no type errors
3. `python -m pytest tests/test_arxiv_provider.py::ArxivConfigTests -v`
4. `python -m pytest tests/test_arxiv_provider.py::ArxivApiTests -v`
5. `python -m pytest tests/test_arxiv_provider.py::ArxivOperationTests -v`
6. `python -m pytest tests/test_arxiv_provider.py::ArxivClientTests -v`

## Dependencies
None.

## Drift Guard
This ticket must not create any tool factory code, touch `shared/tools.py`, `toolset/catalog.py`, `toolset/registry.py`, or any test file other than the new `tests/test_arxiv_provider.py`.
