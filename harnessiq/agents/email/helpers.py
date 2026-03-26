"""Helper functions for email-capable agents."""

from __future__ import annotations

import json

from harnessiq.shared.email import EmailAgentConfig
from harnessiq.shared.tools import ToolDefinition
from harnessiq.tools.resend import build_resend_operation_catalog


def render_resend_credentials(config: EmailAgentConfig) -> str:
    """Render the redacted Resend credential payload for prompt injection."""
    allowed_operations = config.allowed_resend_operations
    if allowed_operations is None:
        allowed_operations = tuple(operation.name for operation in build_resend_operation_catalog())
    payload = config.resend_credentials.as_redacted_dict()
    payload["allowed_operation_count"] = len(allowed_operations)
    payload["allowed_operation_sample"] = list(allowed_operations[:8])
    return json.dumps(payload, indent=2, sort_keys=True)


def summarize_tool(tool: ToolDefinition) -> str:
    """Return the first descriptive line for a tool."""
    return tool.description.splitlines()[0]


__all__ = ["render_resend_credentials", "summarize_tool"]
