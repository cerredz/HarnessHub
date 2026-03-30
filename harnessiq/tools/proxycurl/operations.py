"""
===============================================================================
File: harnessiq/tools/proxycurl/operations.py

What this file does:
- Exposes the `proxycurl` tool family for the HarnessIQ tool layer.
- In most packages this module is the bridge between provider-backed operations
  and the generic tool registration surface.
- Proxycurl MCP-style tool factory for the Harnessiq tool layer. NOTE:
  Proxycurl shut down in January 2025 following a LinkedIn lawsuit. This module
  is preserved for reference only and will not produce live responses.

Use cases:
- Import this module when an agent or registry needs the `proxycurl` tool
  definitions.
- Read it to see which runtime operations are intentionally surfaced as tools.

How to use it:
- Call the exported factory helpers from `harnessiq/tools/proxycurl` and merge
  the resulting tools into a registry.

Intent:
- Keep the public `proxycurl` tool surface small, explicit, and separate from
  provider implementation details.
===============================================================================
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.proxycurl.operations import (
    ProxycurlOperation,
    build_proxycurl_operation_catalog,
    get_proxycurl_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO
from harnessiq.shared.tools import (
    PROXYCURL_REQUEST,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

if TYPE_CHECKING:
    from harnessiq.providers.proxycurl.client import ProxycurlClient
    from harnessiq.providers.proxycurl.credentials import ProxycurlCredentials


def build_proxycurl_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Proxycurl request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=PROXYCURL_REQUEST,
        name="proxycurl_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Proxycurl operation to execute. Person operations scrape and "
                        "resolve LinkedIn profiles. Company operations scrape company pages "
                        "and list employees. Job operations surface open roles. Email "
                        "operations resolve emails to profiles and retrieve contact numbers. "
                        "WARNING: Proxycurl shut down in January 2025 — these operations "
                        "will not return live data."
                    ),
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Parameters for the operation. For scrape_person_profile: {url, ...}. "
                        "For resolve_person_profile: {first_name?, last_name?, company_domain?}. "
                        "For lookup_person_by_email: {email_address}. "
                        "For scrape_company_profile: {url, categories?, funding_data?}. "
                        "For resolve_company_profile: {company_name?, company_domain?}. "
                        "For list_company_employees: {url, country?, role_search?, page_size?}. "
                        "For list_company_jobs: {url, keyword?, type?}. "
                        "For search_jobs: {keyword?, geo_id?, type?}. "
                        "For resolve_email_to_profile: {email}. "
                        "For get_personal_emails / get_personal_contacts: {linkedin_profile_url}."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_proxycurl_tools(
    *,
    credentials: "ProxycurlCredentials | None" = None,
    client: "ProxycurlClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the Proxycurl request tool backed by the provided client.

    NOTE: Proxycurl shut down in January 2025. This tool is preserved for
    reference and local testing only.
    """
    proxycurl_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_proxycurl_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        request = ProviderPayloadRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            payload=dict(_optional_mapping(arguments, "payload") or {}),
        )
        return proxycurl_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[ProxycurlOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute Proxycurl LinkedIn data scraping API operations.",
        "",
        "⚠️  DEPRECATED: Proxycurl shut down in January 2025 following a LinkedIn "
        "cease-and-desist. This tool is preserved for reference and offline testing "
        "purposes only. No live responses will be returned.",
        "",
        "Proxycurl was a LinkedIn profile scraping service providing structured data "
        "for person profiles, company pages, employee lists, and job postings. Person "
        "operations could resolve names or emails to profile URLs and scrape full "
        "contact information. Company operations listed employees and open roles. "
        "Email operations resolved emails to profiles and surfaced personal contacts.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: pass all operation-specific arguments inside 'payload' "
        "as key-value pairs."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[ProxycurlOperation, ...]:
    if allowed is None:
        return build_proxycurl_operation_catalog()
    seen: set[str] = set()
    selected: list[ProxycurlOperation] = []
    for name in allowed:
        op = get_proxycurl_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Proxycurl credentials or a Proxycurl client must be provided.")
    from harnessiq.providers.proxycurl.client import ProxycurlClient
    return ProxycurlClient(api_key=credentials["api_key"])


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Proxycurl operation '{value}'. Allowed: {allowed_str}.")
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
    "build_proxycurl_request_tool_definition",
    "create_proxycurl_tools",
]
