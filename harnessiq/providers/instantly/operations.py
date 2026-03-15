"""Instantly operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.instantly.client import InstantlyCredentials

INSTANTLY_REQUEST = "instantly.request"
PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class InstantlyOperation:
    """Declarative metadata for one Instantly API operation."""

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
class InstantlyPreparedRequest:
    """A validated Instantly request ready for execution."""

    operation: InstantlyOperation
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
) -> tuple[str, InstantlyOperation]:
    return (
        name,
        InstantlyOperation(
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


_INSTANTLY_CATALOG: OrderedDict[str, InstantlyOperation] = OrderedDict(
    (
        # Account
        _op("list_accounts", "Account", "GET", "/accounts"),
        _op("get_account", "Account", "GET", "/accounts/{account_id}", required_path_params=("account_id",)),
        _op("create_account", "Account", "POST", "/accounts", payload_kind="object", payload_required=True),
        _op("update_account", "Account", "PATCH", "/accounts/{account_id}", required_path_params=("account_id",), payload_kind="object", payload_required=True),
        _op("delete_account", "Account", "DELETE", "/accounts/{account_id}", required_path_params=("account_id",)),
        _op("test_account_vitals", "Account", "GET", "/accounts/{account_id}/vitals", required_path_params=("account_id",)),
        _op("get_account_warmup_analytics", "Account", "GET", "/accounts/{account_id}/warmup-analytics", required_path_params=("account_id",)),
        # Account Campaign Mapping
        _op("list_account_campaign_mappings", "Account Campaign Mapping", "GET", "/account-campaign-mappings", allow_query=True),
        _op("create_account_campaign_mapping", "Account Campaign Mapping", "POST", "/account-campaign-mappings", payload_kind="object", payload_required=True),
        _op("delete_account_campaign_mapping", "Account Campaign Mapping", "DELETE", "/account-campaign-mappings/{mapping_id}", required_path_params=("mapping_id",)),
        # Analytics
        _op("get_campaign_summary", "Analytics", "GET", "/analytics/campaign-summary", allow_query=True),
        _op("get_campaign_step_summary", "Analytics", "GET", "/analytics/campaign-step-summary", allow_query=True),
        _op("get_account_summary", "Analytics", "GET", "/analytics/account-summary", allow_query=True),
        # API Key
        _op("list_api_keys", "API Key", "GET", "/api-keys"),
        _op("create_api_key", "API Key", "POST", "/api-keys", payload_kind="object", payload_required=True),
        _op("update_api_key", "API Key", "PATCH", "/api-keys/{key_id}", required_path_params=("key_id",), payload_kind="object", payload_required=True),
        _op("delete_api_key", "API Key", "DELETE", "/api-keys/{key_id}", required_path_params=("key_id",)),
        # Audit Log
        _op("list_audit_logs", "Audit Log", "GET", "/audit-logs", allow_query=True),
        # Background Job
        _op("get_background_job", "Background Job", "GET", "/background-jobs/{job_id}", required_path_params=("job_id",)),
        # Block List Entry
        _op("list_block_list_entries", "Block List Entry", "GET", "/block-list", allow_query=True),
        _op("create_block_list_entry", "Block List Entry", "POST", "/block-list", payload_kind="object", payload_required=True),
        _op("delete_block_list_entry", "Block List Entry", "DELETE", "/block-list/{entry_id}", required_path_params=("entry_id",)),
        # Campaign
        _op("list_campaigns", "Campaign", "GET", "/campaigns", allow_query=True),
        _op("get_campaign", "Campaign", "GET", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),
        _op("create_campaign", "Campaign", "POST", "/campaigns", payload_kind="object", payload_required=True),
        _op("update_campaign", "Campaign", "PATCH", "/campaigns/{campaign_id}", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("delete_campaign", "Campaign", "DELETE", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),
        _op("launch_campaign", "Campaign", "POST", "/campaigns/{campaign_id}/launch", required_path_params=("campaign_id",)),
        _op("pause_campaign", "Campaign", "POST", "/campaigns/{campaign_id}/pause", required_path_params=("campaign_id",)),
        # Campaign Subsequence
        _op("list_subsequences", "Campaign Subsequence", "GET", "/campaign-subsequences", allow_query=True),
        _op("get_subsequence", "Campaign Subsequence", "GET", "/campaign-subsequences/{subsequence_id}", required_path_params=("subsequence_id",)),
        _op("create_subsequence", "Campaign Subsequence", "POST", "/campaign-subsequences", payload_kind="object", payload_required=True),
        _op("update_subsequence", "Campaign Subsequence", "PATCH", "/campaign-subsequences/{subsequence_id}", required_path_params=("subsequence_id",), payload_kind="object", payload_required=True),
        _op("delete_subsequence", "Campaign Subsequence", "DELETE", "/campaign-subsequences/{subsequence_id}", required_path_params=("subsequence_id",)),
        # Custom Tag
        _op("list_custom_tags", "Custom Tag", "GET", "/custom-tags", allow_query=True),
        _op("create_custom_tag", "Custom Tag", "POST", "/custom-tags", payload_kind="object", payload_required=True),
        _op("update_custom_tag", "Custom Tag", "PATCH", "/custom-tags/{tag_id}", required_path_params=("tag_id",), payload_kind="object", payload_required=True),
        _op("delete_custom_tag", "Custom Tag", "DELETE", "/custom-tags/{tag_id}", required_path_params=("tag_id",)),
        # Custom Tag Mapping
        _op("list_custom_tag_mappings", "Custom Tag Mapping", "GET", "/custom-tag-mappings", allow_query=True),
        _op("create_custom_tag_mapping", "Custom Tag Mapping", "POST", "/custom-tag-mappings", payload_kind="object", payload_required=True),
        _op("delete_custom_tag_mapping", "Custom Tag Mapping", "DELETE", "/custom-tag-mappings/{mapping_id}", required_path_params=("mapping_id",)),
        # Email
        _op("list_emails", "Email", "GET", "/emails", allow_query=True),
        _op("get_email", "Email", "GET", "/emails/{email_id}", required_path_params=("email_id",)),
        _op("list_email_replies", "Email", "GET", "/emails/{email_id}/replies", required_path_params=("email_id",)),
        _op("mark_email_as_read", "Email", "POST", "/emails/{email_id}/mark-as-read", required_path_params=("email_id",)),
        _op("reply_to_email", "Email", "POST", "/emails/{email_id}/reply", required_path_params=("email_id",), payload_kind="object", payload_required=True),
        # Email Verification
        _op("verify_email", "Email Verification", "POST", "/email-verification", payload_kind="object", payload_required=True),
        # Inbox Placement Test
        _op("list_inbox_placement_tests", "Inbox Placement Test", "GET", "/inbox-placement-tests", allow_query=True),
        _op("get_inbox_placement_test", "Inbox Placement Test", "GET", "/inbox-placement-tests/{test_id}", required_path_params=("test_id",)),
        _op("create_inbox_placement_test", "Inbox Placement Test", "POST", "/inbox-placement-tests", payload_kind="object", payload_required=True),
        # Lead
        _op("list_leads", "Lead", "GET", "/leads", allow_query=True),
        _op("get_lead", "Lead", "GET", "/leads/{lead_id}", required_path_params=("lead_id",)),
        _op("create_lead", "Lead", "POST", "/leads", payload_kind="object", payload_required=True),
        _op("update_lead", "Lead", "PATCH", "/leads/{lead_id}", required_path_params=("lead_id",), payload_kind="object", payload_required=True),
        _op("delete_lead", "Lead", "DELETE", "/leads/{lead_id}", required_path_params=("lead_id",)),
        _op("move_lead", "Lead", "POST", "/leads/{lead_id}/move", required_path_params=("lead_id",), payload_kind="object", payload_required=True),
        _op("set_lead_interest", "Lead", "POST", "/leads/{lead_id}/interest", required_path_params=("lead_id",), payload_kind="object", payload_required=True),
        # Lead Label
        _op("list_lead_labels", "Lead Label", "GET", "/lead-labels", allow_query=True),
        _op("create_lead_label", "Lead Label", "POST", "/lead-labels", payload_kind="object", payload_required=True),
        _op("update_lead_label", "Lead Label", "PATCH", "/lead-labels/{label_id}", required_path_params=("label_id",), payload_kind="object", payload_required=True),
        _op("delete_lead_label", "Lead Label", "DELETE", "/lead-labels/{label_id}", required_path_params=("label_id",)),
        # Lead List
        _op("list_lead_lists", "Lead List", "GET", "/lead-lists", allow_query=True),
        _op("get_lead_list", "Lead List", "GET", "/lead-lists/{list_id}", required_path_params=("list_id",)),
        _op("create_lead_list", "Lead List", "POST", "/lead-lists", payload_kind="object", payload_required=True),
        _op("update_lead_list", "Lead List", "PATCH", "/lead-lists/{list_id}", required_path_params=("list_id",), payload_kind="object", payload_required=True),
        _op("delete_lead_list", "Lead List", "DELETE", "/lead-lists/{list_id}", required_path_params=("list_id",)),
        # Webhook
        _op("list_webhooks", "Webhook", "GET", "/webhooks", allow_query=True),
        _op("get_webhook", "Webhook", "GET", "/webhooks/{webhook_id}", required_path_params=("webhook_id",)),
        _op("create_webhook", "Webhook", "POST", "/webhooks", payload_kind="object", payload_required=True),
        _op("update_webhook", "Webhook", "PATCH", "/webhooks/{webhook_id}", required_path_params=("webhook_id",), payload_kind="object", payload_required=True),
        _op("delete_webhook", "Webhook", "DELETE", "/webhooks/{webhook_id}", required_path_params=("webhook_id",)),
        # Webhook Event
        _op("list_webhook_events", "Webhook Event", "GET", "/webhook-events", allow_query=True),
        _op("get_webhook_event", "Webhook Event", "GET", "/webhook-events/{event_id}", required_path_params=("event_id",)),
        # Workspace
        _op("get_workspace", "Workspace", "GET", "/workspace"),
        _op("update_workspace", "Workspace", "PATCH", "/workspace", payload_kind="object", payload_required=True),
    )
)


def build_instantly_operation_catalog() -> tuple[InstantlyOperation, ...]:
    """Return the supported Instantly operation catalog in stable order."""
    return tuple(_INSTANTLY_CATALOG.values())


def get_instantly_operation(operation_name: str) -> InstantlyOperation:
    """Return a supported Instantly operation or raise a clear error."""
    op = _INSTANTLY_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_INSTANTLY_CATALOG)
        raise ValueError(f"Unsupported Instantly operation '{operation_name}'. Available: {available}.")
    return op


def build_instantly_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Instantly request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=INSTANTLY_REQUEST,
        name="instantly_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Instantly operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as account_id, campaign_id, lead_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for paginated list operations.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "Optional JSON body for create/update operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_instantly_tools(
    *,
    credentials: "InstantlyCredentials | None" = None,
    client: "Any | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Instantly request tool backed by the provided client."""
    instantly_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_instantly_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = instantly_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = instantly_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=instantly_client.credentials.timeout_seconds,
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
    credentials: "InstantlyCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> InstantlyPreparedRequest:
    from harnessiq.providers.instantly.api import build_headers

    op = get_instantly_operation(operation_name)
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

    return InstantlyPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


def _select_operations(allowed: Sequence[str] | None) -> tuple[InstantlyOperation, ...]:
    if allowed is None:
        return build_instantly_operation_catalog()
    seen: set[str] = set()
    selected: list[InstantlyOperation] = []
    for name in allowed:
        op = get_instantly_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.instantly.client import InstantlyClient
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Instantly credentials or an Instantly client must be provided.")
    return InstantlyClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        raise ValueError(f"Unsupported Instantly operation '{value}'.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


def _build_tool_description(operations: Sequence[InstantlyOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Instantly email outreach API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append("Use 'path_params' for resource ids, 'query' for paginated lists, 'payload' for JSON bodies.")
    return "\n".join(lines)


__all__ = [
    "INSTANTLY_REQUEST",
    "InstantlyOperation",
    "InstantlyPreparedRequest",
    "_build_prepared_request",
    "build_instantly_operation_catalog",
    "build_instantly_request_tool_definition",
    "create_instantly_tools",
    "get_instantly_operation",
]
