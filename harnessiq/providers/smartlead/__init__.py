"""Smartlead cold email outreach API — credentials, client, and operation catalog."""

from .client import SmartleadClient, SmartleadCredentials
from .operations import (
    SMARTLEAD_REQUEST,
    SmartleadOperation,
    SmartleadPreparedRequest,
    build_smartlead_operation_catalog,
    get_smartlead_operation,
)

__all__ = [
    "SMARTLEAD_REQUEST",
    "SmartleadClient",
    "SmartleadCredentials",
    "SmartleadOperation",
    "SmartleadPreparedRequest",
    "build_smartlead_operation_catalog",
    "get_smartlead_operation",
]
