"""Instantly.ai cold email API v2 — credentials, client, and operation catalog."""

from .client import InstantlyClient, InstantlyCredentials
from .operations import (
    INSTANTLY_REQUEST,
    InstantlyOperation,
    InstantlyPreparedRequest,
    build_instantly_operation_catalog,
    get_instantly_operation,
)

__all__ = [
    "INSTANTLY_REQUEST",
    "InstantlyClient",
    "InstantlyCredentials",
    "InstantlyOperation",
    "InstantlyPreparedRequest",
    "build_instantly_operation_catalog",
    "get_instantly_operation",
]
