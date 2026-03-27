"""Smartlead MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.interfaces import RequestPreparingClient

from harnessiq.providers.smartlead.operations import (
    SmartleadOperation,
    build_smartlead_operation_catalog,
    get_smartlead_operation,
)
from harnessiq.shared.tools import SMARTLEAD_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.smartlead.client import SmartleadClient, SmartleadCredentials


def build_smartlead_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Smartlead request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=SMARTLEAD_REQUEST,
        name="smartlead_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Smartlead operation to execute. Use 'create_campaign' then "
                        "'create_campaign_sequences' to set up an outreach campaign. "
                        "Use 'save_email_account' and 'add_email_account_to_campaign' to connect "
                        "sending accounts. Use 'add_leads_to_campaign' to enroll contacts (up to 400 "
                        "per request). Use 'get_campaign_analytics' or 'get_campaign_analytics_by_date' "
                        "to monitor performance. Use 'save_campaign_webhook' to subscribe to "
                        "LEAD_REPLIED, LEAD_OPENED, and other real-time events."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": (
                        "Path parameters for resource-specific operations. "
                        "Supported keys: campaign_id, email_account_id, lead_id, key_id."
                    ),
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": (
                        "Query parameters for list and analytics operations. "
                        "list_campaigns: {client_id (opt), include_tags (bool, opt)}. "
                        "list_email_accounts: {offset (default 0), limit (max 100)}. "
                        "list_campaign_leads: {offset, limit}. "
                        "get_campaign_analytics_by_date: {start_date: 'YYYY-MM-DD', end_date: 'YYYY-MM-DD'}. "
                        "fetch_lead_by_email: {email}."
                    ),
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "JSON body for create, update, and write operations. "
                        "create_campaign: {name, client_id (null)}. "
                        "update_campaign_status: {status: 'ACTIVE'|'PAUSED'|'STOPPED'}. "
                        "add_leads_to_campaign: array of lead objects (max 400). "
                        "save_email_account: {from_name, from_email, username, password, smtp_host, "
                        "smtp_port, smtp_port_type, imap_host, imap_port, max_email_per_day}. "
                        "save_campaign_webhook: {name, webhook_url, event_types array, id (null for new)}."
                    ),
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_smartlead_tools(
    *,
    credentials: "SmartleadCredentials | None" = None,
    client: RequestPreparingClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Smartlead request tool backed by the provided client."""
    sl_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_smartlead_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = sl_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = sl_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=sl_client.credentials.timeout_seconds,
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

def _build_tool_description(operations: Sequence[SmartleadOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Smartlead cold email outreach and deliverability API operations.",
        "",
        "Smartlead is a cold email platform with multi-inbox support, email warm-up, "
        "AI-powered ESP matching, and a master inbox for centralized reply management. "
        "Use it to create and manage outreach campaigns with A/B-tested email sequences, "
        "connect and warm up sending email accounts, enroll leads at scale, reply to prospects "
        "from the master inbox, monitor campaign analytics, configure webhooks for real-time "
        "event notifications, and manage sub-clients in agency/whitelabel setups.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: 'path_params' carries resource ids (campaign_id, email_account_id, "
        "lead_id, key_id). 'query' carries list pagination (offset, limit) and date range filters. "
        "'payload' carries request bodies for create/update/write operations."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[SmartleadOperation, ...]:
    if allowed is None:
        return build_smartlead_operation_catalog()
    seen: set[str] = set()
    selected: list[SmartleadOperation] = []
    for name in allowed:
        op = get_smartlead_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Smartlead credentials or a Smartlead client must be provided.")
    from harnessiq.providers.smartlead.client import SmartleadClient
    return SmartleadClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(
            f"Unsupported Smartlead operation '{value}'. Allowed: {allowed_str}."
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
    "build_smartlead_request_tool_definition",
    "create_smartlead_tools",
]


