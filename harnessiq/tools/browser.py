"""
===============================================================================
File: harnessiq/tools/browser.py

What this file does:
- Implements focused support logic for `harnessiq/tools`.
- Reusable browser tool definitions and factory helpers.

Use cases:
- Import this module when sibling runtime code needs the behavior it
  centralizes.

How to use it:
- Use `build_browser_tool_definitions` and the other exported symbols here
  through their package-level integration points.

Intent:
- Keep related runtime behavior centralized and easier to discover during
  maintenance.
===============================================================================
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from harnessiq.shared.tools import (
    BROWSER_CLICK,
    BROWSER_EXTRACT_CONTENT,
    BROWSER_FIND_ELEMENT,
    BROWSER_GET_CURRENT_URL,
    BROWSER_GET_TEXT,
    BROWSER_HOVER,
    BROWSER_NAVIGATE,
    BROWSER_PRESS_KEY,
    BROWSER_SCREENSHOT,
    BROWSER_SCROLL,
    BROWSER_SELECT_OPTION,
    BROWSER_TYPE,
    BROWSER_UPLOAD_FILE,
    BROWSER_VIEW_HTML,
    BROWSER_WAIT_FOR_ELEMENT,
    RegisteredTool,
    ToolDefinition,
    ToolHandler,
)


def build_browser_tool_definitions() -> tuple[ToolDefinition, ...]:
    """Return canonical reusable browser tool definitions."""
    return (
        _tool_definition(
            key=BROWSER_NAVIGATE,
            name="navigate",
            description="Navigate the active browser page to a URL.",
            properties={"url": {"type": "string", "description": "Destination URL."}},
            required=("url",),
        ),
        _tool_definition(
            key=BROWSER_CLICK,
            name="click",
            description="Click an element matched by selector or accessible target text.",
            properties={"selector": {"type": "string", "description": "Element selector or target text."}},
            required=("selector",),
        ),
        _tool_definition(
            key=BROWSER_TYPE,
            name="type",
            description="Focus an input and type text into it after clearing any existing value.",
            properties={
                "selector": {"type": "string", "description": "Input selector."},
                "text": {"type": "string", "description": "Text to enter."},
            },
            required=("selector", "text"),
        ),
        _tool_definition(
            key=BROWSER_SELECT_OPTION,
            name="select_option",
            description="Select an option in a dropdown by value or label.",
            properties={
                "selector": {"type": "string", "description": "Select element selector."},
                "value": {"type": "string", "description": "Option value or visible label."},
            },
            required=("selector", "value"),
        ),
        _tool_definition(
            key=BROWSER_HOVER,
            name="hover",
            description="Hover over an element without clicking it.",
            properties={"selector": {"type": "string", "description": "Element selector."}},
            required=("selector",),
        ),
        _tool_definition(
            key=BROWSER_UPLOAD_FILE,
            name="upload_file",
            description="Upload a file through a file input element.",
            properties={
                "selector": {"type": "string", "description": "File input selector."},
                "file_path": {"type": "string", "description": "Path to the file to upload."},
            },
            required=("selector", "file_path"),
        ),
        _tool_definition(
            key=BROWSER_PRESS_KEY,
            name="press_key",
            description="Send a keyboard event such as Enter, Tab, Escape, or ArrowDown.",
            properties={"key": {"type": "string", "description": "Keyboard key value."}},
            required=("key",),
        ),
        _tool_definition(
            key=BROWSER_SCROLL,
            name="scroll",
            description="Scroll the current page up or down by a pixel amount.",
            properties={
                "direction": {"type": "string", "enum": ["up", "down"], "description": "Scroll direction."},
                "amount": {"type": "integer", "description": "Number of pixels to scroll."},
            },
            required=("direction", "amount"),
        ),
        _tool_definition(
            key=BROWSER_WAIT_FOR_ELEMENT,
            name="wait_for_element",
            description="Wait until an element appears or the timeout expires.",
            properties={
                "selector": {"type": "string", "description": "Selector to wait for."},
                "timeout_ms": {"type": "integer", "description": "Maximum wait in milliseconds."},
            },
            required=("selector",),
        ),
        _tool_definition(
            key=BROWSER_SCREENSHOT,
            name="screenshot",
            description="Capture a screenshot of the current browser page.",
            properties={},
        ),
        _tool_definition(
            key=BROWSER_VIEW_HTML,
            name="view_html",
            description="Return the raw HTML for the current browser page.",
            properties={},
        ),
        _tool_definition(
            key=BROWSER_GET_TEXT,
            name="get_text",
            description="Return the visible text content of the current page.",
            properties={},
        ),
        _tool_definition(
            key=BROWSER_FIND_ELEMENT,
            name="find_element",
            description="Return whether an element exists on the current page.",
            properties={"selector": {"type": "string", "description": "Selector or text target to search for."}},
            required=("selector",),
        ),
        _tool_definition(
            key=BROWSER_GET_CURRENT_URL,
            name="get_current_url",
            description="Return the current browser URL.",
            properties={},
        ),
        _tool_definition(
            key=BROWSER_EXTRACT_CONTENT,
            name="extract_content",
            description="Run an integration-provided structured extraction mode against the current page.",
            properties={
                "mode": {
                    "type": "string",
                    "description": (
                        "Named extraction mode implemented by the browser integration, for example "
                        "'maps_search_results', 'maps_place_details', or 'website_quality_snapshot'."
                    ),
                },
                "selector": {
                    "type": "string",
                    "description": "Optional selector used by the integration-specific extraction mode.",
                },
                "max_items": {
                    "type": "integer",
                    "description": "Optional maximum number of extracted items to return.",
                },
            },
            required=("mode",),
        ),
    )


def create_browser_tools(*, handlers: Mapping[str, ToolHandler]) -> tuple[RegisteredTool, ...]:
    """Bind canonical browser definitions to concrete handlers."""
    tools: list[RegisteredTool] = []
    for definition in build_browser_tool_definitions():
        handler = handlers.get(definition.name) or handlers.get(definition.key)
        if handler is None:
            raise KeyError(
                f"Missing browser handler for '{definition.name}'. "
                f"Expected a handler keyed by '{definition.name}' or '{definition.key}'."
            )
        tools.append(RegisteredTool(definition=definition, handler=handler))
    return tuple(tools)


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


__all__ = [
    "build_browser_tool_definitions",
    "create_browser_tools",
]
