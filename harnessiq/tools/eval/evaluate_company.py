"""
===============================================================================
File: harnessiq/tools/eval/evaluate_company.py

What this file does:
- Implements focused support logic for `harnessiq/tools/eval`.
- Public shared evaluation tool for prospecting-style workflows.

Use cases:
- Import this module when sibling runtime code needs the behavior it
  centralizes.

How to use it:
- Use `build_evaluate_company_tool_definition` and the other exported symbols
  here through their package-level integration points.

Intent:
- Keep related runtime behavior centralized and easier to discover during
  maintenance.
===============================================================================
"""

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
                "listing_data": {
                    "type": "object",
                    "description": (
                        "Structured extracted listing data. The harness injects the configured "
                        "company description and evaluation prompt."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["listing_data"],
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
