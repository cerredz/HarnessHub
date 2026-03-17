"""Smartlead operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.smartlead.client import SmartleadCredentials

SMARTLEAD_REQUEST = "smartlead.request"
PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class SmartleadOperation:
    """Declarative metadata for one Smartlead API operation."""

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
class SmartleadPreparedRequest:
    """A validated Smartlead request ready for execution."""

    operation: SmartleadOperation
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
) -> tuple[str, SmartleadOperation]:
    return (
        name,
        SmartleadOperation(
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


_SMARTLEAD_CATALOG: OrderedDict[str, SmartleadOperation] = OrderedDict(
    (
        # Campaigns
        _op("list_campaigns", "Campaigns", "GET", "/campaigns/", allow_query=True),
        _op("get_campaign", "Campaigns", "GET", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),
        _op("create_campaign", "Campaigns", "POST", "/campaigns/create", payload_kind="object", payload_required=True),
        _op("update_campaign_status", "Campaigns", "PATCH", "/campaigns/{campaign_id}/status", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("update_campaign_schedule", "Campaigns", "POST", "/campaigns/{campaign_id}/schedule", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("update_campaign_settings", "Campaigns", "PATCH", "/campaigns/{campaign_id}/settings", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("delete_campaign", "Campaigns", "DELETE", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),

        # Sequences
        _op("get_campaign_sequences", "Sequences", "GET", "/campaigns/{campaign_id}/sequences", required_path_params=("campaign_id",)),
        _op("create_campaign_sequences", "Sequences", "POST", "/campaigns/{campaign_id}/sequences", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),

        # Email Accounts
        _op("list_email_accounts", "Email Accounts", "GET", "/email-accounts/", allow_query=True),
        _op("get_email_account", "Email Accounts", "GET", "/email-accounts/{email_account_id}/", required_path_params=("email_account_id",)),
        _op("save_email_account", "Email Accounts", "POST", "/email-accounts/save", payload_kind="object", payload_required=True),
        _op("update_email_account", "Email Accounts", "POST", "/email-accounts/{email_account_id}", required_path_params=("email_account_id",), payload_kind="object", payload_required=True),
        _op("update_email_account_warmup", "Email Accounts", "POST", "/email-accounts/{email_account_id}/warmup", required_path_params=("email_account_id",), payload_kind="object", payload_required=True),
        _op("get_email_account_warmup_stats", "Email Accounts", "GET", "/email-accounts/{email_account_id}/warmup-stats", required_path_params=("email_account_id",)),
        _op("list_campaign_email_accounts", "Email Accounts", "GET", "/campaigns/{campaign_id}/email-accounts", required_path_params=("campaign_id",)),
        _op("add_email_account_to_campaign", "Email Accounts", "POST", "/campaigns/{campaign_id}/email-accounts", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("remove_email_account_from_campaign", "Email Accounts", "DELETE", "/campaigns/{campaign_id}/email-accounts", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),

        # Leads
        _op("list_campaign_leads", "Leads", "GET", "/campaigns/{campaign_id}/leads", required_path_params=("campaign_id",), allow_query=True),
        _op("add_leads_to_campaign", "Leads", "POST", "/campaigns/{campaign_id}/leads", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("fetch_lead_by_email", "Leads", "GET", "/leads/", allow_query=True),
        _op("fetch_lead_categories", "Leads", "GET", "/leads/fetch-categories"),
        _op("fetch_global_leads", "Leads", "GET", "/leads/global-leads", allow_query=True),
        _op("get_lead_campaigns", "Leads", "GET", "/leads/{lead_id}/campaigns", required_path_params=("lead_id",)),
        _op("update_lead", "Leads", "POST", "/campaigns/{campaign_id}/leads/{lead_id}", required_path_params=("campaign_id", "lead_id"), payload_kind="object", payload_required=True),
        _op("pause_lead", "Leads", "POST", "/campaigns/{campaign_id}/leads/{lead_id}/pause", required_path_params=("campaign_id", "lead_id")),
        _op("resume_lead", "Leads", "POST", "/campaigns/{campaign_id}/leads/{lead_id}/resume", required_path_params=("campaign_id", "lead_id")),
        _op("delete_lead", "Leads", "DELETE", "/campaigns/{campaign_id}/leads/{lead_id}", required_path_params=("campaign_id", "lead_id")),
        _op("unsubscribe_lead_from_campaign", "Leads", "POST", "/campaigns/{campaign_id}/leads/{lead_id}/unsubscribe", required_path_params=("campaign_id", "lead_id")),
        _op("unsubscribe_lead_globally", "Leads", "POST", "/leads/{lead_id}/unsubscribe", required_path_params=("lead_id",)),
        _op("add_domain_to_block_list", "Leads", "POST", "/leads/add-domain-block-list", payload_kind="object", payload_required=True),

        # Master Inbox
        _op("get_message_history", "Master Inbox", "GET", "/campaigns/{campaign_id}/leads/{lead_id}/message-history", required_path_params=("campaign_id", "lead_id"), allow_query=True),
        _op("reply_to_lead", "Master Inbox", "POST", "/email-campaigns/send-email-thread", payload_kind="object", payload_required=True),
        _op("forward_reply", "Master Inbox", "POST", "/email-campaigns/forward-reply-email", payload_kind="object", payload_required=True),

        # Analytics
        _op("get_campaign_analytics", "Analytics", "GET", "/campaigns/{campaign_id}/analytics", required_path_params=("campaign_id",)),
        _op("get_campaign_analytics_by_date", "Analytics", "GET", "/campaigns/{campaign_id}/analytics-by-date", required_path_params=("campaign_id",), allow_query=True),
        _op("get_campaign_statistics", "Analytics", "GET", "/campaigns/{campaign_id}/statistics", required_path_params=("campaign_id",), allow_query=True),
        _op("get_campaign_lead_stats", "Analytics", "GET", "/campaigns/{campaign_id}/lead-stats", required_path_params=("campaign_id",)),
        _op("get_account_analytics", "Analytics", "GET", "/analytics/overview"),

        # Webhooks
        _op("list_campaign_webhooks", "Webhooks", "GET", "/campaigns/{campaign_id}/webhooks", required_path_params=("campaign_id",)),
        _op("save_campaign_webhook", "Webhooks", "POST", "/campaigns/{campaign_id}/webhooks", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("delete_campaign_webhook", "Webhooks", "DELETE", "/campaigns/{campaign_id}/webhooks", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),

        # Client Management
        _op("list_clients", "Clients", "GET", "/client/"),
        _op("save_client", "Clients", "POST", "/client/save", payload_kind="object", payload_required=True),
        _op("list_client_api_keys", "Clients", "GET", "/client/api-key", allow_query=True),
        _op("create_client_api_key", "Clients", "POST", "/client/api-key", payload_kind="object", payload_required=True),
        _op("delete_client_api_key", "Clients", "DELETE", "/client/api-key/{key_id}", required_path_params=("key_id",)),
        _op("reset_client_api_key", "Clients", "PUT", "/client/api-key/reset/{key_id}", required_path_params=("key_id",)),
    )
)


def build_smartlead_operation_catalog() -> tuple[SmartleadOperation, ...]:
    """Return the supported Smartlead operation catalog in stable order."""
    return tuple(_SMARTLEAD_CATALOG.values())


def get_smartlead_operation(operation_name: str) -> SmartleadOperation:
    """Return a supported Smartlead operation or raise a clear error."""
    op = _SMARTLEAD_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_SMARTLEAD_CATALOG)
        raise ValueError(
            f"Unsupported Smartlead operation '{operation_name}'. Available: {available}."
        )
    return op


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
                    "description": "Smartlead operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as campaign_id, email_account_id, lead_id, key_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for list and analytics operations (offset, limit, start_date, end_date).",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "JSON body for create, update, and delete operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_smartlead_tools(
    *,
    credentials: "SmartleadCredentials | None" = None,
    client: "Any | None" = None,
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

def _build_prepared_request(
    *,
    operation_name: str,
    credentials: "SmartleadCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> SmartleadPreparedRequest:
    from harnessiq.providers.smartlead.api import build_headers

    op = get_smartlead_operation(operation_name)
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

    # Inject api_key as query parameter (Smartlead auth mechanism)
    caller_query = {str(k): v for k, v in query.items()} if query else {}
    merged_query: dict[str, object] = {"api_key": credentials.api_key, **caller_query}

    full_url = join_url(credentials.base_url, path, query=merged_query)  # type: ignore[arg-type]
    headers = build_headers()

    return SmartleadPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


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


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.smartlead.client import SmartleadClient
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Smartlead credentials or a Smartlead client must be provided.")
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


def _build_tool_description(operations: Sequence[SmartleadOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Smartlead cold email outreach API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append(
        "Use 'path_params' for resource ids (campaign_id, email_account_id, lead_id, key_id). "
        "'query' for list pagination and date filters. 'payload' for request bodies."
    )
    return "\n".join(lines)


__all__ = [
    "SMARTLEAD_REQUEST",
    "SmartleadOperation",
    "SmartleadPreparedRequest",
    "_build_prepared_request",
    "build_smartlead_operation_catalog",
    "build_smartlead_request_tool_definition",
    "create_smartlead_tools",
    "get_smartlead_operation",
]
