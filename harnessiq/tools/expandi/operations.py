"""Expandi MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.interfaces import RequestPreparingClient

from harnessiq.providers.expandi.operations import (
    ExpandiOperation,
    build_expandi_operation_catalog,
    get_expandi_operation,
)
from harnessiq.shared.tools import EXPANDI_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.expandi.client import ExpandiClient, ExpandiCredentials


def build_expandi_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Expandi request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=EXPANDI_REQUEST,
        name="expandi_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Expandi operation to execute. Use 'list_campaigns' to see all campaigns. "
                        "Use 'add_prospect_to_campaign' to enroll a LinkedIn profile into a campaign "
                        "(payload: {profile_link, company_name, custom_placeholder}). "
                        "Use 'send_connection_request' or 'send_message' to interact with LinkedIn "
                        "connections via a specific LinkedIn account. Use 'enable_messaging_webhook' "
                        "to subscribe to real-time conversation events."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": (
                        "Path parameters for resource operations. "
                        "Supported keys: campaign_id, contact_id, account_id, action_id."
                    ),
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": (
                        "Optional query parameters. For 'list_linkedin_accounts_v2': "
                        "{workspace_id (opt), page (opt)}."
                    ),
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "JSON body for write operations. "
                        "add_prospect_to_campaign: {profile_link, company_name (opt), custom_placeholder (opt)}. "
                        "send_connection_request: {profile_link, body (opt), ignore_campaigns (opt)}. "
                        "send_message: {profile_link, body}. "
                        "send_email: {profile_link, subject, body}. "
                        "create_campaign_contact_v2: {profile_link, placeholders (obj)}. "
                        "enable_messaging_webhook: {target (URL), li_account_ids, source}."
                    ),
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_expandi_tools(
    *,
    credentials: "ExpandiCredentials | None" = None,
    client: "RequestPreparingClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Expandi request tool backed by the provided client."""
    expandi_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_expandi_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = expandi_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = expandi_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=expandi_client.credentials.timeout_seconds,
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

def _build_tool_description(operations: Sequence[ExpandiOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Expandi LinkedIn outreach automation API operations.",
        "",
        "Expandi is a LinkedIn automation platform for safe, human-like outreach at scale. "
        "Use it to manage LinkedIn campaigns, enroll prospects by LinkedIn profile URL, "
        "pause or resume individual campaign contacts, send connection requests and messages "
        "via linked LinkedIn accounts, manage messaging webhooks for real-time conversation "
        "monitoring, and maintain a blacklist of excluded profiles.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: 'path_params' carries resource ids (campaign_id, contact_id, "
        "account_id, action_id). 'payload' carries the request body (prospect data, message "
        "content, webhook config). Auth (key + secret) is injected automatically."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[ExpandiOperation, ...]:
    if allowed is None:
        return build_expandi_operation_catalog()
    seen: set[str] = set()
    selected: list[ExpandiOperation] = []
    for name in allowed:
        op = get_expandi_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Expandi credentials or an Expandi client must be provided.")
    from harnessiq.providers.expandi.client import ExpandiClient
    return ExpandiClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(
            f"Unsupported Expandi operation '{value}'. Allowed: {allowed_str}."
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
    "build_expandi_request_tool_definition",
    "create_expandi_tools",
]

