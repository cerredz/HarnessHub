"""Public shared evaluation tool for prospecting-style workflows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harnessiq.shared.tools import EVALUATE_COMPANY, RegisteredTool, ToolDefinition

EvaluateCompanyHandler = Callable[[dict[str, Any]], dict[str, Any]]


def build_evaluate_company_tool_definition() -> ToolDefinition:
    """Return the canonical tool definition for company qualification."""
    return ToolDefinition(
        key=EVALUATE_COMPANY,
        name="evaluate_company",
        description="Evaluate one extracted company listing against a target company description and return a structured verdict.",
        input_schema={
            "type": "object",
            "properties": {
                "company_description": {
                    "type": "string",
                    "description": "Natural-language description of the target company profile.",
                },
                "eval_system_prompt": {
                    "type": "string",
                    "description": "Full system prompt used by the evaluation engine.",
                },
                "listing_data": {
                    "type": "object",
                    "description": "Structured extracted listing data.",
                    "additionalProperties": True,
                },
            },
            "required": ["company_description", "eval_system_prompt", "listing_data"],
            "additionalProperties": False,
        },
    )


def create_evaluate_company_tool(*, handler: EvaluateCompanyHandler) -> RegisteredTool:
    """Create the public shared evaluation tool with an injected handler."""
    return RegisteredTool(definition=build_evaluate_company_tool_definition(), handler=handler)


__all__ = [
    "EvaluateCompanyHandler",
    "build_evaluate_company_tool_definition",
    "create_evaluate_company_tool",
]
