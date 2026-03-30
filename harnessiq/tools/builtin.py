"""
===============================================================================
File: harnessiq/tools/builtin.py

What this file does:
- Composes the default built-in tool catalog that every HarnessIQ runtime can
  start from.
- This file is the assembly point where generic context, filesystem, reasoning,
  memory, and validation tool families are stitched together.
- Small built-in tools used to validate the initial runtime scaffold.

Use cases:
- Inspect the default baseline tool surface available before agent-specific
  tools are added.
- Update this file when adding or reordering a built-in tool family.

How to use it:
- Import `BUILTIN_TOOLS` or call registry helpers that use it under the hood.
- Add new built-ins by defining `RegisteredTool` entries or appending family
  factory output here.

Intent:
- Make the default runtime surface explicit and deterministic instead of
  letting built-ins emerge from scattered imports.
===============================================================================
"""

from __future__ import annotations

from harnessiq.shared.tools import ADD_NUMBERS, ECHO_TEXT, RegisteredTool, ToolArguments, ToolDefinition

from .context_compaction import create_context_compaction_tools
from .context import create_context_tools
from .filesystem import create_filesystem_tools
from .filesystem_safe import create_filesystem_safe_tools
from .artifact import create_artifact_tools
from .control import create_control_tools
from .general_purpose import create_general_purpose_tools
from .memory import create_memory_tools
from .prompting import create_prompt_tools
from .reasoning import create_reasoning_tools
from .records import create_records_tools
from .text import create_text_tools
from .validation import create_validation_tools


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
    *create_general_purpose_tools(),
    *create_prompt_tools(),
    *create_filesystem_tools(),
    *create_reasoning_tools(),
    *create_context_tools(),
    *create_text_tools(),
    *create_records_tools(),
    *create_control_tools(),
    *create_filesystem_safe_tools(),
    *create_validation_tools(),
    *create_memory_tools(),
    *create_artifact_tools(),
)
