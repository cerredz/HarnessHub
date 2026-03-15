"""Exa operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.exa.client import ExaCredentials

EXA_REQUEST = "exa.request"
PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class ExaOperation:
    """Declarative metadata for one Exa API operation."""

    name: str
    category: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path_hint: str
    required_path_params: tuple[str, ...] = ()
    payload_kind: PayloadKind = "none"
    payload_required: bool = False
    allow_query: bool = False

    def summary(self) -> str:
        return f"{self.name} ({self.method} {self.path_hint})"


@dataclass(frozen=True, slots=True)
class ExaPreparedRequest:
    """A validated Exa request ready for execution."""

    operation: ExaOperation
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
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path_hint: str,
    *,
    required_path_params: Sequence[str] = (),
    payload_kind: PayloadKind = "none",
    payload_required: bool = False,
    allow_query: bool = False,
) -> tuple[str, ExaOperation]:
    return (
        name,
        ExaOperation(
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


_EXA_CATALOG: OrderedDict[str, ExaOperation] = OrderedDict(
    (
        # Search
        _op("search", "Search", "POST", "/search", payload_kind="object", payload_required=True),
        # Contents
        _op("get_contents", "Contents", "POST", "/contents", payload_kind="object", payload_required=True),
        # Find Similar
        _op("find_similar", "Find Similar", "POST", "/findSimilar", payload_kind="object", payload_required=True),
        # Answer
        _op("get_answer", "Answer", "POST", "/answer", payload_kind="object", payload_required=True),
        # Research (search + contents combined)
        _op("search_and_contents", "Research", "POST", "/searchAndContents", payload_kind="object", payload_required=True),
        # Websets (saved search collections)
        _op("list_websets", "Webset", "GET", "/websets", allow_query=True),
        _op("get_webset", "Webset", "GET", "/websets/{webset_id}", required_path_params=("webset_id",)),
        _op("create_webset", "Webset", "POST", "/websets", payload_kind="object", payload_required=True),
        _op("update_webset", "Webset", "PATCH", "/websets/{webset_id}", required_path_params=("webset_id",), payload_kind="object", payload_required=True),
        _op("delete_webset", "Webset", "DELETE", "/websets/{webset_id}", required_path_params=("webset_id",)),
        # Webset Items
        _op("list_webset_items", "Webset Item", "GET", "/websets/{webset_id}/items", required_path_params=("webset_id",), allow_query=True),
        _op("get_webset_item", "Webset Item", "GET", "/websets/{webset_id}/items/{item_id}", required_path_params=("webset_id", "item_id")),
        # Webset Searches (automated search schedules)
        _op("list_webset_searches", "Webset Search", "GET", "/websets/{webset_id}/searches", required_path_params=("webset_id",)),
        _op("create_webset_search", "Webset Search", "POST", "/websets/{webset_id}/searches", required_path_params=("webset_id",), payload_kind="object", payload_required=True),
        _op("delete_webset_search", "Webset Search", "DELETE", "/websets/{webset_id}/searches/{search_id}", required_path_params=("webset_id", "search_id")),
    )
)


def build_exa_operation_catalog() -> tuple[ExaOperation, ...]:
    """Return the supported Exa operation catalog in stable order."""
    return tuple(_EXA_CATALOG.values())


def get_exa_operation(operation_name: str) -> ExaOperation:
    """Return a supported Exa operation or raise a clear error."""
    op = _EXA_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_EXA_CATALOG)
        raise ValueError(f"Unsupported Exa operation '{operation_name}'. Available: {available}.")
    return op


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
                    "description": "Exa operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as webset_id, item_id, search_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for paginated list operations.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "JSON body for search/contents/findSimilar/answer/webset operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_exa_tools(
    *,
    credentials: "ExaCredentials | None" = None,
    client: "Any | None" = None,
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
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = exa_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = exa_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=exa_client.credentials.timeout_seconds,
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
    credentials: "ExaCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> ExaPreparedRequest:
    from harnessiq.providers.exa.api import build_headers

    op = get_exa_operation(operation_name)
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
    headers = build_headers(credentials.api_key)

    return ExaPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


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


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.exa.client import ExaClient
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Exa credentials or an Exa client must be provided.")
    return ExaClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        raise ValueError(f"Unsupported Exa operation '{value}'.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


def _build_tool_description(operations: Sequence[ExaOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Exa AI neural search API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append("Use 'path_params' for resource ids, 'query' for paginated lists, 'payload' for JSON bodies.")
    return "\n".join(lines)


__all__ = [
    "EXA_REQUEST",
    "ExaOperation",
    "ExaPreparedRequest",
    "_build_prepared_request",
    "build_exa_operation_catalog",
    "build_exa_request_tool_definition",
    "create_exa_tools",
    "get_exa_operation",
]
