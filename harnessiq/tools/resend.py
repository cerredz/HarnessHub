"""Resend-backed tooling primitives for outbound email workflows."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.parse import urlencode

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

from harnessiq.shared.resend import (
    DEFAULT_RESEND_BASE_URL,
    DEFAULT_RESEND_USER_AGENT,
    RESEND_REQUEST,
    ResendCredentials,
    ResendOperation,
    ResendPreparedRequest,
    _BATCH_VALIDATION_MODES,
    build_resend_operation_catalog,
    get_resend_operation,
)

@dataclass(frozen=True, slots=True)
class ResendClient:
    """Small Resend HTTP client suitable for tool execution and tests."""

    credentials: ResendCredentials
    request_executor: RequestExecutor = request_json

    def prepare_request(
        self,
        operation_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        payload: Any | None = None,
        idempotency_key: str | None = None,
        batch_validation: str | None = None,
    ) -> ResendPreparedRequest:
        """Validate the operation inputs and build an executable request."""
        operation = get_resend_operation(operation_name)
        normalized_path_params = _normalize_path_params(path_params)
        _validate_path_params(operation, normalized_path_params)
        normalized_query = _normalize_mapping(query, field_name="query") if query is not None else None
        _validate_payload(operation, payload)
        _validate_headers(
            operation,
            idempotency_key=idempotency_key,
            batch_validation=batch_validation,
        )

        path = operation.path_builder(normalized_path_params)
        url = _build_url(self.credentials.base_url, path, query=normalized_query)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.credentials.api_key}",
            "User-Agent": self.credentials.user_agent,
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if batch_validation is not None:
            headers["x-batch-validation"] = batch_validation

        return ResendPreparedRequest(
            operation=operation,
            method=operation.method,
            path=path,
            url=url,
            headers=headers,
            json_body=_copy_payload(payload),
        )

    def execute_operation(
        self,
        operation_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        payload: Any | None = None,
        idempotency_key: str | None = None,
        batch_validation: str | None = None,
    ) -> Any:
        """Execute one validated Resend operation and return the decoded response."""
        prepared = self.prepare_request(
            operation_name,
            path_params=path_params,
            query=query,
            payload=payload,
            idempotency_key=idempotency_key,
            batch_validation=batch_validation,
        )
        return self.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=self.credentials.timeout_seconds,
        )


def build_resend_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Resend request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [operation.name for operation in operations]
    return ToolDefinition(
        key=RESEND_REQUEST,
        name="resend_request",
        description=_build_resend_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Supported Resend operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Operation-specific path parameters such as ids used in the URL.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for list/filter operations.",
                    "additionalProperties": True,
                },
                "payload": {
                    "description": "Optional operation-specific JSON body. Some operations require an object or array.",
                    "anyOf": [
                        {"type": "object"},
                        {"type": "array"},
                    ],
                },
                "idempotency_key": {
                    "type": "string",
                    "description": "Optional Resend Idempotency-Key header for supported send operations.",
                },
                "batch_validation": {
                    "type": "string",
                    "enum": sorted(_BATCH_VALIDATION_MODES),
                    "description": "Optional x-batch-validation mode for batch send operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_resend_tools(
    *,
    credentials: ResendCredentials | None = None,
    client: ResendClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Resend request tool backed by the provided client."""
    resend_client = _coerce_client(credentials=credentials, client=client)
    selected_operations = _select_operations(allowed_operations)
    allowed_names = frozenset(operation.name for operation in selected_operations)
    definition = build_resend_request_tool_definition(
        allowed_operations=tuple(operation.name for operation in selected_operations)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = resend_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
            idempotency_key=_optional_string(arguments, "idempotency_key"),
            batch_validation=_optional_string(arguments, "batch_validation"),
        )
        response = resend_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=resend_client.credentials.timeout_seconds,
        )
        return {
            "operation": prepared.operation.name,
            "method": prepared.method,
            "path": prepared.path,
            "response": response,
        }

    return (RegisteredTool(definition=definition, handler=handler),)


def _coerce_client(
    *,
    credentials: ResendCredentials | None,
    client: ResendClient | None,
) -> ResendClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Resend credentials or a Resend client must be provided.")
    return ResendClient(credentials=credentials)


