"""Outreach.io sales engagement API — credentials, OAuth client, and operation catalog."""

from .client import OutreachClient, OutreachCredentials
from .operations import (
    OUTREACH_REQUEST,
    OutreachOperation,
    OutreachPreparedRequest,
    build_outreach_operation_catalog,
    get_outreach_operation,
)

__all__ = [
    "OUTREACH_REQUEST",
    "OutreachClient",
    "OutreachCredentials",
    "OutreachOperation",
    "OutreachPreparedRequest",
    "build_outreach_operation_catalog",
    "get_outreach_operation",
]
