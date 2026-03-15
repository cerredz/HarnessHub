"""Snov.io MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.snovio.operations import (
    SnovioOperation,
    build_snovio_operation_catalog,
    get_snovio_operation,
)
from harnessiq.shared.tools import SNOVIO_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.snovio.client import SnovioClient
    from harnessiq.providers.snovio.credentials import SnovioCredentials


def build_snovio_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Snov.io request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=SNOVIO_REQUEST,
        name="snovio_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Snov.io operation to execute. Email discovery operations find "
                        "and verify addresses by domain or social profile. Prospect operations "
                        "manage contact records and lists. Campaign operations control email "
                        "drip sequences. All operations use OAuth2 client-credentials auth "
                        "handled transparently by the tool."
                    ),
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Parameters for the operation. For domain_search: {domain, type?, limit?}. "
                        "For get_emails_from_names: {first_name, last_name, domain}. "
                        "For add_prospect: {email, full_name, list_id, ...}. "
                        "For add_to_campaign: {campaign_id, emails}. "
                        "For get_campaign: {campaign_id}. "
                        "Omit for operations that require no additional parameters "
                        "(e.g., get_prospect_lists, get_all_campaigns, get_user_info)."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_snovio_tools(
    *,
    credentials: "SnovioCredentials | None" = None,
    client: "SnovioClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the Snov.io request tool backed by the provided client.

    Snov.io uses OAuth2 client credentials.  The tool transparently exchanges
    *client_id* / *client_secret* for an access token before each operation.
    Pass either *credentials* (to construct a default client) or an already-
    constructed *client*.
    """
    snovio_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_snovio_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        payload: dict[str, Any] = dict(_optional_mapping(arguments, "payload") or {})

        # Exchange client credentials for an OAuth2 access token.
        token_response = snovio_client.get_access_token()
        access_token: str = (
            token_response.get("access_token", token_response)
            if isinstance(token_response, dict)
            else str(token_response)
        )

        result = getattr(snovio_client, operation_name)(access_token, **payload)
        return {"operation": operation_name, "result": result}

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[SnovioOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Snov.io email intelligence and outreach API operations.",
        "",
        "Snov.io is a B2B email discovery and outreach platform. Use email discovery "
        "operations to find and verify contact emails from domains, names, or LinkedIn "
        "profiles. Prospect operations manage contact records across segmented lists. "
        "Campaign operations run automated email drip sequences — add recipients, start, "
        "pause, and monitor campaign delivery. The tool handles OAuth2 token exchange "
        "automatically using the configured client credentials.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: pass all operation-specific arguments inside 'payload' "
        "as key-value pairs (e.g., {\"domain\": \"example.com\"} for domain_search). "
        "The access token is managed internally — do not include it in payload."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[SnovioOperation, ...]:
    if allowed is None:
        return build_snovio_operation_catalog()
    seen: set[str] = set()
    selected: list[SnovioOperation] = []
    for name in allowed:
        op = get_snovio_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Snov.io credentials or a Snov.io client must be provided.")
    from harnessiq.providers.snovio.client import SnovioClient
    return SnovioClient(
        client_id=credentials["client_id"],
        client_secret=credentials["client_secret"],
    )


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Snov.io operation '{value}'. Allowed: {allowed_str}.")
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
    "build_snovio_request_tool_definition",
    "create_snovio_tools",
]