def _build_resend_tool_description(operations: Sequence[ResendOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for operation in operations:
        grouped.setdefault(operation.category, []).append(operation.summary())

    lines = ["Execute authenticated Resend API operations through a single MCP-style request tool."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append(
        "Use `path_params` for URL ids, `query` for list pagination/filtering, `payload` for JSON bodies, "
        "`idempotency_key` for supported send operations, and `batch_validation` for batch sends."
    )
    return "\n".join(lines)


def _select_operations(allowed_operations: Sequence[str] | None) -> tuple[ResendOperation, ...]:
    if allowed_operations is None:
        return build_resend_operation_catalog()
    selected: list[ResendOperation] = []
    seen: set[str] = set()
    for operation_name in allowed_operations:
        operation = get_resend_operation(operation_name)
        if operation.name in seen:
            continue
        seen.add(operation.name)
        selected.append(operation)
    return tuple(selected)


def _require_operation_name(arguments: Mapping[str, object], allowed_names: set[str] | frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed_names:
        allowed = ", ".join(sorted(allowed_names))
        raise ValueError(f"Unsupported Resend operation '{value}' for this tool configuration. Allowed: {allowed}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return value


def _optional_string(arguments: Mapping[str, object], key: str) -> str | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string when provided.")
    return value


def _normalize_path_params(path_params: Mapping[str, object] | None) -> dict[str, str]:
    if path_params is None:
        return {}
    normalized = _normalize_mapping(path_params, field_name="path_params")
    return {key: str(value) for key, value in normalized.items()}


def _normalize_mapping(mapping: Mapping[str, object], *, field_name: str) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise ValueError(f"All keys in '{field_name}' must be strings.")
        normalized[key] = deepcopy(value)
    return normalized


def _validate_path_params(operation: ResendOperation, path_params: Mapping[str, str]) -> None:
    allowed = set(operation.required_path_params) | set(operation.optional_path_params)
    unexpected = sorted(set(path_params) - allowed)
    if unexpected:
        raise ValueError(
            f"Operation '{operation.name}' received unexpected path parameters: {', '.join(unexpected)}."
        )

    missing = [key for key in operation.required_path_params if not path_params.get(key)]
    if missing:
        raise ValueError(f"Operation '{operation.name}' requires path parameters: {', '.join(missing)}.")


def _validate_payload(operation: ResendOperation, payload: Any | None) -> None:
    if operation.payload_kind == "none":
        if payload is not None:
            raise ValueError(f"Operation '{operation.name}' does not accept a payload.")
        return

    if payload is None:
        if operation.payload_required:
            raise ValueError(f"Operation '{operation.name}' requires a payload.")
        return

    if operation.payload_kind == "object" and not isinstance(payload, Mapping):
        raise ValueError(f"Operation '{operation.name}' requires an object payload.")
    if operation.payload_kind == "array":
        if not isinstance(payload, list):
            raise ValueError(f"Operation '{operation.name}' requires an array payload.")
        for index, item in enumerate(payload):
            if not isinstance(item, Mapping):
                raise ValueError(f"Operation '{operation.name}' requires payload item {index} to be an object.")


def _validate_headers(
    operation: ResendOperation,
    *,
    idempotency_key: str | None,
    batch_validation: str | None,
) -> None:
    if idempotency_key is not None and not operation.supports_idempotency_key:
        raise ValueError(f"Operation '{operation.name}' does not support idempotency_key.")
    if batch_validation is not None:
        if not operation.supports_batch_validation:
            raise ValueError(f"Operation '{operation.name}' does not support batch_validation.")
        if batch_validation not in _BATCH_VALIDATION_MODES:
            modes = ", ".join(sorted(_BATCH_VALIDATION_MODES))
            raise ValueError(f"batch_validation must be one of: {modes}.")


def _copy_payload(payload: Any | None) -> Any | None:
    if payload is None:
        return None
    return deepcopy(payload)


def _build_url(base_url: str, path: str, *, query: Mapping[str, object] | None = None) -> str:
    base = base_url.rstrip("/")
    if not query:
        return f"{base}{path}"

    encoded_query = urlencode(list(_flatten_query_items(query)), doseq=True)
    return f"{base}{path}?{encoded_query}"


def _flatten_query_items(query: Mapping[str, object]) -> list[tuple[str, object]]:
    items: list[tuple[str, object]] = []
    for key, value in query.items():
        if isinstance(value, (list, tuple)):
            for item in value:
                items.append((key, item))
            continue
        items.append((key, value))
    return items


__all__ = [
    "DEFAULT_RESEND_BASE_URL",
    "DEFAULT_RESEND_USER_AGENT",
    "RESEND_REQUEST",
    "ResendClient",
    "ResendCredentials",
    "ResendOperation",
    "ResendPreparedRequest",
    "build_resend_operation_catalog",
    "build_resend_request_tool_definition",
    "create_resend_tools",
    "get_resend_operation",
]
