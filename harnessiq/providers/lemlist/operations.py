"""Lemlist operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.lemlist.client import LemlistCredentials

LEMLIST_REQUEST = "lemlist.request"
PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class LemlistOperation:
    """Declarative metadata for one Lemlist API operation."""

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
class LemlistPreparedRequest:
    """A validated Lemlist request ready for execution."""

    operation: LemlistOperation
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
) -> tuple[str, LemlistOperation]:
    return (
        name,
        LemlistOperation(
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


_LEMLIST_CATALOG: OrderedDict[str, LemlistOperation] = OrderedDict(
    (
        # Team
        _op("get_team", "Team", "GET", "/team"),
        # Campaigns
        _op("list_campaigns", "Campaign", "GET", "/campaigns"),
        _op("get_campaign", "Campaign", "GET", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),
        _op("create_campaign", "Campaign", "POST", "/campaigns", payload_kind="object", payload_required=True),
        _op("update_campaign", "Campaign", "PATCH", "/campaigns/{campaign_id}", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("delete_campaign", "Campaign", "DELETE", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),
        _op("export_campaign_results", "Campaign", "GET", "/campaigns/{campaign_id}/export", required_path_params=("campaign_id",), allow_query=True),
        # Campaign Stats
        _op("get_campaign_stats", "Campaign Stats", "GET", "/campaigns/{campaign_id}/stats", required_path_params=("campaign_id",)),
        # Leads (within campaigns)
        _op("list_campaign_leads", "Campaign Lead", "GET", "/campaigns/{campaign_id}/leads", required_path_params=("campaign_id",), allow_query=True),
        _op("get_campaign_lead", "Campaign Lead", "GET", "/campaigns/{campaign_id}/leads/{lead_id}", required_path_params=("campaign_id", "lead_id")),
        _op("add_lead_to_campaign", "Campaign Lead", "POST", "/campaigns/{campaign_id}/leads/{lead_id}", required_path_params=("campaign_id", "lead_id"), payload_kind="object"),
        _op("delete_lead_from_campaign", "Campaign Lead", "DELETE", "/campaigns/{campaign_id}/leads/{lead_id}", required_path_params=("campaign_id", "lead_id")),
        _op("unsubscribe_lead_from_campaign", "Campaign Lead", "DELETE", "/campaigns/{campaign_id}/leads/{lead_id}/unsubscribe", required_path_params=("campaign_id", "lead_id")),
        # Leads (global)
        _op("list_leads", "Lead", "GET", "/leads", allow_query=True),
        _op("get_lead", "Lead", "GET", "/leads/{lead_id}", required_path_params=("lead_id",)),
        _op("create_lead", "Lead", "POST", "/leads", payload_kind="object", payload_required=True),
        _op("update_lead", "Lead", "PATCH", "/leads/{lead_id}", required_path_params=("lead_id",), payload_kind="object", payload_required=True),
        _op("delete_lead", "Lead", "DELETE", "/leads/{lead_id}", required_path_params=("lead_id",)),
        _op("unsubscribe_lead", "Lead", "DELETE", "/leads/{lead_id}/unsubscribe", required_path_params=("lead_id",)),
        # Lead Activities
        _op("list_lead_activities", "Lead Activity", "GET", "/leads/{lead_id}/activities", required_path_params=("lead_id",), allow_query=True),
        # Sender Identities
        _op("list_sender_identities", "Sender Identity", "GET", "/sender-identities"),
        _op("get_sender_identity", "Sender Identity", "GET", "/sender-identities/{identity_id}", required_path_params=("identity_id",)),
        # Inboxes
        _op("list_inboxes", "Inbox", "GET", "/inboxes"),
        # Hooks (Webhooks)
        _op("list_hooks", "Hook", "GET", "/hooks"),
        _op("get_hook", "Hook", "GET", "/hooks/{hook_id}", required_path_params=("hook_id",)),
        _op("create_hook", "Hook", "POST", "/hooks", payload_kind="object", payload_required=True),
        _op("update_hook", "Hook", "PATCH", "/hooks/{hook_id}", required_path_params=("hook_id",), payload_kind="object", payload_required=True),
        _op("delete_hook", "Hook", "DELETE", "/hooks/{hook_id}", required_path_params=("hook_id",)),
        # Unsubscribes
        _op("list_unsubscribes", "Unsubscribe", "GET", "/unsubscribes", allow_query=True),
        _op("add_unsubscribe", "Unsubscribe", "POST", "/unsubscribes", payload_kind="object", payload_required=True),
        _op("delete_unsubscribe", "Unsubscribe", "DELETE", "/unsubscribes/{email}", required_path_params=("email",)),
        # DNS Checks
        _op("check_dns", "DNS", "GET", "/dns-check"),
        # Activity Feed
        _op("get_activity_feed", "Activity", "GET", "/activities", allow_query=True),
        # Enrichment
        _op("enrich_lead", "Enrichment", "POST", "/leads/{lead_id}/enrich", required_path_params=("lead_id",), payload_kind="object"),
    )
)


def build_lemlist_operation_catalog() -> tuple[LemlistOperation, ...]:
    """Return the supported Lemlist operation catalog in stable order."""
    return tuple(_LEMLIST_CATALOG.values())


def get_lemlist_operation(operation_name: str) -> LemlistOperation:
    """Return a supported Lemlist operation or raise a clear error."""
    op = _LEMLIST_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_LEMLIST_CATALOG)
        raise ValueError(f"Unsupported Lemlist operation '{operation_name}'. Available: {available}.")
    return op


def build_lemlist_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Lemlist request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=LEMLIST_REQUEST,
        name="lemlist_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Lemlist operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as campaign_id, lead_id, hook_id.",
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


def create_lemlist_tools(
    *,
    credentials: "LemlistCredentials | None" = None,
    client: "Any | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Lemlist request tool backed by the provided client."""
    lemlist_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_lemlist_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = lemlist_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = lemlist_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=lemlist_client.credentials.timeout_seconds,
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
    credentials: "LemlistCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> LemlistPreparedRequest:
    from harnessiq.providers.lemlist.api import build_headers

    op = get_lemlist_operation(operation_name)
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

    return LemlistPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


def _select_operations(allowed: Sequence[str] | None) -> tuple[LemlistOperation, ...]:
    if allowed is None:
        return build_lemlist_operation_catalog()
    seen: set[str] = set()
    selected: list[LemlistOperation] = []
    for name in allowed:
        op = get_lemlist_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.lemlist.client import LemlistClient
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Lemlist credentials or a Lemlist client must be provided.")
    return LemlistClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        raise ValueError(f"Unsupported Lemlist operation '{value}'.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


def _build_tool_description(operations: Sequence[LemlistOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Lemlist cold email outreach API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append("Use 'path_params' for resource ids, 'query' for paginated lists, 'payload' for JSON bodies.")
    return "\n".join(lines)


__all__ = [
    "LEMLIST_REQUEST",
    "LemlistOperation",
    "LemlistPreparedRequest",
    "_build_prepared_request",
    "build_lemlist_operation_catalog",
    "build_lemlist_request_tool_definition",
    "create_lemlist_tools",
    "get_lemlist_operation",
]
