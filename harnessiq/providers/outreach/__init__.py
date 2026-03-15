"""Outreach.io sales engagement API — credentials, OAuth client, and operation catalog."""

from .client import OutreachClient, OutreachCredentials
from .operations import (
    OUTREACH_REQUEST,
    OutreachOperation,
    OutreachPreparedRequest,
    build_outreach_operation_catalog,
    build_outreach_request_tool_definition,
    create_outreach_tools,
    get_outreach_operation,
)

__all__ = [
    "OUTREACH_REQUEST",
    "OutreachClient",
    "OutreachCredentials",
    "OutreachOperation",
    "OutreachPreparedRequest",
    "build_outreach_operation_catalog",
    "build_outreach_request_tool_definition",
    "create_outreach_tools",
    "get_outreach_operation",
]
