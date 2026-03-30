"""
===============================================================================
File: harnessiq/tools/exa/operations.py

What this file does:
- Exposes the `exa` tool family for the HarnessIQ tool layer.
- In most packages this module is the bridge between provider-backed operations
  and the generic tool registration surface.
- Exa MCP-style tool factory for the Harnessiq tool layer.

Use cases:
- Import this module when an agent or registry needs the `exa` tool
  definitions.
- Read it to see which runtime operations are intentionally surfaced as tools.

How to use it:
- Call the exported factory helpers from `harnessiq/tools/exa` and merge the
  resulting tools into a registry.

Intent:
- Keep the public `exa` tool surface small, explicit, and separate from
  provider implementation details.
===============================================================================
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.interfaces import RequestPreparingClient
from harnessiq.shared.dtos import ProviderOperationRequestDTO

from harnessiq.providers.exa.operations import (
    ExaOperation,
    build_exa_operation_catalog,
    get_exa_operation,
)
from harnessiq.shared.tools import EXA_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.exa.client import ExaClient, ExaCredentials


def build_exa_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Exa request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=EXA_REQUEST,
        name="exa_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Exa operation to execute. Use 'search' for web search, "
                        "'contents' to fetch page text, 'find_similar' for related URLs, "
                        "'answer' for AI-generated answers, and 'research' for combined "
                        "search-plus-contents in one call. Webset operations manage curated "
                        "URL collections."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters for webset and item operations (e.g. webset_id, item_id).",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for list and filter operations.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "JSON request body. For search operations, provide query, num_results, "
                        "and optional filters. For contents, provide ids and content settings."
                    ),
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_exa_tools(
    *,
    credentials: "ExaCredentials | None" = None,
    client: RequestPreparingClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Exa request tool backed by the provided client."""
    exa_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_exa_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        request = ProviderOperationRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            path_params=_optional_mapping(arguments, "path_params") or {},
            query=_optional_mapping(arguments, "query") or {},
            payload=arguments.get("payload"),
        )
        return exa_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[ExaOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Exa AI neural search and web content API operations.",
        "",
        "Exa is a neural web search engine optimised for AI agents. Use it to search the "
        "live web with natural language queries, retrieve full page content, find semantically "
        "similar URLs, get AI-generated answers grounded in web sources, and manage Websets "
        "(curated collections of URLs with automatic enrichment). Exa is ideal for research, "
        "competitive intelligence, and grounding agent responses with real-time information.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: 'payload' carries the main request body (query, filters, "
        "content settings). Use 'path_params' for webset/item ids. 'query' for list pagination."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[ExaOperation, ...]:
    if allowed is None:
        return build_exa_operation_catalog()
    seen: set[str] = set()
    selected: list[ExaOperation] = []
    for name in allowed:
        op = get_exa_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Exa credentials or an Exa client must be provided.")
    from harnessiq.providers.exa.client import ExaClient
    return ExaClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Exa operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


__all__ = [
    "build_exa_request_tool_definition",
    "create_exa_tools",
]
