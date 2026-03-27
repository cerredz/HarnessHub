"""ZoomInfo MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.zoominfo.operations import (
    ZoomInfoOperation,
    build_zoominfo_operation_catalog,
    get_zoominfo_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO
from harnessiq.shared.tools import (
    ZOOMINFO_REQUEST,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

if TYPE_CHECKING:
    from harnessiq.providers.zoominfo.client import ZoomInfoClient
    from harnessiq.providers.zoominfo.credentials import ZoomInfoCredentials


def build_zoominfo_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the ZoomInfo request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=ZOOMINFO_REQUEST,
        name="zoominfo_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The ZoomInfo operation to execute. Contact and company search "
                        "operations find records by structured match filters. Enrichment "
                        "operations hydrate partial records with full profile data. Bulk "
                        "operations submit large enrichment jobs. Intent and news operations "
                        "surface buying signals and intelligence. The tool handles two-step "
                        "JWT authentication automatically."
                    ),
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Parameters for the operation. For search_contacts / search_companies: "
                        "{output_fields: [...], match_filter: {...}, rpp?, page?}. "
                        "For search_intent: {company_ids: [...], topics: [...], "
                        "start_date?, end_date?}. "
                        "For enrich_contact / enrich_company: "
                        "{match_input: [{...}, ...], output_fields?: [...]}. "
                        "For enrich_ip: {ip_address, output_fields?: [...]}. "
                        "For bulk_enrich_contacts / bulk_enrich_companies: "
                        "{match_input: [{...}, ...], output_fields?: [...]}. "
                        "For lookup_output_fields: {entity} where entity is 'contact' or 'company'. "
                        "Omit for get_usage."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_zoominfo_tools(
    *,
    credentials: "ZoomInfoCredentials | None" = None,
    client: "ZoomInfoClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the ZoomInfo request tool backed by the provided client.

    ZoomInfo uses a two-step JWT authentication flow: the tool transparently
    calls ``client.authenticate()`` before each operation to obtain a fresh JWT.
    """
    zoominfo_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_zoominfo_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        payload: dict[str, Any] = dict(_optional_mapping(arguments, "payload") or {})

        # Obtain a fresh JWT via two-step authentication.
        jwt: str = zoominfo_client.authenticate()

        request = ProviderPayloadRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            payload={"jwt": jwt, **payload},
        )
        return zoominfo_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[ZoomInfoOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated ZoomInfo B2B intelligence and data enrichment API operations.",
        "",
        "ZoomInfo is an enterprise-grade B2B intelligence platform providing verified "
        "contact, company, and intent data. Use search_contacts and search_companies to "
        "discover prospects by structured match filters such as title, industry, and "
        "revenue range. Use enrich_contact or enrich_company to hydrate partial records "
        "with full profile data. Bulk enrichment operations handle large datasets. Intent "
        "operations surface companies actively researching topics related to your product. "
        "The tool handles ZoomInfo's two-step JWT authentication automatically — the "
        "username and password are exchanged for a JWT before each API call.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: pass all operation-specific arguments inside 'payload'. "
        "JWT authentication is handled internally — do not include it in payload."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[ZoomInfoOperation, ...]:
    if allowed is None:
        return build_zoominfo_operation_catalog()
    seen: set[str] = set()
    selected: list[ZoomInfoOperation] = []
    for name in allowed:
        op = get_zoominfo_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either ZoomInfo credentials or a ZoomInfo client must be provided.")
    from harnessiq.providers.zoominfo.client import ZoomInfoClient
    return ZoomInfoClient(
        username=credentials["username"],
        password=credentials["password"],
    )


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported ZoomInfo operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(
    arguments: Mapping[str, object], key: str
) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


__all__ = [
    "build_zoominfo_request_tool_definition",
    "create_zoominfo_tools",
]
