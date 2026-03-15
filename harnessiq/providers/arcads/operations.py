"""Arcads operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.arcads.client import ArcadsCredentials

ARCADS_REQUEST = "arcads.request"
PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class ArcadsOperation:
    """Declarative metadata for one Arcads API operation."""

    name: str
    category: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    path_hint: str
    required_path_params: tuple[str, ...] = ()
    payload_kind: PayloadKind = "none"
    payload_required: bool = False
    allow_query: bool = False

    def summary(self) -> str:
        return f"{self.name} ({self.method} {self.path_hint})"


@dataclass(frozen=True, slots=True)
class ArcadsPreparedRequest:
    """A validated Arcads request ready for execution."""

    operation: ArcadsOperation
    method: str
    path: str
    url: str
    headers: dict[str, str]
    json_body: Any | None


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def _op(
    name: str,
    category: str,
    method: Literal["GET", "POST", "PUT", "DELETE"],
    path_hint: str,
    *,
    required_path_params: Sequence[str] = (),
    payload_kind: PayloadKind = "none",
    payload_required: bool = False,
    allow_query: bool = False,
) -> tuple[str, ArcadsOperation]:
    return (
        name,
        ArcadsOperation(
            name=name,
            category=category,
            method=method,
            path_hint=path_hint,
            required_path_params=tuple(required_path_params),
            payload_kind=payload_kind,
            payload_required=payload_required,
            allow_query=allow_query,
        ),
    )


_ARCADS_CATALOG: OrderedDict[str, ArcadsOperation] = OrderedDict(
    (
        # Products
        _op("create_product", "Products", "POST", "/v1/products", payload_kind="object", payload_required=True),
        _op("list_products", "Products", "GET", "/v1/products"),
        # Folders
        _op("create_folder", "Folders", "POST", "/v1/folders", payload_kind="object", payload_required=True),
        _op("list_product_folders", "Folders", "GET", "/v1/products/{productId}/folders", required_path_params=("productId",)),
        # Situations
        _op("list_situations", "Situations", "GET", "/v1/situations", allow_query=True),
        # Scripts
        _op("create_script", "Scripts", "POST", "/v1/scripts", payload_kind="object", payload_required=True),
        _op("list_folder_scripts", "Scripts", "GET", "/v1/folders/{folderId}/scripts", required_path_params=("folderId",)),
        _op("update_script", "Scripts", "PUT", "/v1/scripts/{scriptId}", required_path_params=("scriptId",), payload_kind="object", payload_required=True),
        _op("generate_video", "Scripts", "POST", "/v1/scripts/{scriptId}/generate", required_path_params=("scriptId",), payload_kind="object"),
        # Videos
        _op("list_script_videos", "Videos", "GET", "/v1/scripts/{scriptId}/videos", required_path_params=("scriptId",)),
    )
)


def build_arcads_operation_catalog() -> tuple[ArcadsOperation, ...]:
    """Return the supported Arcads operation catalog in stable order."""
    return tuple(_ARCADS_CATALOG.values())


def get_arcads_operation(operation_name: str) -> ArcadsOperation:
    """Return a supported Arcads operation or raise a clear error."""
    op = _ARCADS_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_ARCADS_CATALOG)
        raise ValueError(f"Unsupported Arcads operation '{operation_name}'. Available: {available}.")
    return op


def build_arcads_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Arcads request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=ARCADS_REQUEST,
        name="arcads_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Arcads operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as productId, folderId, scriptId.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for paginated list operations.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "Optional JSON body for create/update/generate operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_arcads_tools(
    *,
    credentials: "ArcadsCredentials | None" = None,
    client: "Any | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Arcads request tool backed by the provided client."""
    arcads_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_arcads_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = arcads_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = arcads_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=arcads_client.credentials.timeout_seconds,
        )
        return {
            "operation": prepared.operation.name,
            "method": prepared.method,
            "path": prepared.path,
            "response": response,
        }

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_prepared_request(
    *,
    operation_name: str,
    credentials: "ArcadsCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> ArcadsPreparedRequest:
    from harnessiq.providers.arcads.api import build_headers

    op = get_arcads_operation(operation_name)
    normalized_params = {str(k): str(v) for k, v in (path_params or {}).items()}
    missing = [k for k in op.required_path_params if not normalized_params.get(k)]
    if missing:
        raise ValueError(f"Operation '{op.name}' requires path parameters: {', '.join(missing)}.")

    if op.payload_kind == "none" and payload is not None:
        raise ValueError(f"Operation '{op.name}' does not accept a payload.")
    if op.payload_required and payload is None:
        raise ValueError(f"Operation '{op.name}' requires a payload.")

    path = op.path_hint
    for key, value in normalized_params.items():
        path = path.replace(f"{{{key}}}", quote(value, safe=""))

    normalized_query = {str(k): v for k, v in query.items()} if query else None
    full_url = join_url(credentials.base_url, path, query=normalized_query)  # type: ignore[arg-type]
    headers = build_headers(credentials.client_id, credentials.client_secret)

    return ArcadsPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


def _select_operations(allowed: Sequence[str] | None) -> tuple[ArcadsOperation, ...]:
    if allowed is None:
        return build_arcads_operation_catalog()
    seen: set[str] = set()
    selected: list[ArcadsOperation] = []
    for name in allowed:
        op = get_arcads_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.arcads.client import ArcadsClient
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Arcads credentials or an Arcads client must be provided.")
    return ArcadsClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        raise ValueError(f"Unsupported Arcads operation '{value}'.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


def _build_tool_description(operations: Sequence[ArcadsOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Arcads AI video ad creation API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append("Use 'path_params' for resource ids, 'query' for paginated lists, 'payload' for JSON bodies.")
    return "\n".join(lines)


__all__ = [
    "ARCADS_REQUEST",
    "ArcadsOperation",
    "ArcadsPreparedRequest",
    "_build_prepared_request",
    "build_arcads_operation_catalog",
    "build_arcads_request_tool_definition",
    "create_arcads_tools",
    "get_arcads_operation",
]
