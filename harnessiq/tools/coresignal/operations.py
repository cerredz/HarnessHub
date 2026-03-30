"""
===============================================================================
File: harnessiq/tools/coresignal/operations.py

What this file does:
- Exposes the `coresignal` tool family for the HarnessIQ tool layer.
- In most packages this module is the bridge between provider-backed operations
  and the generic tool registration surface.
- Coresignal MCP-style tool factory for the Harnessiq tool layer.

Use cases:
- Import this module when an agent or registry needs the `coresignal` tool
  definitions.
- Read it to see which runtime operations are intentionally surfaced as tools.

How to use it:
- Call the exported factory helpers from `harnessiq/tools/coresignal` and merge
  the resulting tools into a registry.

Intent:
- Keep the public `coresignal` tool surface small, explicit, and separate from
  provider implementation details.
===============================================================================
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.coresignal.operations import (
    CoreSignalOperation,
    build_coresignal_operation_catalog,
    get_coresignal_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO
from harnessiq.shared.tools import (
    CORESIGNAL_REQUEST,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

if TYPE_CHECKING:
    from harnessiq.providers.coresignal.client import CoreSignalClient
    from harnessiq.providers.coresignal.credentials import CoreSignalCredentials


def build_coresignal_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Coresignal request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=CORESIGNAL_REQUEST,
        name="coresignal_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Coresignal operation to execute. Employee operations search "
                        "and retrieve professional profile records. Company operations search "
                        "and retrieve organisation records. Job operations search and retrieve "
                        "job posting records. Each entity supports both simple filter-based "
                        "search and advanced Elasticsearch DSL queries."
                    ),
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Parameters for the operation. For search_employees_by_filter: "
                        "{name?, title?, company_name?, location?, page?, size?}. "
                        "For search_companies_by_filter: "
                        "{name?, website?, industry?, country?, page?, size?}. "
                        "For search_jobs_by_filter: "
                        "{title?, company_name?, location?, date_from?, date_to?, page?, size?}. "
                        "For *_es_dsl operations: {query: {...}, size?, from_?}. "
                        "For get_employee / get_company / get_job: {employee_id / company_id / job_id}."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_coresignal_tools(
    *,
    credentials: "CoreSignalCredentials | None" = None,
    client: "CoreSignalClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the Coresignal request tool backed by the provided client."""
    coresignal_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_coresignal_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        request = ProviderPayloadRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            payload=dict(_optional_mapping(arguments, "payload") or {}),
        )
        return coresignal_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[CoreSignalOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Coresignal professional data intelligence API operations.",
        "",
        "Coresignal is a B2B data platform providing fresh, structured professional "
        "profiles, company records, and job postings sourced from public LinkedIn data. "
        "Use filter-based search operations for structured queries by name, title, company, "
        "or location. Use Elasticsearch DSL operations for complex multi-field queries, "
        "range filters, and boolean logic. Use collect operations to retrieve a full "
        "record by its Coresignal ID after identifying it in search results. "
        "Authentication uses the lowercase 'apikey' header.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: pass all operation-specific arguments inside 'payload'. "
        "IDs for get operations are strings or integers."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[CoreSignalOperation, ...]:
    if allowed is None:
        return build_coresignal_operation_catalog()
    seen: set[str] = set()
    selected: list[CoreSignalOperation] = []
    for name in allowed:
        op = get_coresignal_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Coresignal credentials or a Coresignal client must be provided.")
    from harnessiq.providers.coresignal.client import CoreSignalClient
    return CoreSignalClient(api_key=credentials["api_key"])


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Coresignal operation '{value}'. Allowed: {allowed_str}.")
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
    "build_coresignal_request_tool_definition",
    "create_coresignal_tools",
]
