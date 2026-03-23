"""Leads agent tool factory and handlers."""

from __future__ import annotations

import importlib
import inspect
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from harnessiq.shared.leads import (
    LeadICP,
    LeadRecord,
    LeadSearchRecord,
    LeadSearchSummary,
    LeadsAgentConfig,
    LeadsMemoryStore,
    normalize_leads_platform_name,
)
from harnessiq.shared.tools import (
    LEADS_CHECK_SEEN,
    LEADS_COMPACT_SEARCH_HISTORY,
    LEADS_LOG_SEARCH,
    LEADS_SAVE_LEADS,
    RegisteredTool,
    ToolDefinition,
)
from harnessiq.tools.registry import merge_tools
from harnessiq.toolset.catalog import PROVIDER_FACTORY_MAP


def create_leads_tools(
    *,
    config: LeadsAgentConfig,
    memory_store: LeadsMemoryStore,
    current_icp: Callable[[], LeadICP],
    current_run_id: Callable[[], str | None],
    refresh_parameters: Callable[[], None],
    provider_tools: Sequence[RegisteredTool] | None = None,
    provider_credentials: Mapping[str, Any] | None = None,
    provider_clients: Mapping[str, Any] | None = None,
    allowed_provider_operations: Mapping[str, Sequence[str] | None] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Create the full leads tool surface for one harness instance."""
    external_tools = (
        tuple(provider_tools)
        if provider_tools is not None
        else _build_provider_tools(
            platforms=config.run_config.platforms,
            provider_credentials=dict(provider_credentials or {}),
            provider_clients=dict(provider_clients or {}),
            allowed_provider_operations=dict(allowed_provider_operations or {}),
        )
    )
    internal_tools = _build_internal_tools(
        config=config,
        memory_store=memory_store,
        current_icp=current_icp,
        current_run_id=current_run_id,
        refresh_parameters=refresh_parameters,
    )
    return merge_tools(external_tools, internal_tools)


def _build_internal_tools(
    *,
    config: LeadsAgentConfig,
    memory_store: LeadsMemoryStore,
    current_icp: Callable[[], LeadICP],
    current_run_id: Callable[[], str | None],
    refresh_parameters: Callable[[], None],
) -> tuple[RegisteredTool, ...]:
    def coerce_lead(payload: Mapping[str, Any]) -> LeadRecord:
        icp = current_icp()
        return LeadRecord(
            full_name=str(payload["full_name"]),
            company_name=str(payload.get("company_name", "")),
            title=str(payload.get("title", "")),
            icp_key=icp.key,
            provider=str(payload["provider"]),
            found_at=str(payload.get("found_at", _utcnow())),
            email=str(payload["email"]) if payload.get("email") else None,
            linkedin_url=str(payload["linkedin_url"]) if payload.get("linkedin_url") else None,
            phone=str(payload["phone"]) if payload.get("phone") else None,
            location=str(payload["location"]) if payload.get("location") else None,
            provider_person_id=str(payload["provider_person_id"]) if payload.get("provider_person_id") else None,
            source_search_sequence=int(payload["source_search_sequence"])
            if payload.get("source_search_sequence") is not None
            else None,
            metadata=dict(payload.get("metadata", {})),
        )

    def handle_log_search(arguments: dict[str, Any]) -> dict[str, Any]:
        icp = current_icp()
        sequence = memory_store.next_search_sequence(icp.key)
        search = LeadSearchRecord(
            sequence=sequence,
            icp_key=icp.key,
            platform=str(arguments["platform"]),
            query=str(arguments["query"]),
            recorded_at=_utcnow(),
            filters=dict(arguments.get("filters", {})),
            result_count=int(arguments["result_count"]) if arguments.get("result_count") is not None else None,
            outcome=str(arguments.get("outcome", "")),
            new_leads=int(arguments.get("new_leads", 0)),
            metadata=dict(arguments.get("metadata", {})),
        )
        state = memory_store.append_search(icp.key, search)
        auto_summary: LeadSearchSummary | None = None
        if (
            search.sequence % config.run_config.search_summary_every == 0
            and len(state.searches) > config.run_config.search_tail_size
        ):
            keep_last = config.run_config.search_tail_size
            replaceable = state.searches[:-keep_last] if keep_last else list(state.searches)
            auto_summary = memory_store.compact_searches(
                icp.key,
                summary_content=_build_auto_summary(replaceable),
                keep_last=keep_last,
                metadata={"auto_compacted": True},
            )
        refresh_parameters()
        return {
            "search": search.as_dict(),
            "total_searches_for_icp": memory_store.next_search_sequence(icp.key) - 1,
            "auto_compacted": auto_summary is not None,
            "summary": auto_summary.as_dict() if auto_summary is not None else None,
        }

    def handle_compact_search_history(arguments: dict[str, Any]) -> dict[str, Any]:
        icp = current_icp()
        summary = memory_store.compact_searches(
            icp.key,
            summary_content=str(arguments["summary_content"]),
            keep_last=int(arguments.get("keep_last", config.run_config.search_tail_size)),
            metadata={"manual_compaction": True},
        )
        refresh_parameters()
        return summary.as_dict()

    def handle_check_seen_lead(arguments: dict[str, Any]) -> dict[str, Any]:
        lead = coerce_lead(arguments)
        dedupe_key = lead.dedupe_key()
        already_seen = config.storage_backend.has_seen_lead(dedupe_key)
        return {"dedupe_key": dedupe_key, "already_seen": already_seen}

    def handle_save_leads(arguments: dict[str, Any]) -> dict[str, Any]:
        run_id = current_run_id()
        if run_id is None:
            raise RuntimeError("Cannot save leads before prepare() has been called.")
        icp = current_icp()
        payload = arguments.get("leads")
        if not isinstance(payload, list):
            raise ValueError("The 'leads' argument must be an array.")
        leads = tuple(coerce_lead(item) for item in payload)
        results = config.storage_backend.save_leads(
            run_id,
            icp.key,
            leads,
            metadata=dict(arguments.get("metadata", {})),
        )
        for result in results:
            if result.saved:
                memory_store.record_saved_lead_key(icp.key, result.lead.dedupe_key())
        refresh_parameters()
        return {
            "saved_count": sum(1 for result in results if result.saved),
            "duplicate_count": sum(1 for result in results if not result.saved),
            "results": [result.as_dict() for result in results],
        }

    return (
        RegisteredTool(
            definition=_tool_definition(
                key=LEADS_LOG_SEARCH,
                name="log_search",
                description=(
                    "Persist a search attempt for the active ICP. Call this after every provider "
                    "search or enrichment query so the harness can track durable search history."
                ),
                properties={
                    "platform": {"type": "string", "description": "Provider family used for the search."},
                    "query": {"type": "string", "description": "Human-readable query or search hypothesis."},
                    "filters": {"type": "object", "additionalProperties": True},
                    "result_count": {"type": "integer", "description": "Number of results returned, if known."},
                    "outcome": {"type": "string", "description": "Short verdict on search quality or next action."},
                    "new_leads": {"type": "integer", "description": "How many new leads this search produced."},
                    "metadata": {"type": "object", "additionalProperties": True},
                },
                required=("platform", "query"),
            ),
            handler=handle_log_search,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=LEADS_COMPACT_SEARCH_HISTORY,
                name="compact_search_history",
                description=(
                    "Replace older search entries for the active ICP with a durable summary while keeping "
                    "the most recent tail available in prompt context."
                ),
                properties={
                    "summary_content": {
                        "type": "string",
                        "description": "Summary of what worked, what failed, and what remains.",
                    },
                    "keep_last": {
                        "type": "integer",
                        "description": "How many recent raw searches to preserve after compaction.",
                    },
                },
                required=("summary_content",),
            ),
            handler=handle_compact_search_history,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=LEADS_CHECK_SEEN,
                name="check_seen_lead",
                description=(
                    "Check whether a prospective lead has already been saved in durable storage using the "
                    "same dedupe identity."
                ),
                properties=_lead_properties_schema(),
                required=("full_name", "provider"),
            ),
            handler=handle_check_seen_lead,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=LEADS_SAVE_LEADS,
                name="save_leads",
                description=(
                    "Persist one or more qualified leads for the active ICP through the configured storage backend."
                ),
                properties={
                    "leads": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": _lead_properties_schema(),
                            "required": ["full_name", "provider"],
                            "additionalProperties": False,
                        },
                    },
                    "metadata": {"type": "object", "additionalProperties": True},
                },
                required=("leads",),
            ),
            handler=handle_save_leads,
        ),
    )


def _build_provider_tools(
    *,
    platforms: Sequence[str],
    provider_credentials: Mapping[str, Any],
    provider_clients: Mapping[str, Any],
    allowed_provider_operations: Mapping[str, Sequence[str] | None],
) -> tuple[RegisteredTool, ...]:
    resolved_tools: list[RegisteredTool] = []
    for platform in platforms:
        family = normalize_leads_platform_name(platform)
        if family not in PROVIDER_FACTORY_MAP:
            available = ", ".join(sorted(PROVIDER_FACTORY_MAP))
            raise ValueError(f"Unsupported leads platform '{family}'. Available: {available}.")
        module_path, function_name = PROVIDER_FACTORY_MAP[family]
        factory = getattr(importlib.import_module(module_path), function_name)
        signature = inspect.signature(factory)
        kwargs: dict[str, Any] = {}
        if "credentials" in signature.parameters and family in provider_credentials:
            kwargs["credentials"] = provider_credentials[family]
        if "client" in signature.parameters and family in provider_clients:
            kwargs["client"] = provider_clients[family]
        if "allowed_operations" in signature.parameters and family in allowed_provider_operations:
            kwargs["allowed_operations"] = allowed_provider_operations[family]
        if "credentials" in signature.parameters and "client" in signature.parameters and not (
            "credentials" in kwargs or "client" in kwargs
        ):
            raise ValueError(
                f"Platform '{family}' requires either provider credentials or a prebuilt client."
            )
        resolved_tools.extend(factory(**kwargs))
    return tuple(resolved_tools)
def _tool_definition(
    *,
    key: str,
    name: str,
    description: str,
    properties: dict[str, Any],
    required: Sequence[str] = (),
) -> ToolDefinition:
    return ToolDefinition(
        key=key,
        name=name,
        description=description,
        input_schema={
            "type": "object",
            "properties": properties,
            "required": list(required),
            "additionalProperties": False,
        },
    )


def _lead_properties_schema() -> dict[str, Any]:
    return {
        "full_name": {"type": "string"},
        "company_name": {"type": "string"},
        "title": {"type": "string"},
        "provider": {"type": "string"},
        "found_at": {"type": "string"},
        "email": {"type": "string"},
        "linkedin_url": {"type": "string"},
        "phone": {"type": "string"},
        "location": {"type": "string"},
        "provider_person_id": {"type": "string"},
        "source_search_sequence": {"type": "integer"},
        "metadata": {"type": "object", "additionalProperties": True},
    }


def _build_auto_summary(entries: Sequence[LeadSearchRecord]) -> str:
    platform_counts = Counter(entry.platform for entry in entries)
    result_counts = [entry.result_count for entry in entries if entry.result_count is not None]
    outcomes = [entry.outcome.strip() for entry in entries if entry.outcome.strip()]
    lines = [
        f"Auto-compacted {len(entries)} searches covering sequences {entries[0].sequence}-{entries[-1].sequence}.",
        f"Platforms used: {', '.join(f'{platform} x{count}' for platform, count in sorted(platform_counts.items()))}.",
        f"Total new leads observed: {sum(entry.new_leads for entry in entries)}.",
    ]
    if result_counts:
        lines.append(f"Observed result counts ranged from {min(result_counts)} to {max(result_counts)}.")
    if outcomes:
        lines.append(f"Recent outcomes: {' | '.join(outcomes[-3:])}")
    return "\n".join(lines)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["create_leads_tools"]
