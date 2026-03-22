"""Compatibility facade for the decomposed Resend tooling surface."""

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
