"""
===============================================================================
File: harnessiq/tools/resend.py

What this file does:
- Implements focused support logic for `harnessiq/tools`.
- Compatibility facade for the decomposed Resend tooling surface.

Use cases:
- Import this module when sibling runtime code needs the behavior it
  centralizes.

How to use it:
- Import the exported symbols here through their package-level integration
  points.

Intent:
- Keep related runtime behavior centralized and easier to discover during
  maintenance.
===============================================================================
"""

from __future__ import annotations

from harnessiq.shared.resend import (
    DEFAULT_RESEND_BASE_URL,
    DEFAULT_RESEND_USER_AGENT,
    RESEND_REQUEST,
    ResendCredentials,
    ResendOperation,
    ResendPreparedRequest,
)
from harnessiq.tools.resend_catalog import build_resend_operation_catalog, get_resend_operation
from harnessiq.tools.resend_client import ResendClient
from harnessiq.tools.resend_tool import build_resend_request_tool_definition, create_resend_tools

__all__ = [
    "DEFAULT_RESEND_BASE_URL",
    "DEFAULT_RESEND_USER_AGENT",
    "RESEND_REQUEST",
    "ResendClient",
    "ResendCredentials",
    "ResendOperation",
    "ResendPreparedRequest",
    "build_resend_operation_catalog",
    "build_resend_request_tool_definition",
    "create_resend_tools",
    "get_resend_operation",
]
