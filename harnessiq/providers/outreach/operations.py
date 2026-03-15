"""Outreach operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.outreach.client import OutreachCredentials

OUTREACH_REQUEST = "outreach.request"
PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class OutreachOperation:
    """Declarative metadata for one Outreach API operation."""

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
class OutreachPreparedRequest:
    """A validated Outreach request ready for execution."""

    operation: OutreachOperation
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
) -> tuple[str, OutreachOperation]:
    return (
        name,
        OutreachOperation(
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


_OUTREACH_CATALOG: OrderedDict[str, OutreachOperation] = OrderedDict(
    (
        # Prospects
        _op("list_prospects", "Prospect", "GET", "/prospects", allow_query=True),
        _op("get_prospect", "Prospect", "GET", "/prospects/{prospect_id}", required_path_params=("prospect_id",)),
        _op("create_prospect", "Prospect", "POST", "/prospects", payload_kind="object", payload_required=True),
        _op("update_prospect", "Prospect", "PATCH", "/prospects/{prospect_id}", required_path_params=("prospect_id",), payload_kind="object", payload_required=True),
        _op("delete_prospect", "Prospect", "DELETE", "/prospects/{prospect_id}", required_path_params=("prospect_id",)),
        # Accounts
        _op("list_accounts", "Account", "GET", "/accounts", allow_query=True),
        _op("get_account", "Account", "GET", "/accounts/{account_id}", required_path_params=("account_id",)),
        _op("create_account", "Account", "POST", "/accounts", payload_kind="object", payload_required=True),
        _op("update_account", "Account", "PATCH", "/accounts/{account_id}", required_path_params=("account_id",), payload_kind="object", payload_required=True),
        _op("delete_account", "Account", "DELETE", "/accounts/{account_id}", required_path_params=("account_id",)),
        # Sequences
        _op("list_sequences", "Sequence", "GET", "/sequences", allow_query=True),
        _op("get_sequence", "Sequence", "GET", "/sequences/{sequence_id}", required_path_params=("sequence_id",)),
        _op("create_sequence", "Sequence", "POST", "/sequences", payload_kind="object", payload_required=True),
        _op("update_sequence", "Sequence", "PATCH", "/sequences/{sequence_id}", required_path_params=("sequence_id",), payload_kind="object", payload_required=True),
        _op("delete_sequence", "Sequence", "DELETE", "/sequences/{sequence_id}", required_path_params=("sequence_id",)),
        # Sequence States
        _op("list_sequence_states", "Sequence State", "GET", "/sequenceStates", allow_query=True),
        _op("get_sequence_state", "Sequence State", "GET", "/sequenceStates/{sequence_state_id}", required_path_params=("sequence_state_id",)),
        _op("create_sequence_state", "Sequence State", "POST", "/sequenceStates", payload_kind="object", payload_required=True),
        _op("delete_sequence_state", "Sequence State", "DELETE", "/sequenceStates/{sequence_state_id}", required_path_params=("sequence_state_id",)),
        # Sequence Steps
        _op("list_sequence_steps", "Sequence Step", "GET", "/sequenceSteps", allow_query=True),
        _op("get_sequence_step", "Sequence Step", "GET", "/sequenceSteps/{sequence_step_id}", required_path_params=("sequence_step_id",)),
        _op("create_sequence_step", "Sequence Step", "POST", "/sequenceSteps", payload_kind="object", payload_required=True),
        _op("update_sequence_step", "Sequence Step", "PATCH", "/sequenceSteps/{sequence_step_id}", required_path_params=("sequence_step_id",), payload_kind="object", payload_required=True),
        _op("delete_sequence_step", "Sequence Step", "DELETE", "/sequenceSteps/{sequence_step_id}", required_path_params=("sequence_step_id",)),
        # Opportunities
        _op("list_opportunities", "Opportunity", "GET", "/opportunities", allow_query=True),
        _op("get_opportunity", "Opportunity", "GET", "/opportunities/{opportunity_id}", required_path_params=("opportunity_id",)),
        _op("create_opportunity", "Opportunity", "POST", "/opportunities", payload_kind="object", payload_required=True),
        _op("update_opportunity", "Opportunity", "PATCH", "/opportunities/{opportunity_id}", required_path_params=("opportunity_id",), payload_kind="object", payload_required=True),
        _op("delete_opportunity", "Opportunity", "DELETE", "/opportunities/{opportunity_id}", required_path_params=("opportunity_id",)),
        # Tasks
        _op("list_tasks", "Task", "GET", "/tasks", allow_query=True),
        _op("get_task", "Task", "GET", "/tasks/{task_id}", required_path_params=("task_id",)),
        _op("create_task", "Task", "POST", "/tasks", payload_kind="object", payload_required=True),
        _op("update_task", "Task", "PATCH", "/tasks/{task_id}", required_path_params=("task_id",), payload_kind="object", payload_required=True),
        _op("delete_task", "Task", "DELETE", "/tasks/{task_id}", required_path_params=("task_id",)),
        # Calls
        _op("list_calls", "Call", "GET", "/calls", allow_query=True),
        _op("get_call", "Call", "GET", "/calls/{call_id}", required_path_params=("call_id",)),
        _op("create_call", "Call", "POST", "/calls", payload_kind="object", payload_required=True),
        _op("update_call", "Call", "PATCH", "/calls/{call_id}", required_path_params=("call_id",), payload_kind="object", payload_required=True),
        _op("delete_call", "Call", "DELETE", "/calls/{call_id}", required_path_params=("call_id",)),
        # Mailboxes
        _op("list_mailboxes", "Mailbox", "GET", "/mailboxes", allow_query=True),
        _op("get_mailbox", "Mailbox", "GET", "/mailboxes/{mailbox_id}", required_path_params=("mailbox_id",)),
        _op("update_mailbox", "Mailbox", "PATCH", "/mailboxes/{mailbox_id}", required_path_params=("mailbox_id",), payload_kind="object", payload_required=True),
        # Templates
        _op("list_templates", "Template", "GET", "/templates", allow_query=True),
        _op("get_template", "Template", "GET", "/templates/{template_id}", required_path_params=("template_id",)),
        _op("create_template", "Template", "POST", "/templates", payload_kind="object", payload_required=True),
        _op("update_template", "Template", "PATCH", "/templates/{template_id}", required_path_params=("template_id",), payload_kind="object", payload_required=True),
        _op("delete_template", "Template", "DELETE", "/templates/{template_id}", required_path_params=("template_id",)),
        # Users
        _op("list_users", "User", "GET", "/users", allow_query=True),
        _op("get_user", "User", "GET", "/users/{user_id}", required_path_params=("user_id",)),
        _op("update_user", "User", "PATCH", "/users/{user_id}", required_path_params=("user_id",), payload_kind="object", payload_required=True),
        # Webhooks
        _op("list_webhooks", "Webhook", "GET", "/webhooks", allow_query=True),
        _op("get_webhook", "Webhook", "GET", "/webhooks/{webhook_id}", required_path_params=("webhook_id",)),
        _op("create_webhook", "Webhook", "POST", "/webhooks", payload_kind="object", payload_required=True),
        _op("update_webhook", "Webhook", "PATCH", "/webhooks/{webhook_id}", required_path_params=("webhook_id",), payload_kind="object", payload_required=True),
        _op("delete_webhook", "Webhook", "DELETE", "/webhooks/{webhook_id}", required_path_params=("webhook_id",)),
        # Calls Dispositions
        _op("list_call_dispositions", "Call Disposition", "GET", "/callDispositions", allow_query=True),
        _op("get_call_disposition", "Call Disposition", "GET", "/callDispositions/{disposition_id}", required_path_params=("disposition_id",)),
        _op("create_call_disposition", "Call Disposition", "POST", "/callDispositions", payload_kind="object", payload_required=True),
        _op("update_call_disposition", "Call Disposition", "PATCH", "/callDispositions/{disposition_id}", required_path_params=("disposition_id",), payload_kind="object", payload_required=True),
        _op("delete_call_disposition", "Call Disposition", "DELETE", "/callDispositions/{disposition_id}", required_path_params=("disposition_id",)),
        # Stages
        _op("list_stages", "Stage", "GET", "/stages", allow_query=True),
        _op("get_stage", "Stage", "GET", "/stages/{stage_id}", required_path_params=("stage_id",)),
        _op("create_stage", "Stage", "POST", "/stages", payload_kind="object", payload_required=True),
        _op("update_stage", "Stage", "PATCH", "/stages/{stage_id}", required_path_params=("stage_id",), payload_kind="object", payload_required=True),
        _op("delete_stage", "Stage", "DELETE", "/stages/{stage_id}", required_path_params=("stage_id",)),
    )
)


def build_outreach_operation_catalog() -> tuple[OutreachOperation, ...]:
    """Return the supported Outreach operation catalog in stable order."""
    return tuple(_OUTREACH_CATALOG.values())


def get_outreach_operation(operation_name: str) -> OutreachOperation:
    """Return a supported Outreach operation or raise a clear error."""
    op = _OUTREACH_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_OUTREACH_CATALOG)
        raise ValueError(f"Unsupported Outreach operation '{operation_name}'. Available: {available}.")
    return op


def build_outreach_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Outreach request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=OUTREACH_REQUEST,
        name="outreach_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Outreach operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as prospect_id, account_id, sequence_id.",
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


def create_outreach_tools(
    *,
    credentials: "OutreachCredentials | None" = None,
    client: "Any | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Outreach request tool backed by the provided client."""
    outreach_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_outreach_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = outreach_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = outreach_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=outreach_client.credentials.timeout_seconds,
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
    credentials: "OutreachCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> OutreachPreparedRequest:
    from harnessiq.providers.outreach.api import build_headers

    op = get_outreach_operation(operation_name)
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
    headers = build_headers(credentials.access_token)

    return OutreachPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


def _select_operations(allowed: Sequence[str] | None) -> tuple[OutreachOperation, ...]:
    if allowed is None:
        return build_outreach_operation_catalog()
    seen: set[str] = set()
    selected: list[OutreachOperation] = []
    for name in allowed:
        op = get_outreach_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.outreach.client import OutreachClient
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Outreach credentials or an Outreach client must be provided.")
    return OutreachClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        raise ValueError(f"Unsupported Outreach operation '{value}'.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


def _build_tool_description(operations: Sequence[OutreachOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Outreach sales engagement API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append("Use 'path_params' for resource ids, 'query' for paginated lists, 'payload' for JSON bodies.")
    return "\n".join(lines)


__all__ = [
    "OUTREACH_REQUEST",
    "OutreachOperation",
    "OutreachPreparedRequest",
    "_build_prepared_request",
    "build_outreach_operation_catalog",
    "build_outreach_request_tool_definition",
    "create_outreach_tools",
    "get_outreach_operation",
]
