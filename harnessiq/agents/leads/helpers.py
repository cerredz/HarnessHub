"""Helper functions for the Leads agent."""

from __future__ import annotations

from datetime import datetime, timezone

from harnessiq.shared.agents import render_json_parameter_content
from harnessiq.shared.leads import LeadICPState, LeadsAgentConfig, LeadSearchRecord, LeadSearchSummary, LeadsMemoryStore


def render_search_history(
    summaries: tuple[LeadSearchSummary, ...] | list[LeadSearchSummary],
    recent_searches: tuple[LeadSearchRecord, ...] | list[LeadSearchRecord],
) -> str:
    """Render a compact search history payload for prompt injection."""
    payload = {
        "summaries": [summary.as_dict() for summary in summaries],
        "recent_searches": [search.as_dict() for search in recent_searches],
    }
    if not payload["summaries"] and not payload["recent_searches"]:
        return "(no search history recorded yet)"
    return render_json_parameter_content(payload)


def build_leads_instance_payload(*, config: LeadsAgentConfig) -> dict[str, object]:
    """Build the Leads agent instance payload from config and persisted state."""
    payload: dict[str, object] = {
        "memory_path": str(config.memory_path),
        "run_config": config.run_config.as_dict(),
        "runtime": {
            "max_tokens": config.max_tokens,
            "reset_threshold": config.reset_threshold,
            "prune_search_interval": config.prune_search_interval,
            "prune_token_limit": config.prune_token_limit,
        },
    }
    if not config.memory_path.exists():
        return payload

    store = LeadsMemoryStore(memory_path=config.memory_path)
    if store.run_state_path.exists():
        payload["run_state"] = store.read_run_state().as_dict()

    icp_states = store.list_icp_states()
    if icp_states:
        payload["icp_progress"] = [
            {
                "icp": state.icp.as_dict(),
                "status": state.status,
                "search_count": len(state.searches),
                "summary_count": len(state.summaries),
                "saved_lead_count": len(state.saved_lead_keys),
                "completed_at": state.completed_at,
            }
            for state in icp_states
        ]
    return payload


def total_searches_for_state(state: LeadICPState) -> int:
    """Count the highest completed search/summary sequence for an ICP state."""
    last_search = state.searches[-1].sequence if state.searches else 0
    last_summary = state.summaries[-1].last_sequence or 0 if state.summaries else 0
    return max(last_search, last_summary)


def utc_now_z() -> str:
    """Return the current UTC timestamp in ISO-8601 Zulu format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def timestamped_run_id() -> str:
    """Build a deterministic timestamp-based run identifier."""
    return f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


__all__ = [
    "build_leads_instance_payload",
    "render_search_history",
    "timestamped_run_id",
    "total_searches_for_state",
    "utc_now_z",
]
