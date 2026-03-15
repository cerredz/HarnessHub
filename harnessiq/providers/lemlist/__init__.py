"""Lemlist cold email and outreach API — credentials, client, and operation catalog."""

from .client import LemlistClient, LemlistCredentials
from .operations import (
    LEMLIST_REQUEST,
    LemlistOperation,
    LemlistPreparedRequest,
    build_lemlist_operation_catalog,
    build_lemlist_request_tool_definition,
    create_lemlist_tools,
    get_lemlist_operation,
)

__all__ = [
    "LEMLIST_REQUEST",
    "LemlistClient",
    "LemlistCredentials",
    "LemlistOperation",
    "LemlistPreparedRequest",
    "build_lemlist_operation_catalog",
    "build_lemlist_request_tool_definition",
    "create_lemlist_tools",
    "get_lemlist_operation",
]
