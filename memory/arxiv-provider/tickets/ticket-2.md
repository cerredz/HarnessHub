# Ticket 2: arXiv Tool Factory

## Title
Add `harnessiq/tools/arxiv/` — MCP-style tool factory for arXiv

## Intent
Expose the arXiv provider operations as a single `RegisteredTool` (`arxiv.request`) using the standard MCP-style factory pattern. Agents inject this tool to search and retrieve papers from arXiv via the four operations defined in Ticket 1.

## Scope
**Creates:**
- `harnessiq/tools/arxiv/__init__.py`
- `harnessiq/tools/arxiv/operations.py` — `build_arxiv_request_tool_definition()` + `create_arxiv_tools()` factory

**Does not touch:** provider files, shared/tools.py, catalog.py, registry.py, or tests.

## Relevant Files
| File | Change |
|------|--------|
| `harnessiq/tools/arxiv/__init__.py` | New — re-exports `create_arxiv_tools` |
| `harnessiq/tools/arxiv/operations.py` | New — tool definition builder + factory |

## Approach

### `build_arxiv_request_tool_definition()`
Returns a `ToolDefinition` with:
- `key = ARXIV_REQUEST` (`"arxiv.request"` — defined in Ticket 3)
- `name = "arxiv_request"`
- `description` — multi-line, grouped by category (Search, Retrieval, Download), listing each operation's summary
- `input_schema` — JSON Schema with:
  - `operation` (string, enum of allowed names) — required
  - `query` (string) — required for search/search_raw
  - `paper_id` (string) — required for get_paper/download_paper
  - `max_results` (integer, default 10, min 1, max 2000)
  - `start` (integer, default 0, min 0)
  - `sort_by` (string, enum: relevance/lastUpdatedDate/submittedDate)
  - `sort_order` (string, enum: ascending/descending)
  - `save_path` (string) — required for download_paper
  - `additionalProperties: false`

### `create_arxiv_tools()`
```python
def create_arxiv_tools(
    *,
    credentials: "ArxivConfig | None" = None,
    client: "ArxivClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
```
- `_coerce_client()` helper: if `client` is provided use it; else construct `ArxivClient(config=credentials or ArxivConfig())`
- `_select_operations()`: filter `_CATALOG` to `allowed_operations` (or all if `None`); raise `ValueError` on unknown names
- `allowed_names = frozenset(op.name for op in selected)`
- Tool definition built from selected operations only (enum is filtered)
- Handler closure dispatches by `operation` to corresponding `ArxivClient` method:

```python
def handler(arguments: ToolArguments) -> dict[str, Any]:
    operation_name = _require_operation_name(arguments, allowed_names)
    if operation_name == "search":
        results = arxiv_client.search(
            query=_require_str(arguments, "query"),
            max_results=arguments.get("max_results", 10),
            start=arguments.get("start", 0),
            sort_by=arguments.get("sort_by", "relevance"),
            sort_order=arguments.get("sort_order", "descending"),
        )
        return {"operation": "search", "results": results, "count": len(results)}
    if operation_name == "search_raw":
        xml = arxiv_client.search_raw(
            query=_require_str(arguments, "query"),
            max_results=arguments.get("max_results", 10),
            start=arguments.get("start", 0),
            sort_by=arguments.get("sort_by", "relevance"),
            sort_order=arguments.get("sort_order", "descending"),
        )
        return {"operation": "search_raw", "xml": xml}
    if operation_name == "get_paper":
        record = arxiv_client.get_paper(_require_str(arguments, "paper_id"))
        return {"operation": "get_paper", "paper": record}
    if operation_name == "download_paper":
        path = arxiv_client.download_paper(
            _require_str(arguments, "paper_id"),
            _require_str(arguments, "save_path"),
        )
        return {"operation": "download_paper", "saved_to": path}
    raise ValueError(f"Unhandled operation '{operation_name}'.")  # unreachable
```

### Validation helpers
- `_require_operation_name(arguments, allowed)` — validates str + membership in frozenset
- `_require_str(arguments, key)` — raises `ValueError` with clear message if key missing or not str
- `_coerce_client(credentials, client)` — constructs default if both None

## Assumptions
- `ARXIV_REQUEST = "arxiv.request"` constant is available in `harnessiq.shared.tools` (from Ticket 3). Uses `TYPE_CHECKING` guard and string literal fallback if needed, or deferred import.
- `ArxivConfig` with no arguments works (all defaults), so `_coerce_client(None, None)` is valid.
- Handler returns a plain `dict` — no special serialization needed.

## Acceptance Criteria
- [ ] `create_arxiv_tools()` with no arguments returns a 1-tuple of `RegisteredTool`
- [ ] `create_arxiv_tools(allowed_operations=["search"])` returns a tool whose schema enum only contains `["search"]`
- [ ] `create_arxiv_tools(allowed_operations=["nonexistent"])` raises `ValueError`
- [ ] Tool handler dispatches `"search"` → `ArxivClient.search()` and returns `{"operation": "search", "results": [...], "count": N}`
- [ ] Tool handler dispatches `"search_raw"` → `ArxivClient.search_raw()` and returns `{"operation": "search_raw", "xml": "..."}`
- [ ] Tool handler dispatches `"get_paper"` → `ArxivClient.get_paper()` and returns `{"operation": "get_paper", "paper": {...}}`
- [ ] Tool handler dispatches `"download_paper"` → `ArxivClient.download_paper()` and returns `{"operation": "download_paper", "saved_to": "..."}`
- [ ] Tool handler raises `ValueError` for unknown operation name
- [ ] `ToolRegistry(create_arxiv_tools())` registers without error (integration check)

## Verification Steps
1. `python -m py_compile harnessiq/tools/arxiv/*.py` — no syntax errors
2. `mypy harnessiq/tools/arxiv/` — no type errors
3. `python -m pytest tests/test_arxiv_provider.py::ArxivToolsTests -v`
4. `python -m pytest tests/test_arxiv_provider.py -v --tb=short` — all provider + tool tests pass together

## Dependencies
Ticket 1 must be complete (provider layer must exist).

## Drift Guard
This ticket must not modify the provider layer, shared constants, catalog, or registry. All input validation and dispatch logic stays inside `harnessiq/tools/arxiv/operations.py`.
