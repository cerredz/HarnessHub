"""Creatify MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.interfaces import RequestPreparingClient
from harnessiq.shared.dtos import ProviderOperationRequestDTO

from harnessiq.providers.creatify.operations import (
    CreatifyOperation,
    build_creatify_operation_catalog,
    get_creatify_operation,
)
from harnessiq.shared.tools import CREATIFY_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.creatify.client import CreatifyClient, CreatifyCredentials


def build_creatify_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Creatify request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=CREATIFY_REQUEST,
        name="creatify_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Creatify operation to execute. Each operation maps to one "
                        "API endpoint — use the lifecycle sequence create → preview → render "
                        "for video and avatar operations."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": (
                        "Path parameters required by the operation URL, typically a resource "
                        "id such as {'id': 'abc123'}."
                    ),
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": (
                        "Optional query parameters for list and filter operations "
                        "(e.g. pagination, status filters)."
                    ),
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "JSON request body for create and update operations. Required when "
                        "the operation specifies payload_required=True."
                    ),
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_creatify_tools(
    *,
    credentials: "CreatifyCredentials | None" = None,
    client: RequestPreparingClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Creatify request tool backed by the provided client.

    Provide either *credentials* (used to construct a fresh ``CreatifyClient``) or
    an already-constructed *client* for testing.
    """
    creatify_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_creatify_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        request = ProviderOperationRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            path_params=_optional_mapping(arguments, "path_params") or {},
            query=_optional_mapping(arguments, "query") or {},
            payload=arguments.get("payload"),
        )
        return creatify_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[CreatifyOperation]) -> str:
    """Build a semantically rich description for the Creatify tool."""
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Creatify AI video creation API operations.",
        "",
        "Creatify is an AI-powered video and ad creation platform. Use it to generate "
        "marketing videos from product URLs, create AI avatar videos with text-to-speech, "
        "produce short-form social content with AI Shorts, and manage custom video templates "
        "and assets. The standard lifecycle for video operations is: create (POST) → "
        "preview (POST /{id}/preview/) → render (POST /{id}/render/) → poll status (GET /{id}/).",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: use 'path_params' to pass resource ids (e.g. {'id': 'abc123'}), "
        "'query' for pagination and list filters, 'payload' for JSON request bodies on create "
        "and update operations."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[CreatifyOperation, ...]:
    if allowed is None:
        return build_creatify_operation_catalog()
    seen: set[str] = set()
    selected: list[CreatifyOperation] = []
    for name in allowed:
        op = get_creatify_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Creatify credentials or a Creatify client must be provided.")
    from harnessiq.providers.creatify.client import CreatifyClient
    return CreatifyClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(
            f"Unsupported Creatify operation '{value}'. Allowed: {allowed_str}."
        )
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


__all__ = [
    "build_creatify_request_tool_definition",
    "create_creatify_tools",
]
