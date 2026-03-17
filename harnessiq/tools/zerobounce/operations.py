"""ZeroBounce MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.zerobounce.operations import (
    ZeroBounceOperation,
    build_zerobounce_operation_catalog,
    get_zerobounce_operation,
)
from harnessiq.shared.tools import ZEROBOUNCE_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.zerobounce.client import ZeroBounceClient, ZeroBounceCredentials


def build_zerobounce_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the ZeroBounce request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=ZEROBOUNCE_REQUEST,
        name="zerobounce_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The ZeroBounce operation to execute. Use 'validate_email' for real-time "
                        "single email validation or 'validate_batch' for up to 200 emails at once. "
                        "Use 'bulk_send_file' / 'bulk_file_status' / 'bulk_get_file' for large list "
                        "processing. Use 'score_email' for AI deliverability scoring. Use 'find_email' "
                        "to discover email addresses by name and domain. Use 'get_activity_data' to "
                        "check inbox engagement recency. Bulk operations automatically route to the "
                        "ZeroBounce bulk API endpoint."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters (none currently required by ZeroBounce operations).",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": (
                        "Query parameters for GET operations. "
                        "validate_email: {email, ip_address (opt), timeout (opt)}. "
                        "get_api_usage: {start_date: 'YYYY-MM-DD', end_date: 'YYYY-MM-DD'}. "
                        "bulk_file_status / bulk_get_file / bulk_delete_file: {file_id}. "
                        "find_email: {domain (or company_name), first_name (opt), last_name (opt)}. "
                        "get_activity_data: {email}. score_email: {email}."
                    ),
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "JSON body for POST operations. "
                        "validate_batch: {email_batch: [{email_address, ip_address}], timeout (opt), "
                        "activity_data (opt), verify_plus (opt)}. "
                        "bulk_send_file: {file, email_address_column, return_url (opt), "
                        "has_header_row (opt), remove_duplicate (opt)}. "
                        "add_filter / delete_filter: {rule: 'allow'|'block', "
                        "target: 'email'|'domain'|'mx'|'tld', value}."
                    ),
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_zerobounce_tools(
    *,
    credentials: "ZeroBounceCredentials | None" = None,
    client: "ZeroBounceClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style ZeroBounce request tool backed by the provided client."""
    zb_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_zerobounce_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = zb_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = zb_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=zb_client.credentials.timeout_seconds,
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

def _build_tool_description(operations: Sequence[ZeroBounceOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated ZeroBounce email validation and intelligence API operations.",
        "",
        "ZeroBounce provides enterprise-grade email validation, AI-powered deliverability scoring, "
        "email address discovery, and inbox activity data. Use it to clean email lists before "
        "outreach (removing invalid, disposable, and spam-trap addresses), discover correct email "
        "formats for prospects, score contacts by engagement likelihood, and manage allow/block "
        "filter rules. Bulk operations process large files asynchronously via the ZeroBounce bulk API.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: Use 'query' for GET filter parameters (email, file_id, dates). "
        "Use 'payload' for POST request bodies (batch arrays, file upload params, filter rules). "
        "Bulk file operations (bulk_send_file, bulk_scoring_send_file, bulk_finder_send_file) "
        "automatically route to bulkapi.zerobounce.net."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[ZeroBounceOperation, ...]:
    if allowed is None:
        return build_zerobounce_operation_catalog()
    seen: set[str] = set()
    selected: list[ZeroBounceOperation] = []
    for name in allowed:
        op = get_zerobounce_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either ZeroBounce credentials or a ZeroBounce client must be provided.")
    from harnessiq.providers.zerobounce.client import ZeroBounceClient
    return ZeroBounceClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(
            f"Unsupported ZeroBounce operation '{value}'. Allowed: {allowed_str}."
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
    "build_zerobounce_request_tool_definition",
    "create_zerobounce_tools",
]
