"""Helper functions for the ExaOutreach agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

from harnessiq.agents.helpers import read_optional_text
from harnessiq.shared.exa_outreach import EmailTemplate, ExaOutreachMemoryStore
from harnessiq.shared.tools import RegisteredTool, ToolDefinition


def tool_definition(
    *,
    key: str,
    name: str,
    description: str,
    properties: dict[str, Any],
    required: Sequence[str] = (),
) -> ToolDefinition:
    """Build a strict object-schema tool definition."""
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


def coerce_email_data(
    email_data: Iterable[EmailTemplate | dict[str, Any]] | None,
) -> tuple[EmailTemplate, ...]:
    """Normalize template-like inputs into concrete email templates."""
    if email_data is None:
        return ()
    templates: list[EmailTemplate] = []
    for item in email_data:
        if isinstance(item, EmailTemplate):
            templates.append(item)
            continue
        if isinstance(item, dict):
            templates.append(EmailTemplate.from_dict(item))
            continue
        raise TypeError(f"email_data items must be EmailTemplate or dict, got {type(item)!r}.")
    return tuple(templates)


def build_exa_outreach_instance_payload(
    *,
    memory_path: Path | None,
    email_data: tuple[EmailTemplate, ...],
    search_query: str,
    max_tokens: int,
    reset_threshold: float,
    allowed_resend_operations: tuple[str, ...] | None,
    allowed_exa_operations: tuple[str, ...] | None,
) -> dict[str, Any]:
    """Build the agent instance payload from runtime config and persisted memory."""
    payload: dict[str, Any] = {
        "allowed_exa_operations": list(allowed_exa_operations) if allowed_exa_operations is not None else None,
        "allowed_resend_operations": list(allowed_resend_operations) if allowed_resend_operations is not None else None,
        "email_data": [item.as_dict() for item in email_data],
        "max_tokens": max_tokens,
        "reset_threshold": reset_threshold,
        "search_query": search_query,
    }
    if memory_path is not None:
        payload["memory_path"] = str(memory_path)
    if memory_path is None or not memory_path.exists():
        return payload

    store = ExaOutreachMemoryStore(memory_path=memory_path)
    payload["agent_identity"] = read_optional_text(store.agent_identity_path)
    payload["additional_prompt"] = read_optional_text(store.additional_prompt_path)
    query_config = store.read_query_config() if store.query_config_path.exists() else {}
    if query_config:
        payload["query_config"] = query_config
    return payload


def create_exa_tools(
    *,
    credentials: Any | None,
    client: Any | None,
    allowed_operations: Sequence[str] | None,
) -> tuple[RegisteredTool, ...]:
    """Create provider-backed Exa tools lazily to avoid import cycles."""
    from harnessiq.providers.exa.operations import create_exa_tools as _create_exa_tools

    return _create_exa_tools(credentials=credentials, client=client, allowed_operations=allowed_operations)


def create_resend_tools(
    *,
    credentials: Any | None,
    client: Any | None,
    allowed_operations: tuple[str, ...] | None,
) -> tuple[RegisteredTool, ...]:
    """Create Resend tools only when credentials or a client are available."""
    if credentials is None and client is None:
        return ()
    from harnessiq.tools.resend import create_resend_tools as _create_resend_tools

    return _create_resend_tools(credentials=credentials, client=client, allowed_operations=allowed_operations)


__all__ = [
    "build_exa_outreach_instance_payload",
    "coerce_email_data",
    "create_exa_tools",
    "create_resend_tools",
    "tool_definition",
]
