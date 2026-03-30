"""
===============================================================================
File: harnessiq/tools/phantombuster/operations.py

What this file does:
- Exposes the `phantombuster` tool family for the HarnessIQ tool layer.
- In most packages this module is the bridge between provider-backed operations
  and the generic tool registration surface.
- PhantomBuster MCP-style tool factory for the Harnessiq tool layer.

Use cases:
- Import this module when an agent or registry needs the `phantombuster` tool
  definitions.
- Read it to see which runtime operations are intentionally surfaced as tools.

How to use it:
- Call the exported factory helpers from `harnessiq/tools/phantombuster` and
  merge the resulting tools into a registry.

Intent:
- Keep the public `phantombuster` tool surface small, explicit, and separate
  from provider implementation details.
===============================================================================
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.phantombuster.operations import (
    PhantomBusterOperation,
    build_phantombuster_operation_catalog,
    get_phantombuster_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO
from harnessiq.shared.tools import (
    PHANTOMBUSTER_REQUEST,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

if TYPE_CHECKING:
    from harnessiq.providers.phantombuster.client import PhantomBusterClient
    from harnessiq.providers.phantombuster.credentials import PhantomBusterCredentials


def build_phantombuster_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the PhantomBuster request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=PHANTOMBUSTER_REQUEST,
        name="phantombuster_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The PhantomBuster operation to execute. Agent operations manage "
                        "automation agents — launch, abort, fetch output, and configure "
                        "arguments. Container operations inspect individual execution runs. "
                        "Phantom operations browse automation script templates. "
                        "Script operations manage underlying scripts. "
                        "Account operations retrieve user and organisation info."
                    ),
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Parameters for the operation. For get_agent / abort_agent / "
                        "delete_agent / fetch_agent_output / list_containers: {agent_id}. "
                        "For launch_agent: {agent_id, output?, arguments?, manual_launch?}. "
                        "For save_agent_argument: {agent_id, argument: {...}}. "
                        "For get_container: {container_id}. "
                        "For list_containers: {agent_id, status?}. "
                        "For fetch_agent_output: {agent_id, mode?}. "
                        "For get_phantom / get_script: {phantom_id} or {script_id}. "
                        "Omit for list operations (list_agents, list_phantoms, "
                        "list_scripts, get_user_info, list_org_members)."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_phantombuster_tools(
    *,
    credentials: "PhantomBusterCredentials | None" = None,
    client: "PhantomBusterClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the PhantomBuster request tool backed by the provided client."""
    pb_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_phantombuster_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        request = ProviderPayloadRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            payload=dict(_optional_mapping(arguments, "payload") or {}),
        )
        return pb_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[PhantomBusterOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated PhantomBuster browser automation and data extraction API operations.",
        "",
        "PhantomBuster is a no-code browser automation platform for running LinkedIn "
        "scrapers, profile extractors, and outreach bots at scale. Use agent operations "
        "to launch and monitor automation runs, retrieve extracted data, and configure "
        "reusable argument sets. Container operations provide granular run-level inspection. "
        "Phantom and script operations help discover the automation templates available "
        "in the marketplace. All operations use an API key passed in the "
        "X-Phantombuster-Key header.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: pass all operation-specific arguments inside 'payload'. "
        "Agent IDs and container IDs are strings or integers."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[PhantomBusterOperation, ...]:
    if allowed is None:
        return build_phantombuster_operation_catalog()
    seen: set[str] = set()
    selected: list[PhantomBusterOperation] = []
    for name in allowed:
        op = get_phantombuster_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError(
            "Either PhantomBuster credentials or a PhantomBuster client must be provided."
        )
    from harnessiq.providers.phantombuster.client import PhantomBusterClient
    return PhantomBusterClient(api_key=credentials["api_key"])


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported PhantomBuster operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(
    arguments: Mapping[str, object], key: str
) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


__all__ = [
    "build_phantombuster_request_tool_definition",
    "create_phantombuster_tools",
]
