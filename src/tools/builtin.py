"""Small built-in tools used to validate the initial runtime scaffold."""

from __future__ import annotations

from src.shared.tools import ADD_NUMBERS, ECHO_TEXT, RegisteredTool, ToolArguments, ToolDefinition

from .context_compaction import create_context_compaction_tools


def _echo_text(arguments: ToolArguments) -> dict[str, str]:
    text = str(arguments["text"])
    return {"text": text}


def _add_numbers(arguments: ToolArguments) -> dict[str, float]:
    left = float(arguments["left"])
    right = float(arguments["right"])
    return {"sum": left + right}


BUILTIN_TOOLS = (
    RegisteredTool(
        definition=ToolDefinition(
            key=ECHO_TEXT,
            name="echo_text",
            description="Return the provided text unchanged.",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to echo back to the caller.",
                    }
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        ),
        handler=_echo_text,
    ),
    RegisteredTool(
        definition=ToolDefinition(
            key=ADD_NUMBERS,
            name="add_numbers",
            description="Add two numeric values and return the total.",
            input_schema={
                "type": "object",
                "properties": {
                    "left": {
                        "type": "number",
                        "description": "The first numeric value.",
                    },
                    "right": {
                        "type": "number",
                        "description": "The second numeric value.",
                    },
                },
                "required": ["left", "right"],
                "additionalProperties": False,
            },
        ),
        handler=_add_numbers,
    ),
    *create_context_compaction_tools(),
)
