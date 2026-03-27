"""Tool-definition and factory wiring for Resend operations."""

from __future__ import annotations

from typing import Any, Sequence

from harnessiq.interfaces import ResendRequestClient
from harnessiq.shared.resend import RESEND_REQUEST, ResendCredentials
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition
from harnessiq.tools.resend_catalog import (
    _BATCH_VALIDATION_MODES,
    ResendOperation,
    build_resend_tool_description,
    select_resend_operations,
)
from harnessiq.tools.resend_client import (
    ResendClient,
    coerce_resend_client,
    optional_resend_mapping,
    optional_resend_string,
    require_resend_operation_name,
)


def build_resend_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Resend request surface."""
    operations = select_resend_operations(allowed_operations)
    operation_names = [operation.name for operation in operations]
    return ToolDefinition(
        key=RESEND_REQUEST,
        name="resend_request",
        description=build_resend_tool_description(operations),
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
    client: ResendRequestClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Resend request tool backed by the provided client."""
    resend_client = coerce_resend_client(credentials=credentials, client=client)
    selected_operations = select_resend_operations(allowed_operations)
    allowed_names = frozenset(operation.name for operation in selected_operations)
    definition = build_resend_request_tool_definition(
        allowed_operations=tuple(operation.name for operation in selected_operations)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = require_resend_operation_name(arguments, allowed_names)
        prepared = resend_client.prepare_request(
            operation_name,
            path_params=optional_resend_mapping(arguments, "path_params"),
            query=optional_resend_mapping(arguments, "query"),
            payload=arguments.get("payload"),
            idempotency_key=optional_resend_string(arguments, "idempotency_key"),
            batch_validation=optional_resend_string(arguments, "batch_validation"),
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


__all__ = [
    "ResendOperation",
    "build_resend_request_tool_definition",
    "create_resend_tools",
]
