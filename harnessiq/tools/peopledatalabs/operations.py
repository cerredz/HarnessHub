"""People Data Labs MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.peopledatalabs.operations import (
    PeopleDataLabsOperation,
    build_peopledatalabs_operation_catalog,
    get_peopledatalabs_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO
from harnessiq.shared.tools import (
    PEOPLEDATALABS_REQUEST,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

if TYPE_CHECKING:
    from harnessiq.providers.peopledatalabs.client import PeopleDataLabsClient
    from harnessiq.providers.peopledatalabs.credentials import PeopleDataLabsCredentials


def build_peopledatalabs_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the People Data Labs request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=PEOPLEDATALABS_REQUEST,
        name="peopledatalabs_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The People Data Labs operation to execute. Person operations enrich "
                        "and identify individuals using email, phone, name, or LinkedIn URL. "
                        "Company operations enrich and search organisations. Bulk operations "
                        "process multiple records in one call. Utility operations normalise "
                        "location, job title, and autocomplete field values."
                    ),
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Parameters for the operation. For enrich_person / identify_person: "
                        "{email?, phone?, name?, linkedin_url?, company?, location?, "
                        "min_likelihood?, required?}. "
                        "For search_people / search_companies: {query?: {...}, sql?: '...', "
                        "size?: 10, from_?: 0}. "
                        "For bulk_enrich_people / bulk_enrich_companies: "
                        "{requests: [{...}, ...], size?}. "
                        "For enrich_company: {name?, website?, profile?, ticker?}. "
                        "For enrich_school: {name?, website?, profile?}. "
                        "For clean_location: {location}. "
                        "For autocomplete: {field, text, size?}. "
                        "For enrich_job_title: {job_title}."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_peopledatalabs_tools(
    *,
    credentials: "PeopleDataLabsCredentials | None" = None,
    client: "PeopleDataLabsClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the People Data Labs request tool backed by the provided client."""
    pdl_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_peopledatalabs_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        request = ProviderPayloadRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            payload=dict(_optional_mapping(arguments, "payload") or {}),
        )
        return pdl_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[PeopleDataLabsOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated People Data Labs data enrichment and search API operations.",
        "",
        "People Data Labs (PDL) is a B2B data provider offering one of the largest "
        "datasets of professional profiles, company records, and education data. Use "
        "enrich_person to resolve an email, phone, or LinkedIn URL to a full professional "
        "profile. Use identify_person for probabilistic matching across multiple signals. "
        "Use search_people and search_companies for Elasticsearch-powered queries against "
        "the full PDL dataset. Bulk operations batch-enrich dozens of records in a single "
        "API call. Utility operations (clean_location, enrich_job_title, autocomplete) "
        "normalise free-text inputs before using them in queries.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: pass all operation-specific arguments inside 'payload'. "
        "All person and company matching parameters are optional individually but at "
        "least one signal is required per record."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[PeopleDataLabsOperation, ...]:
    if allowed is None:
        return build_peopledatalabs_operation_catalog()
    seen: set[str] = set()
    selected: list[PeopleDataLabsOperation] = []
    for name in allowed:
        op = get_peopledatalabs_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError(
            "Either People Data Labs credentials or a PDL client must be provided."
        )
    from harnessiq.providers.peopledatalabs.client import PeopleDataLabsClient
    return PeopleDataLabsClient(api_key=credentials["api_key"])


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported PDL operation '{value}'. Allowed: {allowed_str}.")
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
    "build_peopledatalabs_request_tool_definition",
    "create_peopledatalabs_tools",
]
