"""Helper functions for the Google Maps prospecting agent."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Sequence

from harnessiq.shared.prospecting import ProspectingMemoryStore
from harnessiq.shared.tools import RegisteredTool, ToolDefinition
from harnessiq.tools import build_browser_tool_definitions


def create_browser_stub_tools() -> tuple[RegisteredTool, ...]:
    """Create browser tool stubs for environments without runtime handlers."""
    return tuple(
        RegisteredTool(definition=definition, handler=unavailable_browser_handler(definition.name))
        for definition in build_browser_tool_definitions()
    )


def unavailable_browser_handler(tool_name: str):
    """Build a browser-tool stub that fails with a clear runtime error."""

    def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        del arguments
        raise RuntimeError(f"Browser tool '{tool_name}' requires a runtime handler.")

    return handler


def tool(
    *,
    key: str,
    name: str,
    description: str,
    properties: dict[str, Any],
    required: Sequence[str],
    handler: Callable[[dict[str, Any]], dict[str, Any]],
) -> RegisteredTool:
    """Build a registered tool with a strict object schema."""
    return RegisteredTool(
        definition=ToolDefinition(
            key=key,
            name=name,
            description=description,
            input_schema={
                "type": "object",
                "properties": properties,
                "required": list(required),
                "additionalProperties": False,
            },
        ),
        handler=handler,
    )


def parse_json_object(raw_text: str) -> dict[str, Any]:
    """Parse a JSON object from plain text or fenced JSON output."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object response.")
    return payload


def build_instance_payload(
    *,
    memory_path: Path | None,
    company_description: str | None,
    max_tokens: int,
    reset_threshold: float,
    qualification_threshold: int,
    summarize_at_x: int,
    max_searches_per_run: int,
    max_listings_per_search: int,
    website_inspect_enabled: bool,
    sink_record_type: str,
    eval_system_prompt: str,
) -> dict[str, Any]:
    """Build the prospecting agent instance payload from config and persisted state."""
    payload: dict[str, Any] = {
        "company_description": company_description or "",
        "runtime": {
            "max_tokens": max_tokens,
            "reset_threshold": reset_threshold,
        },
        "custom": {
            "qualification_threshold": qualification_threshold,
            "summarize_at_x": summarize_at_x,
            "max_searches_per_run": max_searches_per_run,
            "max_listings_per_search": max_listings_per_search,
            "website_inspect_enabled": website_inspect_enabled,
            "sink_record_type": sink_record_type,
            "eval_system_prompt": eval_system_prompt,
        },
    }
    if memory_path is not None:
        payload["memory_path"] = str(memory_path)
    if memory_path is None or not memory_path.exists():
        return payload
    store = ProspectingMemoryStore(memory_path=memory_path)
    store.prepare()
    payload["company_description"] = store.read_company_description()
    payload["agent_identity"] = store.read_agent_identity()
    payload["additional_prompt"] = store.read_additional_prompt()
    payload["runtime"] = store.read_runtime_parameters() or payload["runtime"]
    payload["custom"] = store.read_custom_parameters() or payload["custom"]
    return payload


__all__ = [
    "build_instance_payload",
    "create_browser_stub_tools",
    "parse_json_object",
    "tool",
    "unavailable_browser_handler",
]
