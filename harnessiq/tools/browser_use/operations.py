"""
===============================================================================
File: harnessiq/tools/browser_use/operations.py

What this file does:
- Exposes the `browser_use` tool family for the HarnessIQ tool layer.
- In most packages this module is the bridge between provider-backed operations
  and the generic tool registration surface.
- Browser Use MCP-style tool factory for the Harnessiq tool layer.

Use cases:
- Import this module when an agent or registry needs the `browser_use` tool
  definitions.
- Read it to see which runtime operations are intentionally surfaced as tools.

How to use it:
- Call the exported factory helpers from `harnessiq/tools/browser_use` and
  merge the resulting tools into a registry.

Intent:
- Keep the public `browser_use` tool surface small, explicit, and separate from
  provider implementation details.
===============================================================================
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.shared.dtos import ProviderPayloadRequestDTO
from harnessiq.providers.browser_use.operations import (
    BrowserUseOperation,
    build_browser_use_operation_catalog,
    get_browser_use_operation,
)
from harnessiq.shared.tools import BROWSER_USE_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.browser_use.client import BrowserUseClient
    from harnessiq.providers.browser_use.credentials import BrowserUseCredentials


def build_browser_use_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Browser Use request surface."""

    operations = _select_operations(allowed_operations)
    operation_names = [operation.name for operation in operations]
    return ToolDefinition(
        key=BROWSER_USE_REQUEST,
        name="browser_use_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Browser Use Cloud operation to execute. Task operations run and monitor browser "
                        "automation jobs. Session and profile operations manage persistent browser state. "
                        "Browser operations create standalone CDP-capable sessions. Skill and marketplace "
                        "operations manage reusable Browser Use workflows. File operations return presigned "
                        "upload or download URLs."
                    ),
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Operation-specific arguments using snake_case names that match the Browser Use client "
                        "method signatures. Examples: create_task -> {task, session_id?, llm?, max_steps?, "
                        "allowed_domains?, structured_output?}; get_task_status -> {task_id}; "
                        "create_session -> {profile_id?, start_url?, persist_memory?, keep_alive?}; "
                        "execute_skill -> {skill_id, parameters?, session_id?}; "
                        "create_session_upload_url -> {session_id, file_name, content_type, size_bytes}."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_browser_use_tools(
    *,
    credentials: "BrowserUseCredentials | None" = None,
    client: "BrowserUseClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the Browser Use request tool backed by the provided client."""

    browser_use_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(operation.name for operation in selected)
    definition = build_browser_use_request_tool_definition(
        allowed_operations=tuple(operation.name for operation in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        request = ProviderPayloadRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            payload=dict(_optional_mapping(arguments, "payload") or {}),
        )
        return browser_use_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


def _build_tool_description(operations: Sequence[BrowserUseOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for operation in operations:
        grouped.setdefault(operation.category, []).append(operation.summary())

    lines = [
        "Execute authenticated Browser Use Cloud browser automation, session, profile, browser, file, skill, and marketplace operations.",
        "",
        "Browser Use provides managed browser automation tasks, persistent sessions and profiles, standalone "
        "CDP/browser sessions, reusable skills, and task artifact handling. Use this surface when a Harnessiq "
        "agent needs coarse-grained browser execution through Browser Use rather than low-level selector-driven "
        "Playwright tools.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: pass operation-specific values inside 'payload' using snake_case keys. "
        "Task/session/profile/browser/skill identifiers should be passed as strings."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[BrowserUseOperation, ...]:
    if allowed is None:
        return build_browser_use_operation_catalog()
    seen: set[str] = set()
    selected: list[BrowserUseOperation] = []
    for name in allowed:
        operation = get_browser_use_operation(name)
        if operation.name not in seen:
            seen.add(operation.name)
            selected.append(operation)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Browser Use credentials or a Browser Use client must be provided.")
    from harnessiq.providers.browser_use.client import BrowserUseClient

    return BrowserUseClient(
        api_key=credentials.api_key,
        base_url=credentials.base_url,
        timeout_seconds=credentials.timeout_seconds,
    )


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Browser Use operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return value


__all__ = [
    "build_browser_use_request_tool_definition",
    "create_browser_use_tools",
]
