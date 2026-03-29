from __future__ import annotations

from typing import Any

from harnessiq.shared.tools import RegisteredTool, ToolDefinition


def _handle_stage_complete(arguments: dict[str, Any]) -> dict[str, Any]:
    summary = str(arguments["summary"]).strip()
    raw_outputs = arguments.get("outputs", {})
    if raw_outputs is None:
        outputs: dict[str, Any] = {}
    elif isinstance(raw_outputs, dict):
        outputs = dict(raw_outputs)
    else:
        raise TypeError("outputs must be an object mapping when provided.")
    return {
        "summary": summary,
        "outputs": outputs,
    }


STAGE_COMPLETE_TOOL = RegisteredTool(
    definition=ToolDefinition(
        key="formalization.stage_complete",
        name="stage_complete",
        description=(
            "Signal that the current stage is complete and provide a summary plus any "
            "structured outputs required by the active stage."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A concise summary of the completed stage outcome.",
                },
                "outputs": {
                    "type": "object",
                    "description": "Structured outputs produced by the current stage.",
                    "additionalProperties": True,
                },
            },
            "required": ["summary"],
            "additionalProperties": False,
        },
    ),
    handler=_handle_stage_complete,
)
