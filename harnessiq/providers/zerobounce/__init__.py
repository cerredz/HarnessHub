"""ZeroBounce email validation API — credentials, client, and operation catalog."""

from .client import ZeroBounceClient, ZeroBounceCredentials
from .operations import (
    ZEROBOUNCE_REQUEST,
    ZeroBounceOperation,
    ZeroBouncePreparedRequest,
    build_zerobounce_operation_catalog,
    get_zerobounce_operation,
)

__all__ = [
    "ZEROBOUNCE_REQUEST",
    "ZeroBounceClient",
    "ZeroBounceCredentials",
    "ZeroBounceOperation",
    "ZeroBouncePreparedRequest",
    "build_zerobounce_operation_catalog",
    "get_zerobounce_operation",
]
