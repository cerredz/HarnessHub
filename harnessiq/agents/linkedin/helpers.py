"""Helper functions for the LinkedIn agent."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Sequence

from harnessiq.agents.helpers import read_optional_text
from harnessiq.shared.dtos import LinkedInAgentInstancePayload
from harnessiq.shared.linkedin import LinkedInMemoryStore
from harnessiq.shared.tools import ToolDefinition


def build_linkedin_instance_payload(
    *,
    memory_path: Path | None,
    max_tokens: int,
    reset_threshold: float,
    action_log_window: int,
    linkedin_start_url: str,
    notify_on_pause: bool,
    pause_webhook: str | None,
) -> LinkedInAgentInstancePayload:
    """Build the LinkedIn agent instance payload from config and persisted state."""
    runtime: dict[str, Any] = {
        "action_log_window": action_log_window,
        "linkedin_start_url": linkedin_start_url,
        "max_tokens": max_tokens,
        "notify_on_pause": notify_on_pause,
        "pause_webhook": pause_webhook,
        "reset_threshold": reset_threshold,
    }
    payload = LinkedInAgentInstancePayload(
        memory_path=memory_path,
        runtime=runtime,
    )
    if memory_path is None or not memory_path.exists():
        return payload

    store = LinkedInMemoryStore(memory_path=memory_path)
    runtime_parameters = store.read_runtime_parameters() if store.runtime_parameters_path.exists() else {}
    custom_parameters = store.read_custom_parameters() if store.custom_parameters_path.exists() else {}
    return LinkedInAgentInstancePayload(
        memory_path=memory_path,
        runtime=runtime_parameters or runtime,
        job_preferences=read_optional_text(store.job_preferences_path),
        user_profile=read_optional_text(store.user_profile_path),
        agent_identity=read_optional_text(store.agent_identity_path),
        additional_prompt=read_optional_text(store.additional_prompt_path),
        custom=custom_parameters or None,
    )


def unavailable_browser_handler(tool_name: str):
    """Build a browser-tool stub that fails with a clear runtime error."""

    def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        message = f"Browser tool '{tool_name}' requires a runtime handler."
        raise RuntimeError(message)

    return handler


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


def or_placeholder(value: str, placeholder: str) -> str:
    """Return a placeholder when the stored value is empty."""
    return value if value else placeholder


def sanitize_label(label: str) -> str:
    """Normalize a label into a safe screenshot filename stem."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-")
    return cleaned or "screenshot"


def relative_path_text(path: Path, root: Path) -> str:
    """Render a relative POSIX path for payloads and logs."""
    return path.resolve().relative_to(root.resolve()).as_posix()


__all__ = [
    "build_linkedin_instance_payload",
    "or_placeholder",
    "relative_path_text",
    "sanitize_label",
    "tool_definition",
    "unavailable_browser_handler",
]
