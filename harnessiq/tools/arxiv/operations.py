"""arXiv MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Sequence

from harnessiq.providers.arxiv.operations import (
    ArxivOperation,
    build_arxiv_operation_catalog,
    get_arxiv_operation,
)
from harnessiq.shared.tools import ARXIV_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.arxiv.client import ArxivClient, ArxivConfig


def build_arxiv_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the arXiv request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=ARXIV_REQUEST,
        name="arxiv_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The arXiv operation to execute. "
                        "Use 'search' or 'search_raw' to find papers by keyword, "
                        "'get_paper' to retrieve a paper by arXiv ID, "
                        "and 'download_paper' to save a PDF to a local path."
                    ),
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Search query string. Supports arXiv field prefixes: "
                        "ti: (title), au: (author), abs: (abstract), "
                        "cat: (category, e.g. cs.LG), all: (all fields). "
                        "Boolean operators: AND, OR, ANDNOT. "
                        "Required for 'search' and 'search_raw' operations."
                    ),
                },
                "paper_id": {
                    "type": "string",
                    "description": (
                        "arXiv paper ID (e.g. '2301.12345' or 'hep-ph/9901257'). "
                        "Required for 'get_paper' and 'download_paper' operations."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1–2000). Defaults to 10.",
                    "minimum": 1,
                    "maximum": 2000,
                },
                "start": {
                    "type": "integer",
                    "description": "Pagination offset — index of the first result. Defaults to 0.",
                    "minimum": 0,
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                    "description": "Sort criterion. Defaults to 'relevance'.",
                },
                "sort_order": {
                    "type": "string",
                    "enum": ["ascending", "descending"],
                    "description": "Sort direction. Defaults to 'descending'.",
                },
                "save_path": {
                    "type": "string",
                    "description": (
                        "Local file path where the PDF will be saved. "
                        "Required for 'download_paper'."
                    ),
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_arxiv_tools(
    *,
    credentials: "ArxivConfig | None" = None,
    client: "ArxivClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style arXiv request tool backed by the provided client.

    arXiv requires no API credentials.  When both *credentials* and *client*
    are ``None``, a default ``ArxivClient`` (with default ``ArxivConfig``) is
    constructed automatically.

    Args:
        credentials: Optional ``ArxivConfig`` transport config.  When supplied
            alongside *client=None* a new ``ArxivClient`` is constructed from it.
        client: Optional pre-built ``ArxivClient``.  Takes precedence over
            *credentials* when both are provided.
        allowed_operations: Subset of operation names to expose.  All four
            operations are exposed when ``None``.

    Returns:
        A 1-tuple containing the single ``arxiv.request`` ``RegisteredTool``.
    """
    arxiv_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_arxiv_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)

        if operation_name == "search":
            results = arxiv_client.search(
                query=_require_str(arguments, "query"),
                max_results=int(arguments.get("max_results", 10)),
                start=int(arguments.get("start", 0)),
                sort_by=str(arguments.get("sort_by", "relevance")),
                sort_order=str(arguments.get("sort_order", "descending")),
            )
            return {"operation": "search", "results": results, "count": len(results)}

        if operation_name == "search_raw":
            xml = arxiv_client.search_raw(
                query=_require_str(arguments, "query"),
                max_results=int(arguments.get("max_results", 10)),
                start=int(arguments.get("start", 0)),
                sort_by=str(arguments.get("sort_by", "relevance")),
                sort_order=str(arguments.get("sort_order", "descending")),
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

        # Unreachable: _require_operation_name guards against unknown names.
        raise ValueError(f"Unhandled arXiv operation '{operation_name}'.")  # pragma: no cover

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_tool_description(operations: Sequence[ArxivOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute arXiv academic paper search and retrieval operations.",
        "",
        "arXiv hosts over 2 million open-access papers across physics, mathematics, "
        "computer science, quantitative biology, quantitative finance, statistics, "
        "electrical engineering, and economics. No API credentials are required.",
        "",
        "Search tips: use field prefixes (ti: title, au: author, abs: abstract, "
        "cat: category such as cs.LG or quant-ph) with AND / OR / ANDNOT operators. "
        "arXiv ToS requests ≤ 1 call per 3 seconds — set delay_seconds=3.0 on "
        "ArxivConfig to enforce this automatically.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[ArxivOperation, ...]:
    if allowed is None:
        return build_arxiv_operation_catalog()
    seen: set[str] = set()
    selected: list[ArxivOperation] = []
    for name in allowed:
        op = get_arxiv_operation(name)  # raises ValueError for unknown names
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    from harnessiq.providers.arxiv.client import ArxivClient, ArxivConfig
    return ArxivClient(config=credentials if credentials is not None else ArxivConfig())


def _require_operation_name(arguments: ToolArguments, allowed: frozenset[str]) -> str:
    value = arguments.get("operation")
    if value is None:
        raise ValueError("The 'operation' argument is required.")
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(
            f"Unsupported arXiv operation '{value}'. Allowed: {allowed_str}."
        )
    return value


def _require_str(arguments: ToolArguments, key: str) -> str:
    value = arguments.get(key)
    if value is None:
        raise ValueError(f"The '{key}' argument is required for this operation.")
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string.")
    return value


__all__ = [
    "build_arxiv_request_tool_definition",
    "create_arxiv_tools",
]
