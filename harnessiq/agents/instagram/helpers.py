"""
===============================================================================
File: harnessiq/agents/instagram/helpers.py

What this file does:
- Collects shared helper functions for the `instagram` package.
- Helper functions for the Instagram keyword discovery agent.

Use cases:
- Use these helpers when sibling runtime modules need the same normalization,
  path resolution, or payload-shaping logic.

How to use it:
- Import the narrow helper you need from `harnessiq/agents/instagram` rather
  than duplicating package-specific support code.

Intent:
- Keep reusable `instagram` support logic centralized so business modules stay
  focused on orchestration.
===============================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from harnessiq.agents.helpers import read_optional_text
from harnessiq.shared.agents import AgentModelResponse
from harnessiq.shared.dtos import InstagramAgentInstancePayload
from harnessiq.shared.instagram import InstagramMemoryStore, resolve_instagram_icp_profiles
from harnessiq.shared.tools import INSTAGRAM_SEARCH_KEYWORD


def normalize_icp_descriptions(icp_descriptions: Iterable[str]) -> tuple[str, ...]:
    """Normalize configured ICP descriptions into a stable tuple."""
    normalized: list[str] = []
    for description in icp_descriptions:
        cleaned = str(description).strip()
        if cleaned:
            normalized.append(cleaned)
    return tuple(normalized)


def is_search_only_response(response: AgentModelResponse) -> bool:
    """Return whether the response only called the Instagram search tool."""
    return bool(response.tool_calls) and all(
        tool_call.tool_key == INSTAGRAM_SEARCH_KEYWORD for tool_call in response.tool_calls
    )


def merge_recent_keywords(
    *keyword_groups: Iterable[str],
    limit: int,
) -> tuple[str, ...]:
    """Merge keyword groups without duplicates while preserving recency order."""
    merged: list[str] = []
    seen: set[str] = set()
    for group in keyword_groups:
        for keyword in group:
            cleaned = str(keyword).strip()
            if not cleaned:
                continue
            normalized = cleaned.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            merged.append(cleaned)
    if limit <= 0:
        return tuple(merged)
    return tuple(merged[-limit:])


def build_instagram_instance_payload(
    *,
    memory_path: Path | None,
    icp_descriptions: tuple[str, ...],
    max_tokens: int,
    reset_threshold: float,
    recent_search_window: int,
    recent_result_window: int,
    search_result_limit: int,
    custom_parameters: Mapping[str, Any] | None = None,
) -> InstagramAgentInstancePayload:
    """Build the Instagram agent instance payload from config and persisted state."""
    runtime = {
        "max_tokens": max_tokens,
        "recent_result_window": recent_result_window,
        "recent_search_window": recent_search_window,
        "reset_threshold": reset_threshold,
        "search_result_limit": search_result_limit,
    }
    payload = InstagramAgentInstancePayload(
        custom_parameters=dict(custom_parameters) if custom_parameters else None,
        icp_descriptions=tuple(icp_descriptions),
        memory_path=memory_path,
        runtime=runtime,
    )
    if memory_path is None or not memory_path.exists():
        return payload

    store = InstagramMemoryStore(memory_path=memory_path)
    resolved_custom_parameters = (
        dict(custom_parameters) if custom_parameters is not None else store.read_custom_parameters()
    )
    icp_states = store.list_icp_states(current_only=True, custom_parameters=resolved_custom_parameters)
    return InstagramAgentInstancePayload(
        custom_parameters=resolved_custom_parameters or None,
        icp_descriptions=tuple(
            resolve_instagram_icp_profiles(
                store.read_icp_profiles(),
                resolved_custom_parameters,
            )
        ),
        memory_path=memory_path,
        runtime=runtime,
        agent_identity=read_optional_text(store.agent_identity_path),
        additional_prompt=read_optional_text(store.additional_prompt_path),
        run_state=store.read_run_state().as_dict() if store.run_state_path.exists() else None,
        icp_progress=(
            tuple(
                {
                    "completed_at": state.completed_at,
                    "icp": state.icp.as_dict(),
                    "search_count": len(state.searches),
                    "status": state.status,
                }
                for state in icp_states
            )
            or None
        ),
    )


__all__ = [
    "build_instagram_instance_payload",
    "is_search_only_response",
    "merge_recent_keywords",
    "normalize_icp_descriptions",
]
