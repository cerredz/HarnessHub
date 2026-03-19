"""Expandi operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.expandi.client import ExpandiCredentials

EXPANDI_REQUEST = "expandi.request"
PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class ExpandiOperation:
    """Declarative metadata for one Expandi API operation."""

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
class ExpandiPreparedRequest:
    """A validated Expandi request ready for execution."""

    operation: ExpandiOperation
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
) -> tuple[str, ExpandiOperation]:
    return (
        name,
        ExpandiOperation(
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


_EXPANDI_CATALOG: OrderedDict[str, ExpandiOperation] = OrderedDict(
    (
        # Campaigns (v1)
        _op("list_campaigns", "Campaigns", "GET", "/open-api/campaigns/"),
        _op("add_prospect_to_campaign", "Campaigns", "POST", "/open-api/campaign-instance/{campaign_id}/assign/", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("add_multiple_prospects_to_campaign", "Campaigns", "POST", "/open-api/campaign-instance/{campaign_id}/assign_multiple/", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("pause_campaign_contact", "Campaigns", "GET", "/open-api/campaign-contact/{contact_id}/pause/", required_path_params=("contact_id",)),
        _op("resume_campaign_contact", "Campaigns", "GET", "/open-api/campaign-contact/{contact_id}/resume/", required_path_params=("contact_id",)),

        # Campaign Contacts v2
        _op("create_campaign_contact_v2", "Campaign Contacts", "POST", "/open-api/v2/li_accounts/campaign_instances/{campaign_id}/create_contact/", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("update_campaign_contact_v2", "Campaign Contacts", "PATCH", "/open-api/v2/li_accounts/campaign_instances/{campaign_id}/update_contact/", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("delete_campaign_contact_v2", "Campaign Contacts", "DELETE", "/open-api/v2/li_accounts/campaign_instances/{campaign_id}/delete_contact/", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),

        # LinkedIn Accounts
        _op("list_linkedin_accounts", "LinkedIn Accounts", "GET", "/open-api/fetch_li_accounts/"),
        _op("list_linkedin_accounts_v2", "LinkedIn Accounts", "GET", "/open-api/v2/li_accounts/", allow_query=True),
        _op("send_connection_request", "LinkedIn Accounts", "POST", "/open-api/v2/li_accounts/{account_id}/actions/connection_request/", required_path_params=("account_id",), payload_kind="object", payload_required=True),
        _op("send_message", "LinkedIn Accounts", "POST", "/open-api/v2/li_accounts/{account_id}/actions/message/", required_path_params=("account_id",), payload_kind="object", payload_required=True),
        _op("send_email", "LinkedIn Accounts", "POST", "/open-api/v2/li_accounts/{account_id}/actions/email/", required_path_params=("account_id",), payload_kind="object", payload_required=True),
        _op("check_action_status", "LinkedIn Accounts", "POST", "/open-api/v2/li_accounts/actions/{action_id}/check_action_status/", required_path_params=("action_id",), payload_kind="object", payload_required=True),

        # Messaging (v1)
        _op("fetch_messages", "Messaging", "GET", "/open-api/fetch_messages/"),
        _op("fetch_messages_for_contact", "Messaging", "GET", "/open-api/fetch_messages_contact/"),
        _op("send_message_to_contact", "Messaging", "POST", "/open-api/send_message_to_contact", payload_kind="object", payload_required=True),
        _op("reply_to_message", "Messaging", "POST", "/open-api/reply/", payload_kind="object", payload_required=True),

        # Webhooks
        _op("enable_messaging_webhook", "Webhooks", "POST", "/open-api/li_accounts/messaging/webhooks/enable", payload_kind="object", payload_required=True),
        _op("disable_messaging_webhook", "Webhooks", "POST", "/open-api/li_accounts/messaging/webhooks/disable", payload_kind="object", payload_required=True),

        # Miscellaneous
        _op("add_to_blacklist", "Miscellaneous", "POST", "/open-api/blacklist/", payload_kind="object", payload_required=True),
        _op("fetch_contacts", "Miscellaneous", "GET", "/open-api/fetch_contacts/"),
    )
)


def build_expandi_operation_catalog() -> tuple[ExpandiOperation, ...]:
    """Return the supported Expandi operation catalog in stable order."""
    return tuple(_EXPANDI_CATALOG.values())


def get_expandi_operation(operation_name: str) -> ExpandiOperation:
    """Return a supported Expandi operation or raise a clear error."""
    op = _EXPANDI_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_EXPANDI_CATALOG)
        raise ValueError(
            f"Unsupported Expandi operation '{operation_name}'. Available: {available}."
        )
    return op


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
                    "description": "Expandi operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as campaign_id, contact_id, account_id, action_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters (e.g. workspace_id, page for list_linkedin_accounts_v2).",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "JSON body for POST/PATCH/DELETE operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_expandi_tools(
    *,
    credentials: "ExpandiCredentials | None" = None,
    client: "Any | None" = None,
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

def _build_prepared_request(
    *,
    operation_name: str,
    credentials: "ExpandiCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> ExpandiPreparedRequest:
    from harnessiq.providers.expandi.api import build_headers

    op = get_expandi_operation(operation_name)
    normalized_params = {str(k): str(v) for k, v in (path_params or {}).items()}
    missing = [k for k in op.required_path_params if not normalized_params.get(k)]
    if missing:
        raise ValueError(
            f"Operation '{op.name}' requires path parameters: {', '.join(missing)}."
        )

    if op.payload_kind == "none" and payload is not None:
        raise ValueError(f"Operation '{op.name}' does not accept a payload.")
    if op.payload_required and payload is None:
        raise ValueError(f"Operation '{op.name}' requires a payload.")

    path = op.path_hint
    for key, value in normalized_params.items():
        path = path.replace(f"{{{key}}}", quote(value, safe=""))

    # Inject key + secret as query parameters (Expandi auth mechanism)
    caller_query = {str(k): v for k, v in query.items()} if query else {}
    merged_query: dict[str, object] = {
        "key": credentials.api_key,
        "secret": credentials.api_secret,
        **caller_query,
    }

    full_url = join_url(credentials.base_url, path, query=merged_query)  # type: ignore[arg-type]
    headers = build_headers()

    return ExpandiPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


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


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.expandi.client import ExpandiClient
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Expandi credentials or an Expandi client must be provided.")
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


def _build_tool_description(operations: Sequence[ExpandiOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Expandi LinkedIn outreach automation API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append(
        "Use 'path_params' for resource ids (campaign_id, contact_id, account_id, action_id). "
        "'query' for list filters. 'payload' for prospect data and message bodies."
    )
    return "\n".join(lines)


__all__ = [
    "EXPANDI_REQUEST",
    "ExpandiOperation",
    "ExpandiPreparedRequest",
    "_build_prepared_request",
    "build_expandi_operation_catalog",
    "build_expandi_request_tool_definition",
    "create_expandi_tools",
    "get_expandi_operation",
]
